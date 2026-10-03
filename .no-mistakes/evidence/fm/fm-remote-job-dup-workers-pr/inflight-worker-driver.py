import os, subprocess, time, pathlib, shutil, signal, json, base64
W=pathlib.Path.cwd()
L=W/'.live-validation/inflight'
E=pathlib.Path('/home/kasper/.no-mistakes/evidence/01M41V7EYAFYWNGJKACA3TXXPB')
R=L/'root'; A=L/'account'; H=L/'home'; S=L/'state'
for p in (R/'bin',A,H,S,L/'tmp'): p.mkdir(parents=True,exist_ok=True)
for name in ('fm-remote-job-lib.sh','fm-remote-job-worker.sh'):
    shutil.copy2(W/'bin'/name,R/'bin'/name)
shutil.copy2(W/'AGENTS.md',R/'AGENTS.md')
(R/'bin/fm-lab-echo.sh').write_text('''#!/usr/bin/env bash
printf 'argv=<%s>\n' "$@"
printf 'active=%s\n' "$FM_REMOTE_JOB_ACTIVE"
while IFS= read -r line; do printf 'stdin=<%s>\n' "$line"; done
printf 'worker stderr preserved\n' >&2
exit 7
''')
(R/'bin/fm-lab-echo.sh').chmod(0o755)
env={k:v for k,v in os.environ.items() if not k.startswith(('FM_','TASKS_AXI_'))}
env.update(HOME=str(A),FM_HOME=str(H),FM_ROOT_OVERRIDE=str(R),FM_REMOTE_JOB_STATE_ROOT=str(S),FM_REMOTE_JOB_PLATFORM_OVERRIDE='Linux',TMPDIR=str(L/'tmp'),GIT_CONFIG_GLOBAL='/dev/null',GIT_CONFIG_NOSYSTEM='1')
subprocess.run(['git','init','-q',str(R)],env=env,check=True)
subprocess.run(['git','-C',str(R),'add','AGENTS.md','bin'],env=env,check=True)
records=[]
def log(name,**details):
    rec={'event':name,**details};records.append(rec); print(json.dumps(rec),flush=True)
def call(script,check=True,timeout=60,input=None):
    cp=subprocess.run(['bash','-c','source "$FM_ROOT_OVERRIDE/bin/fm-remote-job-lib.sh"\n'+script],env=env,text=True,input=input,capture_output=True,timeout=timeout)
    if check and cp.returncode: raise RuntimeError(f'{script}: {cp.returncode}: {cp.stdout}: {cp.stderr}')
    return cp
start='FM_REMOTE_JOB_REPAIRED=0; fm_remote_job_start_linux_worker "$FM_ROOT_OVERRIDE" "$HOME" || exit 1; printf "repaired=%s owner=%s\\n" "$FM_REMOTE_JOB_REPAIRED" "${FM_REMOTE_JOB_OWNER_PID:-new}"'
ensure='fm_remote_job_ensure_worker "$FM_ROOT_OVERRIDE" "$HOME" || { printf "%s\\n" "$FM_REMOTE_JOB_ERROR"; exit 1; }; printf "ready owner=%s repaired=%s\\n" "$(cat "$FM_REMOTE_JOB_STATE_ROOT/worker.pid")" "$FM_REMOTE_JOB_REPAIRED"'
def read(p): return (S/p).read_text().strip()
def owner(): return int(read('worker.lock/pid'))
def wait(cond,seconds=12):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        try:
            if cond(): return
        except (FileNotFoundError,ValueError): pass
        time.sleep(.05)
    raise RuntimeError('condition timed out')
def ready(): return (S/'worker.ready').exists() and (S/'worker.pid').exists()
def procs():
    output=subprocess.check_output(['ps','-eo','pid=,ppid=,pgid=,state=,args='],text=True)
    return [row.strip() for row in output.splitlines() if str(R/'bin/fm-remote-job-worker.sh') in row]
def groups(): return sorted({int(row.split()[2]) for row in procs()})
def snap(label):
    state={p: read(p) if (S/p).exists() else None for p in ('worker.pid','worker.identity','worker.ready','worker.lock/pid','worker.lock/start','worker.lock/command')}
    if (S/'worker.ready').exists(): state['ready_age_seconds']=round(time.time()-(S/'worker.ready').stat().st_mtime,3)
    log(label,state=state,processes=procs())
def job(label):
    cp=call('fm_remote_job_stage "$HOME" "$FM_ROOT_OVERRIDE" "$FM_HOME" fm-lab-echo.sh "two words" "literal argument" >/dev/null || exit 1\nprintf "job=%s\\n" "$FM_REMOTE_JOB_ID"\nfm_remote_job_wait "$HOME" "$FM_REMOTE_JOB_ID" || exit 1\nprintf "job_exit=%s\\n" "$FM_REMOTE_JOB_EXIT"\ncat "$FM_REMOTE_JOB_STDOUT"\ncat "$FM_REMOTE_JOB_STDERR" >&2\nfm_remote_job_reap "$HOME" "$FM_REMOTE_JOB_ID"', input='first line\nsecond line\n')
    # Avoid executing a shell-looking string in the driver: literal argv is provided separately below.
    assert 'job_exit=7' in cp.stdout and 'active=1' in cp.stdout and 'stdin=<second line>' in cp.stdout
    assert 'worker stderr preserved' in cp.stderr
    log(label,stdout=cp.stdout,stderr=cp.stderr)
def stop():
    rows=procs()
    for pgid in {int(row.split()[2]) for row in rows}:
        if pgid!=os.getpgrp():
            try: os.killpg(pgid,signal.SIGCONT);os.killpg(pgid,signal.SIGTERM)
            except ProcessLookupError: pass
    for row in procs():
        try: os.kill(int(row.split()[0]),signal.SIGCONT);os.kill(int(row.split()[0]),signal.SIGTERM)
        except ProcessLookupError: pass
    time.sleep(.5)
    for pgid in {int(row.split()[2]) for row in procs()}:
        if pgid!=os.getpgrp():
            try: os.killpg(pgid,signal.SIGKILL)
            except ProcessLookupError: pass
gate=L/'refresh.gate';held=L/'refresh.held';released=L/'refresh.released';shims=L/'tools';shims.mkdir()
real_touch=shutil.which('touch')
(shims/'touch').write_text(f'''#!/usr/bin/env bash
held=0
if [ -e '{gate}' ] && mkdir '{gate}.claim' 2>/dev/null; then
  held=1
  printf '%s\\n' "$PPID" > '{held}'
  while [ -e '{gate}' ]; do sleep 0.05; done
fi
'{real_touch}' "$@"
status=$?
[ "$held" -eq 0 ] || printf 'released\\n' > '{released}'
exit "$status"
''')
(shims/'touch').chmod(0o755)
env['PATH']=str(shims)+':'+env['PATH']
try:
    for replacements in (False,True):
        env['FM_REMOTE_JOB_SUPERVISOR_MAX_RESTARTS']='2' if replacements else '1'
        env['FM_REMOTE_JOB_SUPERVISOR_MAX_BACKOFF_SECONDS']='0'
        for marker in (held,released):
            if marker.exists():marker.unlink()
        claim=L/'refresh.gate.claim'
        if claim.exists():claim.rmdir()
        sup=subprocess.Popen([str(R/'bin/fm-remote-job-worker.sh')],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,start_new_session=True)
        wait(ready);o=owner();original_inode=(S/'worker.ready').stat().st_ino
        gate.touch();wait(lambda:held.exists());heartbeat=int(held.read_text().strip())
        os.kill(o,signal.SIGKILL)
        if replacements:
            wait(lambda:ready() and owner()!=o)
            replacement=owner();new_inode=(S/'worker.ready').stat().st_ino
            bound_inode=os.stat(f'/proc/{heartbeat}/fd/3').st_ino
            log('refresh_bound_across_replacement',crashed_owner=o,replacement_owner=replacement,old_inode=original_inode,new_inode=new_inode,bound_inode=bound_inode,bound_path=os.readlink(f'/proc/{heartbeat}/fd/3'))
            assert bound_inode==original_inode and new_inode!=original_inode
            os.kill(sup.pid,signal.SIGKILL);sup.wait(timeout=5)
            os.kill(replacement,signal.SIGKILL);time.sleep(2)
            os.utime(S/'worker.ready',(946684800,946684800))
        else:
            sup.wait(timeout=10)
            assert not (S/'worker.ready').exists() and not (S/'worker.lock').exists()
            log('crash_cleanup_before_held_refresh_released',owner=o,ready_exists=False,lock_exists=False)
        gate.unlink();wait(lambda:released.exists());time.sleep(.25)
        cp=call('fm_remote_job_probe "$HOME"',check=False)
        log('held_refresh_after_release',replacement=replacements,probe_exit=cp.returncode,ready_exists=(S/'worker.ready').exists(),ready_mtime=(S/'worker.ready').stat().st_mtime if (S/'worker.ready').exists() else None,processes=procs())
        assert cp.returncode!=0
        if replacements: assert (S/'worker.ready').stat().st_mtime==946684800
        else: assert not (S/'worker.ready').exists()
        stop()
        shutil.rmtree(S);S.mkdir()
    log('inflight_refresh_scenarios_passed')
finally:
    if gate.exists():gate.unlink()
    stop();log('inflight_cleanup',remaining_lab_processes=procs())
    (E/'inflight-worker-state.json').write_text(json.dumps(records,indent=2)+'\n')
    shutil.rmtree(L)
