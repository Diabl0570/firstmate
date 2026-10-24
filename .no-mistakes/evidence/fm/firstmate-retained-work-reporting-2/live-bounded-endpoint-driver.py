#!/usr/bin/env python3
"""Suspend only the owned lab tmux server; observe real blocked read descendants."""
import json
import os
from pathlib import Path
import signal
import subprocess
import time

root = Path.cwd()
evidence = Path('/home/kasper/.no-mistakes/evidence/01M5P91F5H9J68964T99S351S3')
lab = Path(os.environ['FM_HOME'])
server = int(subprocess.check_output(['tmux', '-L', 'fm-lab', 'display-message', '-p', '-t', 'primary', '#{pid}'], text=True).strip())

def process_table():
    out = subprocess.check_output(['ps', '-eo', 'pid=,ppid=,pgid=,stat=,args='], text=True)
    rows = {}
    for line in out.splitlines():
        parts = line.strip().split(None, 4)
        if len(parts) == 5:
            rows[int(parts[0])] = {'pid': int(parts[0]), 'ppid': int(parts[1]), 'pgid': int(parts[2]), 'state': parts[3], 'args': parts[4]}
    return rows

results = []
# Only real installed executables are linked; no shim replaces a product dependency.
perl_bin = lab / 'perl-bin'
perl_bin.mkdir()
for tool in ['perl', 'bash', 'sleep', 'mktemp', 'rm', 'cat', 'jq', 'awk', 'basename', 'chmod', 'cmp', 'cp', 'cut', 'date', 'dirname', 'env', 'expr', 'find', 'grep', 'head', 'id', 'ln', 'ls', 'mkdir', 'mv', 'ps', 'readlink', 'rmdir', 'sed', 'sh', 'sort', 'stat', 'tail', 'touch', 'tr', 'uname', 'wc', 'xargs', 'tmux']:
    path = subprocess.check_output(['bash', '-c', 'command -v "$1"', '_', tool], text=True).strip()
    (perl_bin / tool).symlink_to(path)

try:
    os.kill(server, signal.SIGSTOP)
    for mode in ['native', 'perl', 'bash']:
        env = dict(os.environ, FM_SNAPSHOT_CREW_STATE_TIMEOUT='1')
        if mode == 'perl':
            env['PATH'] = str(perl_bin)
        if mode == 'bash':
            env['FM_TIMEOUT_MECHANISM_OVERRIDE'] = 'bash'
        started = time.monotonic()
        p = subprocess.Popen([str(root / 'bin/fm-fleet-snapshot.sh'), '--json'], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        observed = {}
        while p.poll() is None and time.monotonic() - started < 20:
            table = process_table()
            family = {p.pid}
            while True:
                children = {pid for pid, row in table.items() if row['ppid'] in family}
                if children <= family:
                    break
                family |= children
            observed.update({pid: table[pid] for pid in family if pid in table})
            time.sleep(0.025)
        if p.poll() is None:
            p.kill()
            raise AssertionError(f'{mode}: snapshot did not return within its safety ceiling')
        stdout, stderr = p.communicate(timeout=2)
        duration = time.monotonic() - started
        (evidence / f'live-stalled-{mode}.json').write_text(stdout)
        data = json.loads(stdout)
        task = data['tasks'][0]
        assert p.returncode == 0, (mode, p.returncode, stderr)
        assert not stderr, (mode, stderr)
        assert task['current_state']['state'] == 'unknown', (mode, task)
        assert task['endpoint']['exists'] is None, (mode, task)
        assert task['runtime_activity']['state'] == 'unknown', (mode, task)
        assert task['runtime_activity']['source'] == 'endpoint-unverified', (mode, task)
        assert task['hints']['pending_decision'] is True, (mode, task)
        # Poll actual observed PIDs, distinguishing inert zombies from running leaks.
        deadline = time.monotonic() + 3
        while True:
            table = process_table()
            leftovers = [table[pid] for pid in observed if pid in table and not table[pid]['state'].startswith('Z')]
            if not leftovers or time.monotonic() >= deadline:
                break
            time.sleep(0.05)
        blocked_clients = [r for r in observed.values() if r['args'].startswith('tmux ')]
        assert blocked_clients, (mode, 'no actual blocked tmux client was observed')
        assert not leftovers, (mode, leftovers)
        record = {'mechanism': mode, 'snapshot_returncode': p.returncode, 'elapsed_seconds': round(duration, 3), 'observed_blocked_tmux_clients': blocked_clients, 'remaining_live_descendants': leftovers, 'current_state': task['current_state'], 'runtime_activity': task['runtime_activity'], 'endpoint': task['endpoint'], 'pending_decision': task['hints']['pending_decision'], 'stderr': stderr}
        results.append(record)
        print(json.dumps(record, indent=2), flush=True)
finally:
    os.kill(server, signal.SIGCONT)
    (evidence / 'live-endpoint-process-evidence.json').write_text(json.dumps(results, indent=2) + '\n')
