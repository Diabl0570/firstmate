#!/usr/bin/env python3
"""Drive real contribution CLI + installed gh against an isolated local TLS forge.
Run from the gate worktree. Never contacts GitHub or reads operator credentials.
Only the external forge is simulated; all Firstmate and gh code is unmodified.
"""
import collections
import copy
import http.server
import json
import os
from pathlib import Path
import re
import shutil
import ssl
import subprocess
import threading
import time
import urllib.parse

ROOT = Path.cwd()
EVIDENCE = Path('/home/kasper/.no-mistakes/evidence/01M5P95G6JPG8XSVC4A4MC2XBY')
LAB = ROOT / '.test-validation/live'
HEAD = 'a' * 40
NOW = '2026-09-16T08:00:00Z'
URL = 'https://github.com/lab/owned/pull/8'
SECRET = 'PRIVATE_DIAGNOSTIC_SENTINEL'
TRANSCRIPT = []
RESULTS = []
LOCK = threading.Lock()
STATE = {'mode': 'ok', 'calls': [], 'counts': collections.Counter(), 'comments': []}


def log(text):
    print(text, flush=True)
    TRANSCRIPT.append(text)


def reset(mode='ok', comments=None):
    with LOCK:
        STATE.update(mode=mode, calls=[], counts=collections.Counter(), comments=comments or [])


class Forge(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_CONNECT(self):
        if self.path not in ('api.github.com:443', 'github.com:443'):
            self.send_error(403)
            return
        self.send_response(200, 'Connection established')
        self.end_headers()
        self.connection = TLS.wrap_socket(self.connection, server_side=True)
        self.rfile = self.connection.makefile('rb')
        self.wfile = self.connection.makefile('wb')
        self.close_connection = False
        self.handle_one_request()

    def do_GET(self):
        self.answer()

    def do_POST(self):
        self.answer()

    def answer(self):
        body = self.rfile.read(int(self.headers.get('Content-Length', 0)))
        data = json.loads(body) if body else {}
        path = urllib.parse.urlsplit(self.path).path
        stage = 'unknown'
        if path == '/repos/lab/owned/pulls/8': stage = 'core'
        elif path == '/repos/lab/owned/pulls/9': stage = 'core-9'
        elif path.endswith('/check-runs'): stage = 'checks'
        elif path.endswith('/statuses'): stage = 'statuses'
        elif re.search('/pulls/[89]/reviews$', path): stage = 'reviews'
        elif re.search('/pulls/[89]/comments$', path): stage = 'inline'
        elif re.search('/issues/[89]/comments$', path): stage = 'comments'
        elif path == '/repos/lab/owned/issues/9': stage = 'issue-core'
        elif path.endswith('/events'): stage = 'issue-events'
        elif path == '/repos/lab/owned': stage = 'repo'
        elif path == '/graphql': stage = 'threads' if 'reviewThreads' in data.get('query', '') else 'head'
        with LOCK:
            mode = STATE['mode']
            STATE['counts'][stage] += 1
            attempt = STATE['counts'][stage]
            STATE['calls'].append({'stage': stage, 'method': self.command, 'path': self.path, 'attempt': attempt})
            comments = copy.deepcopy(STATE['comments'])
        status = 200
        headers = {}
        if mode in ('both', 'reverse', 'retry') and stage in ('checks', 'statuses') and (mode != 'retry' or attempt == 1):
            # Reverse completion order in the two persistent-failure cases.
            time.sleep(0.12 if stage == ('checks' if mode == 'reverse' else 'statuses') else 0)
            status, payload = 500, {'message': f'{SECRET} https://private.invalid/private?token=secret Authorization: bearer secret'}
        elif mode in ('oversized', 'invalid-http', 'cut-http') and stage == 'reviews':
            status = 422
            if mode == 'oversized': message = 'x' * 5000 + ' (HTTP 500) ' + SECRET
            elif mode == 'invalid-http': message = 'HTTP 5000 ' + SECRET
            else: message = 'x' * 4088 + '\ngh: HTTP 500\n' + SECRET
            payload = {'message': message}
        elif mode == 'schema' and stage == 'reviews':
            status, payload = 404, {'message': SECRET}
        elif mode == 'schema' and stage == 'core-9':
            payload = {'state': 'open', 'user': None}
        elif mode == 'slow' and stage == 'core':
            time.sleep(6)
            payload = {'state': 'open', 'user': {'login': 'author'}, 'head': {'sha': HEAD}}
        elif stage in ('core', 'core-9'):
            payload = {'state': 'open', 'user': {'login': 'author'}, 'head': {'sha': HEAD}, 'draft': False, 'mergeable': True, 'merged_at': None}
        elif stage == 'checks':
            payload = {'check_runs': [{'name': 'test', 'id': 1, 'status': 'completed', 'conclusion': 'success', 'started_at': NOW}]}
        elif stage == 'repo': payload = {'permissions': {'push': False}}
        elif stage == 'head':
            payload = {'data': {'repository': {'pullRequest': {'headRefOid': ('b' * 40 if mode == 'drift' else HEAD), 'reviewDecision': 'APPROVED'}}}}
        elif stage == 'threads':
            payload = {'data': {'repository': {'pullRequest': {'reviewThreads': {'nodes': [], 'pageInfo': {'hasNextPage': False, 'endCursor': None}}}}}}
        elif stage == 'issue-core': payload = {'state': 'open', 'user': {'login': 'author'}, 'labels': [{'name': 'ready-for-pr'}]}
        elif stage == 'issue-events':
            payload = [{'id': 60, 'event': 'labeled', 'label': {'name': 'ready-for-pr'}, 'actor': {'login': 'maintainer'}, 'created_at': NOW}]
        elif stage == 'comments':
            page = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query).get('page', ['1'])[0]
            payload = comments if page == '1' else []
            if comments and page == '1':
                headers['Link'] = f'<https://api.github.com{path}?per_page=100&page=2>; rel="next"'
        elif stage in ('reviews', 'inline', 'statuses'): payload = []
        else:
            status, payload = 500, {'message': 'Unexpected lab endpoint ' + self.path}
        encoded = json.dumps(payload).encode()
        try:
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(encoded)))
            for key, value in headers.items(): self.send_header(key, value)
            self.end_headers()
            self.wfile.write(encoded)
        except (BrokenPipeError, ConnectionResetError, ssl.SSLError):
            pass


def call(home, *args, budget=20, product=None, reply_age=None):
    env = os.environ.copy()
    for key in list(env):
        if key.startswith(('FM_', 'GH_', 'GITHUB_', 'TASKS_AXI_')) or key in ('NO_PROXY', 'no_proxy', 'ALL_PROXY', 'all_proxy', 'HTTP_PROXY', 'http_proxy', 'HTTPS_PROXY', 'https_proxy'):
            env.pop(key)
    env.update(HOME=str(home), GH_CONFIG_DIR=str(home / 'gh-config'), GH_TOKEN='disposable-local-only',
               FM_HOME=str(home), FM_ROOT_OVERRIDE=str(ROOT), FM_STATE_OVERRIDE=str(home / 'state'),
               FM_DATA_OVERRIDE=str(home / 'data'), FM_CONFIG_OVERRIDE=str(home / 'config'), FM_PROJECTS_OVERRIDE=str(home / 'projects'),
               FM_CONTRIBUTIONS_NOW=NOW, FM_CONTRIBUTIONS_BUDGET=str(budget),
               HTTPS_PROXY=f'http://127.0.0.1:{SERVER.server_port}', NO_PROXY='',
               SSL_CERT_FILE=str(LAB / 'cert.pem'), SSL_CERT_DIR=str(LAB / 'empty-trust'),
               TMPDIR=str(LAB / 'tmp'), GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL='/dev/null')
    if reply_age is not None: env['FM_CONTRIBUTIONS_REPLY_AGE'] = str(reply_age)
    started = time.monotonic()
    result = subprocess.run([str(product or ROOT / 'bin/fm-contributions.sh'), *args], cwd=ROOT, env=env, capture_output=True, text=True, timeout=40)
    elapsed = time.monotonic() - started
    log(f'$ bin/{Path(product).name if product else "fm-contributions.sh"} {" ".join(args)} [home={home.name}, budget={budget}]')
    log(f'exit={result.returncode}; elapsed={elapsed:.3f}s\nstdout: {result.stdout.strip() or "(empty)"}\nstderr: {result.stderr.strip() or "(empty)"}')
    assert result.returncode == 0, result.stderr
    assert not result.stderr, result.stderr
    return result.stdout, elapsed


def home(name, owners=('delivery',)):
    dest = LAB / name
    for child in ('data', 'state', 'config', 'projects', 'gh-config'): (dest / child).mkdir(parents=True, exist_ok=True)
    (dest / '.tasks.toml').write_text('backend = "markdown"\n[markdown]\npath = "data/backlog.md"\narchive = "data/done-archive.md"\ndone_keep = 10\n')
    (dest / 'data/backlog.md').write_text('# Backlog\n\n## Queued\n' + ''.join(f'- [ ] {owner} - Owned contribution {URL} (repo: sample) (kind: ship)\n' for owner in owners))
    return dest


def record(dest, owner='delivery'):
    return json.loads((dest / 'data' / owner / 'contributions.json').read_text())['records'][0]


def save(dest, label):
    result = {p.parent.name: json.loads(p.read_text()) for p in (dest / 'data').glob('*/contributions.json')}
    (EVIDENCE / f'{label}.json').write_text(json.dumps({'records': result, 'requests': STATE['calls'], 'wake_queue': (dest / 'state/.wake-queue').read_text() if (dest / 'state/.wake-queue').exists() else ''}, indent=2))
    log('persisted records: ' + json.dumps(result, sort_keys=True))


def check(name, run):
    try:
        run()
        RESULTS.append({'name': name, 'result': 'pass'})
        log('SCENARIO PASS: ' + name)
    except Exception as exc:
        RESULTS.append({'name': name, 'result': 'fail', 'reason': repr(exc)})
        log('SCENARIO FAIL: ' + name + ': ' + repr(exc))
        raise


def coherent():
    global MAIN
    MAIN = home('coherent', ('delivery', 'other'))
    reset(comments=[{'id': 12, 'user': {'login': 'maintainer'}, 'author_association': 'OWNER', 'body': 'Please clarify the public contract', 'html_url': URL + '#issuecomment-12', 'created_at': NOW, 'updated_at': NOW}])
    call(MAIN, 'enroll', 'delivery', URL)
    out, _ = call(MAIN, 'poll', reply_age=300)
    for owner in ('delivery', 'other'):
        row = record(MAIN, owner)
        assert row['error'] is None and row['observation']['head'] == HEAD
        assert row['observation']['checks'][0]['conclusion'] == 'success'
        assert len(row['pending']) == 1 and row['pending'][0]['author'] == 'maintainer'
    assert STATE['counts']['core'] == 1 and STATE['counts']['head'] == 1
    assert STATE['counts']['comments'] == 2 and STATE['counts']['threads'] == 1
    save(MAIN, 'coherent-observation')
    initial_wakes = (MAIN / 'state/.wake-queue').read_bytes()
    assert call(MAIN, 'poll', reply_age=300)[0] == ''
    assert (MAIN / 'state/.wake-queue').read_bytes() == initial_wakes
    pending, _ = call(MAIN, 'pending')
    assert len(json.loads(pending)) == 2
    token = record(MAIN)['pending'][0]['token']
    call(MAIN, 'ack', 'delivery', URL, token)
    assert record(MAIN)['pending'] == []
    # Keep the other owner's pending signal and a real maintainer verdict for outage checks.
    call(MAIN, 'verdict', 'other', URL, HEAD, URL + '#issuecomment-12', 'maintainer', 'awaiting maintainer')
    save(MAIN, 'acknowledged-observation')


def transient():
    prior = record(MAIN, 'other')
    reset('retry')
    assert call(MAIN, 'poll')[0] == ''
    row = record(MAIN, 'other')
    assert row['error'] is None and row['pending'] == prior['pending'] and row['verdict'] == prior['verdict']
    assert STATE['counts']['checks'] == 2 and STATE['counts']['statuses'] == 2 and STATE['counts']['core'] == 1
    save(MAIN, 'transient-recovered')


def concurrent():
    prior = copy.deepcopy(record(MAIN, 'other'))
    wakes = (MAIN / 'state/.wake-queue').read_bytes()
    for mode in ('both', 'reverse'):
        reset(mode)
        out, _ = call(MAIN, 'poll')
        normalized = re.sub(r'with -?\d+s of budget left', 'with Ns of budget left', out)
        expected = f'contributions: observation unavailable for {URL} - checks read exited 1 with Ns of budget left: HTTP 500; statuses read exited 1 with Ns of budget left: HTTP 500\n'
        assert normalized == expected, normalized
        for owner in ('delivery', 'other'):
            row = record(MAIN, owner)
            assert SECRET not in json.dumps(row)
            assert row['error'].startswith('forge observation unavailable: checks read exited 1')
        row = record(MAIN, 'other')
        for field in ('observation', 'pending', 'seen', 'notified', 'verdict'): assert row[field] == prior[field], field
        assert (MAIN / 'state/.wake-queue').read_bytes() == wakes
        assert STATE['counts']['core'] == 1
        save(MAIN, 'parallel-' + mode)
        assert call(MAIN, 'poll')[0] == ''  # one notification per failure episode
        reset()
        assert call(MAIN, 'poll')[0] == ''
        assert record(MAIN, 'other')['error'] is None
        assert record(MAIN, 'other')['verdict'] == prior['verdict']


def bounded():
    for mode in ('oversized', 'invalid-http', 'cut-http'):
        dest = home(mode)
        reset(mode)
        out, _ = call(dest, 'poll')
        # Real gh appends the transport's genuine HTTP 422 to a short message.
        # Oversized/truncated messages place that suffix outside the 4096-byte cap.
        expected = 'HTTP 422' if mode == 'invalid-http' else 'request failed'
        assert re.sub(r'with -?\d+s of budget left', 'with Ns of budget left', out) == f'contributions: observation unavailable for {URL} - reviews read exited 1 with Ns of budget left: {expected}\n', out
        row = record(dest)
        assert SECRET not in json.dumps(row) and 'HTTP 500' not in row['error']
        assert STATE['counts']['reviews'] == 1
        save(dest, 'bounded-' + mode)


def guardrails():
    prior = copy.deepcopy(record(MAIN, 'other'))
    reset('drift')
    out, _ = call(MAIN, 'poll')
    assert out == f'contributions: observation unavailable for {URL} - head changed during observation\n'
    assert record(MAIN, 'other')['observation'] == prior['observation']
    save(MAIN, 'head-drift')
    before = (MAIN / 'data/other/contributions.json').read_bytes()
    reset('slow')
    out, elapsed = call(MAIN, 'poll', budget=3)
    assert out == '' and elapsed < 6
    assert (MAIN / 'data/other/contributions.json').read_bytes() == before
    assert STATE['counts']['core'] == 1 and STATE['counts']['head'] == 0
    save(MAIN, 'budget-refusal')


def schema():
    dest = home('schema')
    with (dest / 'data/backlog.md').open('a') as f:
        f.write('- [ ] second - Second contribution https://github.com/lab/owned/pull/9 (repo: sample) (kind: ship)\n')
    reset('schema')
    out, _ = call(dest, 'poll')
    assert re.fullmatch(r'forge observation unavailable: reviews read exited 1 with -?\d+s of budget left: HTTP 404', record(dest)['error'])
    assert record(dest, 'second')['error'] == 'forge observation unavailable: core read returned an unexpected shape'
    assert 'contributions: observation unavailable for https://github.com/lab/owned/pull/9 - core read returned an unexpected shape' in out
    assert [c['stage'] for c in STATE['calls']].index('core') < [c['stage'] for c in STATE['calls']].index('core-9')
    save(dest, 'schema-isolation')


def issue():
    dest = home('issue', ())
    (dest / 'data/backlog.md').write_text('# Backlog\n\n## Queued\n- [ ] filed - Filed issue https://github.com/lab/owned/issues/9 (repo: sample) (kind: ship)\n')
    reset()
    out, _ = call(dest, 'poll')
    row = record(dest, 'filed')
    assert row['error'] is None and row['observation']['ready'] is True
    assert any(event['type'] == 'ready-for-pr' for event in row['pending'])
    assert STATE['counts']['issue-events'] == 1 and STATE['counts']['comments'] == 1
    save(dest, 'ready-issue')


LAB.mkdir(parents=True, exist_ok=True)
for child in ('tmp', 'empty-trust'): (LAB / child).mkdir(exist_ok=True)
subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-keyout', str(LAB / 'key.pem'), '-out', str(LAB / 'cert.pem'), '-days', '1', '-subj', '/CN=api.github.com', '-addext', 'subjectAltName=DNS:api.github.com,DNS:github.com', '-addext', 'basicConstraints=critical,CA:TRUE'], check=True, capture_output=True)
TLS = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
TLS.load_cert_chain(str(LAB / 'cert.pem'), str(LAB / 'key.pem'))
SERVER = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Forge)
threading.Thread(target=SERVER.serve_forever, daemon=True).start()
try:
    log('Actual binaries: ' + subprocess.check_output(['gh', '--version'], text=True).splitlines()[0])
    log('Isolation: real Firstmate CLI and real gh; disposable home/token/CA; all GitHub HTTPS requests terminated by loopback TLS forge. No real forge or operator credentials used.')
    check('Shared PR owners receive a coherent paginated observation and durable maintainer signals; acknowledgement is exact', coherent)
    check('Transient parallel HTTP 500 reads retry once and recover silently', transient)
    check('Concurrent persistent failures stay stage-sorted, private, episode-deduplicated, and preserve pending/verdict evidence', concurrent)
    check('Oversized, invalid, and truncated HTTP diagnostics cannot fabricate a status or disclose private text', bounded)
    check('Head drift rejects mixed evidence and a deadline-killed core read preserves exact record bytes', guardrails)
    check('Malformed second URL does not inherit the first URL HTTP failure', schema)
    check('Owned issue still observes comments and ready-for-pr timeline events', issue)
    # Reproduce the privacy/order regression through the same real gh transport before the fix.
    baseline = ROOT / 'bin/.fm-contributions-baseline-validation.sh'
    baseline.write_bytes(subprocess.check_output(['git', 'show', '29c3e867b369de8532704e0b54ac988d239a668a:bin/fm-contributions.sh']))
    baseline.chmod(0o700)
    try:
        dest = home('baseline')
        reset('both')
        out, _ = call(dest, 'poll', product=baseline)
        assert SECRET in out and SECRET in record(dest)['error'], 'Expected pre-fix privacy regression not reproduced'
        assert '; statuses read exited' not in out, 'Expected pre-fix missing parallel diagnostic not reproduced'
        save(dest, 'baseline-reproduced')
        log('BASELINE REPRODUCED: raw private forge diagnostic retained, and only one failed parallel read reported; target scenarios reject both behaviors.')
    finally:
        baseline.unlink(missing_ok=True)
finally:
    SERVER.shutdown()
    SERVER.server_close()
    (EVIDENCE / 'live-contributions.log').write_text('\n'.join(TRANSCRIPT) + '\n')
    (EVIDENCE / 'live-scenarios.json').write_text(json.dumps(RESULTS, indent=2))
    shutil.rmtree(LAB)
