import os, subprocess, time, pathlib, shutil, signal, json, base64
W=pathlib.Path.cwd()
L=W/'.live-validation/baseline'
E=pathlib.Path('/home/kasper/.no-mistakes/evidence/01M41V7EYAFYWNGJKACA3TXXPB')
R=L/'root'; A=L/'account'; H=L/'home'; S=L/'state'
for p in (R/'bin',A,H,S,L/'tmp'): p.mkdir(parents=True,exist_ok=True)
for name in ('fm-remote-job-lib.sh','fm-remote-job-worker.sh'):
    (R/'bin'/name).write_bytes(subprocess.check_output(['git','show','1f3e769616fdf9f31f85f4c3e6a9f71606634238:bin/'+name])); (R/'bin'/name).chmod(0o755)
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
observer=L/'observe'; observer.mkdir()
real_nohup=shutil.which('nohup')
(observer/'nohup').write_text(f'''#!/usr/bin/env bash
printf 'pid=%s launch=' "$$" >> '{L/'nohup-launches'}'
printf '%s ' "$@" >> '{L/'nohup-launches'}'
printf '\n' >> '{L/'nohup-launches'}'
exec '{real_nohup}' "$@"
''')
(observer/'nohup').chmod(0o755)
env['PATH']=str(observer)+':'+env['PATH']
try:
    log('base_cold_start',output=call(ensure).stdout)
    wait(ready);o=owner();g=os.getpgid(o)
    os.kill(o,signal.SIGSTOP)
    time.sleep(12)
    probe=call('fm_remote_job_probe "$HOME"',check=False)
    snap('base_serving_stalled_12_seconds')
    log('base_slow_pass_loses_readiness',probe_exit=probe.returncode)
    assert probe.returncode!=0
    os.kill(o,signal.SIGCONT);call(ensure)
    os.killpg(g,signal.SIGSTOP);time.sleep(.2)
    os.utime(S/'worker.ready',(946684800,946684800))
    result=call(start).stdout
    time.sleep(.2)
    snap('base_repeated_start_with_aged_readiness')
    log('base_start_launches_beside_verified_live_owner',output=result,worker_groups=groups(),original_group=g)
    assert 'repaired=1' in result
    log('base_supervisor_launch_transcript',launches=(L/'nohup-launches').read_text())
    assert len((L/'nohup-launches').read_text().splitlines())==2
finally:
    stop()
    log('base_cleanup',remaining_lab_processes=procs())
    (E/'base-worker-state.json').write_text(json.dumps(records,indent=2)+'\n')
    shutil.rmtree(L)
