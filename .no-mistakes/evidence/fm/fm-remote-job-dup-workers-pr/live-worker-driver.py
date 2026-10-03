import os, subprocess, time, pathlib, shutil, signal, json, base64
W=pathlib.Path.cwd()
L=W/'.live-validation/manual'
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
try:
    log('cold_start',output=call(ensure).stdout)
    wait(ready);o=owner();g=os.getpgid(o);snap('cold_start_persisted_owner')
    job('job_result_before_adversarial_checks')
    # Freeze only the serving loop; its heartbeat child must remain live for >10s.
    os.kill(o,signal.SIGSTOP)
    samples=[]
    for i in range(12):
        time.sleep(1)
        samples.append(round(time.time()-(S/'worker.ready').stat().st_mtime,3))
    starts=[call(ensure).stdout for _ in range(3)]
    snap('serving_stalled_12_seconds')
    assert max(samples)<4 and owner()==o and groups()==[g]
    log('slow_serving_pass_heartbeat_and_repeated_ensure',heartbeat_ages=samples,start_results=starts)
    os.kill(o,signal.SIGCONT);job('job_result_after_serving_resumed')
    # Freeze all writers, age readiness, actively repeat the start boundary.
    os.killpg(g,signal.SIGSTOP);time.sleep(.2)
    os.utime(S/'worker.ready',(946684800,946684800))
    probe=call('fm_remote_job_probe "$HOME"',check=False)
    starts=[call(start).stdout for _ in range(5)]
    snap('all_writers_stopped_aged_readiness')
    assert probe.returncode!=0 and all('repaired=0' in x for x in starts) and owner()==o and groups()==[g]
    log('aged_heartbeat_owner_reused',probe_exit=probe.returncode,start_results=starts)
    os.killpg(g,signal.SIGCONT);call(ensure)
    # Losing supervised workers must preserve the owner's public records.
    keys=['worker.pid','worker.identity','worker.lock/pid','worker.lock/start','worker.lock/command']
    before={k:read(k) for k in keys};inode=(S/'worker.ready').stat().st_ino
    loser_env=env|{'FM_REMOTE_JOB_SUPERVISOR_MAX_RESTARTS':'1','FM_REMOTE_JOB_SUPERVISOR_MAX_BACKOFF_SECONDS':'0'}
    loser=subprocess.run([str(R/'bin/fm-remote-job-worker.sh')],env=loser_env,text=True,capture_output=True,timeout=45,start_new_session=True)
    assert loser.returncode==0 and before=={k:read(k) for k in keys} and inode==(S/'worker.ready').stat().st_ino
    original=read('worker.lock/start');(S/'worker.lock/start').write_text('unverifiable start\n')
    loser_bad=subprocess.run([str(R/'bin/fm-remote-job-worker.sh')],env=loser_env,text=True,capture_output=True,timeout=45,start_new_session=True)
    (S/'worker.lock/start').write_text(original+'\n')
    assert loser_bad.returncode!=0 and before=={k:read(k) for k in keys} and inode==(S/'worker.ready').stat().st_ino
    log('losing_supervisors_preserve_owner',verified_exit=loser.returncode,unverifiable_exit=loser_bad.returncode,unverifiable_stderr=loser_bad.stderr,readiness_inode=inode)
    snap('owner_after_losing_supervisors');job('job_after_losing_supervisors')
    # A real code-identity mismatch is still replaced safely.
    (R/'bin/fm-remote-job-worker.sh').open('a').write('\n')
    log('stale_identity_repair',output=call(ensure).stdout)
    wait(lambda:ready() and owner()!=o)
    assert g not in groups() and len(groups())==1
    snap('replacement_after_real_code_change');job('job_after_stale_code_replacement')
    # Crash held unreaped: the heartbeat must stop refreshing even though kill -0 succeeds.
    o=owner();row=[r for r in procs() if int(r.split()[0])==o][0];supervisor=int(row.split()[1])
    os.kill(supervisor,signal.SIGSTOP);os.kill(o,signal.SIGKILL)
    wait(lambda:subprocess.check_output(['ps','-o','state=','-p',str(o)],text=True).strip().startswith('Z'))
    time.sleep(2)
    first=(S/'worker.ready').stat().st_mtime
    time.sleep(11)
    second=(S/'worker.ready').stat().st_mtime
    probe=call('fm_remote_job_probe "$HOME"',check=False)
    log('unreaped_crash_readiness',zombie_pid=o,supervisor_pid=supervisor,first_mtime=first,second_mtime=second,ready_age=time.time()-second,probe_exit=probe.returncode,processes=procs(),zombie_state=subprocess.check_output(['ps','-o','pid=,ppid=,pgid=,state=','-p',str(o)],text=True).strip())
    assert first==second and probe.returncode!=0
    os.kill(supervisor,signal.SIGCONT);wait(lambda:ready() and owner()!=o,seconds=20)
    call(ensure);snap('crash_replacement_ready');job('job_after_crash_recovery')
    stop();wait(lambda:not procs())
    # Stale records plus an initializing owner whose hashing dependency is delayed.
    call('fm_remote_job_prepare_state "$HOME"')
    lock=S/'worker.lock';lock.mkdir(exist_ok=True)
    for p,v in {'worker.lock/pid':'99999999','worker.lock/start':'stale start','worker.lock/command':'stale command','worker.pid':'99999999','worker.identity':'old identity','worker.ready':'99999999'}.items(): (S/p).write_text(v+'\n')
    for p in (lock,S/'worker.ready'): os.utime(p,(946684800,946684800))
    gate=L/'hash.gate';held=L/'hash.held';gate.touch();shims=A/'.local/bin';shims.mkdir(parents=True,exist_ok=True)
    real_git=shutil.which('git')
    (shims/'git').write_text(f'''#!/usr/bin/env bash
if [ "${{1:-}}" = hash-object ] && [ -e '{gate}' ]; then
  printf 'held\\n' >> '{held}'
  while [ -e '{gate}' ]; do sleep 0.05; done
fi
exec '{real_git}' "$@"
''');(shims/'git').chmod(0o755)
    log('start_with_stale_records',output=call(start).stdout)
    wait(lambda:held.exists());o=owner();g=os.getpgid(o)
    cp=call('fm_remote_job_lock_owner_matches_process "$HOME"; printf "verified=%s\\n" "$?"')
    assert 'verified=0' in cp.stdout
    for p in ('worker.pid','worker.identity','worker.ready'): assert not (S/p).exists()
    starts=[call(start).stdout for _ in range(5)]
    assert all('repaired=0' in x for x in starts) and owner()==o and groups()==[g]
    snap('verified_initializing_owner_before_publication')
    log('initialization_reuses_verified_owner',start_results=starts,verification=cp.stdout)
    gate.unlink();call(ensure);assert owner()==o
    snap('same_initializing_owner_after_publication');job('job_after_initialization')
    log('all_manual_scenarios_passed')
finally:
    gate=L/'hash.gate'
    if gate.exists():gate.unlink()
    stop()
    log('cleanup',remaining_lab_processes=procs())
    (E/'live-worker-state.json').write_text(json.dumps(records,indent=2)+'\n')
    for row in procs():
        try: os.kill(int(row.split()[0]),signal.SIGKILL)
        except ProcessLookupError: pass
    shutil.rmtree(L)
