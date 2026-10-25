#!/usr/bin/env python3
"""Compare committed pre-repair implementations with current executable behavior.
Only disposable source overlays and an isolated native SQLite fixture are used.
No tracked source, history, daemon, or pipeline is modified.
"""
import json
import os
from pathlib import Path
import shutil
import signal
import sqlite3
import subprocess
import tempfile
import time

ROOT=Path.cwd()
EVIDENCE=Path('/home/kasper/.no-mistakes/evidence/01M5RW6VSY3JV2SWKMXPM1X127')
TMP=Path(tempfile.mkdtemp(prefix='baseline-proof-',dir=ROOT/'.test-phase-tmp'))
ENV=os.environ.copy()
for k in ('FM_ROOT_OVERRIDE','FM_STATE_OVERRIDE','FM_DATA_OVERRIDE','FM_CONFIG_OVERRIDE',
          'FM_PROJECTS_OVERRIDE','FM_HOME','NM_HOME','FM_TIMEOUT_MECHANISM_OVERRIDE','TMUX'):
    ENV.pop(k,None)
ENV['TMPDIR']=str(ROOT/'.test-phase-tmp')
BASH=shutil.which('bash')
REAL_NM=shutil.which('no-mistakes')
RUNNER=shutil.which('timeout') or shutil.which('gtimeout')
RESULTS=[]

def run(args,env=None,**kw):
    return subprocess.run([str(x) for x in args],env=env or ENV,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=15,**kw)

def overlay(commit):
    d=TMP/commit/'bin';d.mkdir(parents=True)
    for name in ('fm-nm-run-lib.sh','fm-timeout-lib.sh'):
        p=run(['git','-C',ROOT,'show',f'{commit}:bin/{name}'])
        assert p.returncode==0,p.stderr
        (d/name).write_bytes(p.stdout)
    return d

def path_for(name,external=False):
    d=TMP/name;d.mkdir()
    for tool in ('bash','perl','sleep','dirname','mktemp','cat','rm','git'):
        (d/tool).symlink_to(shutil.which(tool))
    if external:
        (d/external).write_text(f'#!/usr/bin/env bash\nprintf "{external}\\n" >> "{d}/selected"\nexec "{RUNNER}" "$@"\n')
        (d/external).chmod(0o755)
    return d

try:
    # R2: invoke the actual byte-consuming command through old/current libraries.
    old=overlay('3a8d264b')
    payload=b'first line\n\x00\x01\x7f\xff\r\n last \tline\n\n'
    for mode in ('perl','timeout','gtimeout'):
        path=path_for('stdin-'+mode,False if mode=='perl' else mode)
        for version,lib in [('before',old/'fm-nm-run-lib.sh'),('after',ROOT/'bin/fm-nm-run-lib.sh')]:
            p=run([BASH,'-c','. "$1"; PATH=$3 fm_nm_bounded "$2" 5 bash -c "cat"','_',lib,TMP,path],input=payload)
            assert p.returncode==0,(mode,version,p.stderr)
            expected=(version=='after' or mode=='perl')
            assert (p.stdout==payload)==expected,(mode,version,p.stdout)
            if mode!='perl':
                assert (path/'selected').read_text().splitlines()[-1]==mode
            RESULTS.append({'criterion':'stdin unchanged','mode':mode,'version':version,
                            'status':p.returncode,'expected_hex':payload.hex(),'actual_hex':p.stdout.hex(),
                            'bytes_preserved':p.stdout==payload})
            print(json.dumps(RESULTS[-1]),flush=True)

    # R1: lock only our disposable real native database. The real native CLI
    # blocks reading it, while a shorter outer read deadline cancels the query.
    pre=overlay('aeaeee7e')
    path=path_for('query-perl')
    (path/'no-mistakes').write_text(f'#!/usr/bin/env bash\nprintf "%s\\n" "$$" > "$QUERY_PID"\nexec "{REAL_NM}" "$@"\n')
    (path/'no-mistakes').chmod(0o755)
    nmhome=TMP/'native-home'
    project=TMP/'native-project'
    native_env=dict(ENV,NM_HOME=str(nmhome),GIT_CONFIG_GLOBAL='/dev/null',GIT_CONFIG_NOSYSTEM='1')
    assert run(['git','init','-q','-b','fm/retained',project],native_env).returncode==0
    assert run(['git','-C',project,'-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-q','--allow-empty','-m','disposable native data'],native_env).returncode==0
    head=run(['git','-C',project,'rev-parse','HEAD'],native_env).stdout.decode().strip()
    run(['no-mistakes','runs','--limit','1'],native_env,cwd=project)
    seed=sqlite3.connect(nmhome/'state.sqlite')
    now=int(time.time())
    seed.execute('INSERT INTO repos (id,working_path,upstream_url,created_at) VALUES (?,?,?,?)',('fixture-repo',str(project),'https://example.invalid/fixture.git',now))
    seed.execute('INSERT INTO runs (id,repo_id,branch,head_sha,base_sha,status,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?)',('fixture-failed','fixture-repo','fm/retained',head,head,'failed',now,now))
    seed.commit();seed.close()
    env=dict(native_env,PATH=str(path),FM_HOME=str(TMP))
    lock=sqlite3.connect(nmhome/'state.sqlite')
    lock.execute('PRAGMA journal_mode=DELETE')
    lock.execute('BEGIN EXCLUSIVE')
    try:
        for version,lib in [('before',pre/'fm-nm-run-lib.sh'),('after',ROOT/'bin/fm-nm-run-lib.sh')]:
            pidfile=TMP/(version+'-native-pid')
            qenv=dict(env,QUERY_PID=str(pidfile))
            script='''. "$1/bin/fm-timeout-lib.sh"
FM_TIMEOUT_MECHANISM_OVERRIDE=perl fm_run_timed 2 bash -c '
  . "$1"
  fm_nm_run_checked "$2" 60 axi status --run fixture-failed
' _ "$2" "$3"
'''
            with open(TMP/(version+'-native-output'),'wb') as output:
                p=subprocess.Popen([BASH,'-c',script,'_',str(ROOT),str(lib),str(project)],env=qenv,
                                   stdout=output,stderr=output)
                for _ in range(150):
                    if pidfile.exists():break
                    time.sleep(.01)
                assert pidfile.exists(),f'{version}: native query did not start'
                pid=int(pidfile.read_text())
                during=run(['ps','-o','pid,ppid,pgid,stat,comm','-p',pid]).stdout.decode().strip()
                status=p.wait(timeout=10)
            assert status==124,(version,status)
            time.sleep(.1)
            state=run(['ps','-o','stat=','-p',pid]).stdout.decode().strip()
            survived=bool(state and 'Z' not in state)
            detail=run(['ps','-o','pid,ppid,pgid,stat,comm','-p',pid]).stdout.decode().strip()
            RESULTS.append({'criterion':'actual native query cancellation','version':version,
                            'outer_status':status,'pid':pid,'during':during,'after':detail,
                            'survived_outer_deadline':survived})
            print(json.dumps(RESULTS[-1]),flush=True)
            if survived:os.kill(pid,signal.SIGKILL)
            assert survived==(version=='before'),(version,state)
    finally:
        lock.rollback();lock.close()
finally:
    (EVIDENCE/'baseline-results.json').write_text(json.dumps(RESULTS,indent=2)+'\n')
    shutil.rmtree(TMP)
