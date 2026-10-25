#!/usr/bin/env python3
"""Execute Firstmate CLIs and real bounded processes against disposable local data.
The tmux endpoint is a real sleep process, not an impersonated harness or login.
Run from the gate worktree: python3 <this-file>
"""
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile
import time

ROOT = Path.cwd()
EVIDENCE = Path('/home/kasper/.no-mistakes/evidence/01M5RW6VSY3JV2SWKMXPM1X127')
BASE = os.environ.copy()
for key in ('FM_ROOT_OVERRIDE', 'FM_STATE_OVERRIDE', 'FM_DATA_OVERRIDE',
            'FM_CONFIG_OVERRIDE', 'FM_PROJECTS_OVERRIDE', 'FM_HOME', 'NM_HOME',
            'TMUX', 'FM_GATE_REFUSE_BYPASS', 'FM_TEST_SEAM', 'TASKS_AXI_FILE',
            'TASKS_AXI_BACKEND'):
    BASE.pop(key, None)
BASE['TMPDIR'] = str(ROOT / '.test-phase-tmp')
RESULTS = []

def run(args, env=None, input=None, check=True, timeout=40):
    p = subprocess.run([str(a) for a in args], cwd=ROOT, env=env or BASE,
                       input=input, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       timeout=timeout)
    if check and p.returncode:
        raise AssertionError(f'{args}: status={p.returncode}\n{p.stderr.decode(errors="replace")}')
    return p

def save(name, obj):
    (EVIDENCE / name).write_text(json.dumps(obj, indent=2) + '\n')

def record(name, details):
    RESULTS.append({'name': name, 'result': 'pass', 'details': details})
    print(name + ': ' + json.dumps(details), flush=True)


def reporting():
    lab = ROOT / '.l'
    parent = ROOT / '.test-phase-tmp' / 'live-parent'
    run(['bin/fm-lab-home.sh', 'create', lab])
    (lab / 'tmux').mkdir()
    tenv = dict(BASE, TMUX_TMPDIR=str(lab / 'tmux'))
    tmux = ['tmux', '-L', 'fm-lab']
    try:
        # This endpoint supplies real tmux inventory/process evidence; it is not
        # a pretend Claude agent. Ambiguous process evidence cannot prove death.
        cmd = 'printf "%s" "$TMUX" > "$FM_HOME/tmux-env"; exec sleep 300'
        run(tmux + ['new-session', '-d', '-s', 'reporting', '-n', 'task',
                    '-x', '120', '-y', '40', '-c', ROOT, '-e', f'FM_HOME={lab}',
                    'bash', '-c', cmd], tenv)
        for _ in range(100):
            if (lab / 'tmux-env').exists():
                break
            time.sleep(.05)
        env = dict(BASE, FM_HOME=str(lab), TMUX=(lab / 'tmux-env').read_text(),
                   FM_ROOT_OVERRIDE=str(ROOT / '.test-phase-tmp/code-root'))
        (lab / 'projects/review').mkdir()
        (lab / 'data/review').mkdir()
        (lab / 'data/review/report.md').write_text('# Disposable review\nA completed synthetic review report.\n')
        backlog = ('## In flight\n'
                   '- [ ] review - Completed review awaiting approval (repo: sample) (kind: scout) '
                   '(hold: approve follow-up) (hold-kind: captain)\n\n## Queued\n\n## Done\n')
        (lab / 'data/backlog.md').write_text(backlog)
        (lab / 'state/review.meta').write_text(
            'window=reporting:task\nbackend=tmux\n'
            f'worktree={lab}/projects/review\nproject=sample\nharness=claude\nkind=scout\nmode=scout\n')
        (lab / 'state/review.status').write_text('done: report delivered\n')
        gen = run(['bin/fm-busy-event.sh', 'arm', lab / 'state', 'review'], env).stdout.decode().strip()
        run(['bin/fm-busy-event.sh', 'apply', lab / 'state', 'review', 'idle',
             '--gen', gen, '--source', 'claude-hook', '--event', 'stop'], env)

        def snapshot(name, parent_mode=False):
            args = ['bin/fm-fleet-snapshot.sh', '--json' if parent_mode else '--secondmate-home-summary']
            data = json.loads(run(args, penv if parent_mode else env).stdout)
            save(name + '.json', data)
            return data

        s = snapshot('live-retained-scout')
        assert s['valid'] and s['state'] == 'captain_decision', s
        assert s['retained_attempts'][0]['id'] == 'review', s
        assert s['retained_attempts'][0]['runtime_activity']['state'] == 'idle', s
        assert s['counts']['landed'] == 0 and not s['active_children'], s
        assert any(x['id'] == 'review' for x in s['holds']), s
        assert any(x['id'] == 'review' for x in s['decisions_open']), s
        record('Real snapshot retains a completed scout without completing logical work',
               {'retained': s['retained_attempts'], 'state': s['state'], 'landed': s['counts']['landed']})

        run(['bin/fm-home-summary-refresh.sh'], env)
        parent.mkdir()
        for d in ('state', 'data', 'config', 'projects'):
            (parent / d).mkdir()
        # A seeded home's memory is a fixture copy, never an edit to project memory.
        shutil.copyfile(ROOT / 'AGENTS.md', lab / 'AGENTS.md')
        (lab / 'bin').mkdir()
        (lab / '.fm-secondmate-home').write_text('mate\n')
        (parent / 'data/secondmates.md').write_text(
            f'- mate - Disposable reporting home (home: {lab}; scope: fixture; projects: sample; added 2026-10-25)\n')
        penv = dict(env, FM_HOME=str(parent))
        p = snapshot('live-parent-retained', True)['secondmate_current']['records'][0]
        assert p['retained_attempts'][0]['id'] == 'review' and p['provenance']['trust'] == 'complete', p
        ledger = json.loads((lab / 'state/home-summary.json').read_text())
        legacy = dict(ledger)
        legacy.pop('retained_attempts')
        legacy['counts'] = dict(legacy['counts'])
        legacy['counts'].pop('retained_attempts')
        (lab / 'state/home-summary.json').write_text(json.dumps(legacy))
        p = snapshot('live-parent-legacy', True)['secondmate_current']['records'][0]
        assert p['retained_attempts'] is None and p['provenance']['trust'] == 'complete', p
        (lab / 'state/home-summary.json').write_text(json.dumps(dict(legacy, retained_attempts={})))
        p = snapshot('live-parent-malformed', True)['secondmate_current']['records'][0]
        assert p['retained_attempts'] is None and p['current']['state'] == 'unknown', p
        record('Real parent accepts legacy missing coverage and refuses malformed coverage',
               {'legacy_retained_attempts': None, 'malformed_state': p['current']['state']})

        (lab / 'data/backlog.md').write_text(backlog.replace(' (hold: approve follow-up) (hold-kind: captain)', ''))
        s = snapshot('live-terminal-without-hold')
        assert not s['valid'] and s['invalidity']['kind'] == 'terminal_in_flight' and not s['retained_attempts'], s
        (lab / 'data/backlog.md').write_text(backlog)
        (lab / 'state/review.busy-state').unlink()
        (lab / 'state/review.status').write_text('done: report delivered\nneeds-decision [key=follow-up]: choose next action\n')
        s = snapshot('live-missing-activity')
        assert not s['valid'] and not s['retained_attempts'], s
        assert any(x.get('key') == 'follow-up' for x in s['decisions_open']), s
        assert (lab / 'data/review/report.md').exists()
        record('Missing activity or a missing hold never fabricates retained completion',
               {'state': s['state'], 'invalidity': s['invalidity'], 'decisions_open': s['decisions_open']})

        gen = run(['bin/fm-busy-event.sh', 'arm', lab / 'state', 'review'], env).stdout.decode().strip()
        run(['bin/fm-busy-event.sh', 'apply', lab / 'state', 'review', 'busy',
             '--gen', gen, '--source', 'claude-hook', '--event', 'user-prompt-submit'], env)
        run(tmux + ['kill-window', '-t', 'reporting:task'], tenv)
        data = json.loads(run(['bin/fm-fleet-snapshot.sh', '--json'], env).stdout)
        save('live-dead-endpoint.json', data)
        task = data['tasks'][0]
        assert task['runtime_activity']['state'] == 'dead' and task['runtime_activity']['source'] == 'endpoint-gone', task
        assert task['hints']['pending_decision'], task
        record('Real endpoint disappearance overrides stale busy evidence without answering an open call',
               {'runtime_activity': task['runtime_activity'], 'open_decisions': task['hints']['open_decisions']})
    finally:
        run(tmux + ['kill-server'], tenv, check=False)
        shutil.rmtree(lab)
        if parent.exists():
            shutil.rmtree(parent)


def bounded():
    scratch = Path(tempfile.mkdtemp(prefix='live-bounds-', dir=ROOT / '.test-phase-tmp'))
    try:
        runner = shutil.which('timeout') or shutil.which('gtimeout')
        payload = b'first line\n\x00\x01\x7f\xff\r\n last \tline\n\n'
        for mode in ('perl', 'timeout', 'gtimeout'):
            if mode != 'perl' and runner is None:
                raise RuntimeError('No external timeout runner available')
            d = scratch / mode
            path = d / 'bin'
            path.mkdir(parents=True)
            for tool in ('bash', 'perl', 'sleep', 'dirname', 'mktemp', 'cat', 'rm'):
                (path / tool).symlink_to(shutil.which(tool))
            if mode != 'perl':
                # A name-selection adapter only: the installed normal executable
                # enforces the actual timeout, preserving its real argv[0].
                (path / mode).write_text(f'#!/usr/bin/env bash\nprintf "{mode}\\n" >> "{d}/runner-used"\nexec "{runner}" "$@"\n')
                (path / mode).chmod(0o755)
            env = dict(BASE, PATH=str(path))
            script = '. "$1/bin/fm-nm-run-lib.sh"; fm_nm_bounded "$2" 5 bash -c \'cat; echo actual-command-stderr >&2; exit 7\''
            p = run([shutil.which('bash'), '-c', script, '_', ROOT, d], env, input=payload, check=False)
            assert p.returncode == 7 and p.stdout == payload and p.stderr == b'actual-command-stderr\n', (mode, p)
            if mode != 'perl':
                assert (d / 'runner-used').read_text().strip() == mode
            record(f'Real bounded command preserves stdin, stdout, stderr and status ({mode})',
                   {'status': p.returncode, 'input_hex': payload.hex(), 'output_hex': p.stdout.hex(), 'stderr': p.stderr.decode()})
            pidfile = d / 'pid'
            script = r'''. "$1/bin/fm-timeout-lib.sh"
FM_TIMEOUT_MECHANISM_OVERRIDE=perl fm_run_timed 2 bash -c '
  . "$1/bin/fm-nm-run-lib.sh"
  fm_nm_bounded "$2" 60 bash -c '\''trap "" TERM; echo $$ > "$1"; exec sleep 300'\'' _ "$3"
' _ "$1" "$2" "$3"
'''
            p = run([shutil.which('bash'), '-c', script, '_', ROOT, d, pidfile], env, check=False, timeout=15)
            assert p.returncode == 124 and pidfile.exists(), (mode, p)
            pid = int(pidfile.read_text())
            stat = run(['ps', '-o', 'stat=', '-p', pid], check=False).stdout.decode().strip()
            if stat and 'Z' not in stat:
                os.kill(pid, signal.SIGKILL)
                raise AssertionError(f'{mode}: descendant {pid} survived: {stat}')
            record(f'Actual nested bounded read leaves no executing descendant ({mode})',
                   {'outer_status': p.returncode, 'actual_command_pid': pid, 'process_state': stat or 'gone'})
    finally:
        shutil.rmtree(scratch)

try:
    reporting()
    bounded()
finally:
    save('live-results.json', RESULTS)
