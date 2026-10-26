#!/usr/bin/env python3
"""Drive real Firstmate CLIs and a real private tmux/Claude endpoint.
Native no-mistakes read responses are disposable external-service fixtures;
no no-mistakes pipeline is started or controlled. All fixture data is in cwd.
"""
import json, os, pathlib, shutil, signal, subprocess, time, traceback
ROOT = pathlib.Path.cwd()
EVIDENCE = pathlib.Path('/home/kasper/.no-mistakes/evidence/01M5TJBFSWYT4F8Y8RTZR679NX')
# Keep the Unix-domain socket under Linux's sockaddr_un path limit.
LAB = ROOT/'.l'
LAB.mkdir(mode=0o700)
env = dict(os.environ)
for key in list(env):
    if key.startswith(('FM_', 'TASKS_', 'GIT_')) or key in ('NM_HOME', 'TMUX', 'TMUX_TMPDIR'):
        env.pop(key, None)
env.update(FM_HOME=str(LAB), NM_HOME=str(LAB/'native-home'), TMPDIR=str(LAB/'tmp'), GIT_CONFIG_GLOBAL='/dev/null', GIT_CONFIG_NOSYSTEM='1', GIT_AUTHOR_NAME='Fixture', GIT_AUTHOR_EMAIL='fixture@example.invalid', GIT_COMMITTER_NAME='Fixture', GIT_COMMITTER_EMAIL='fixture@example.invalid')
results = []
started = False

def run(args, *, e=None, cwd=ROOT, check=True, timeout=60):
    p = subprocess.run([str(x) for x in args], env=e or env, cwd=cwd, text=True, capture_output=True, timeout=timeout)
    if check and p.returncode:
        raise RuntimeError(f'{args}: {p.returncode}\n{p.stdout}\n{p.stderr}')
    return p

def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)

def tmux(*args, check=True):
    return run(['tmux','-L','fm-lab',*args], check=check)

def artifact(name, data):
    (EVIDENCE/name).write_text(json.dumps(data, indent=2)+'\n' if not isinstance(data,str) else data)

def snapshot(name, **extra):
    t=time.monotonic()
    p=run([ROOT/'bin/fm-fleet-snapshot.sh','--secondmate-home-summary'], e=env|extra)
    data=json.loads(p.stdout)
    artifact(name+'.json',data)
    return data, time.monotonic()-t

def record(name, state='idle'):
    gen=run([ROOT/'bin/fm-busy-event.sh','arm',LAB/'state',name]).stdout.strip()
    run([ROOT/'bin/fm-busy-event.sh','apply',LAB/'state',name,state,'--gen',gen,'--source','claude-hook','--event','stop' if state=='idle' else 'user-prompt-submit'])

def native(name, state, duplicate=False):
    wt=LAB/'projects'/name
    head=run(['git','rev-parse','HEAD'],cwd=wt).stdout.strip()
    rows=[('native-'+name,'fm/'+name,state,head)]
    if duplicate: rows.append(('other-'+name,'fm/'+name,'running',head))
    overview=f'count: {len(rows)} of {len(rows)} total\nruns[{len(rows)}]{{id,branch,status,head,pr}}:\n'+''.join(f'  {i},{b},{s},{h},\n' for i,b,s,h in rows)
    detail=f'id: native-{name}\nbranch: fm/{name}\nstatus: {state}\nhead: {head}\n'
    write(wt/'native.json',json.dumps({'overview':overview,'detail':detail}))

try:
    run([ROOT/'bin/fm-lab-home.sh','create',LAB])
    (LAB/'tmp').mkdir()
    (LAB/'tmux').mkdir()
    write(LAB/'config/supervision-host-off','')
    env['TMUX_TMPDIR']=str(LAB/'tmux')
    launch_env=dict(env)
    for k in ('NO_MISTAKES_GATE','FM_GATE_REFUSE_BYPASS','FM_ROOT_OVERRIDE','FM_STATE_OVERRIDE','FM_DATA_OVERRIDE','FM_CONFIG_OVERRIDE','FM_PROJECTS_OVERRIDE'):
        launch_env.pop(k,None)
    run(['tmux','-L','fm-lab','new-session','-d','-s','primary','-x','120','-y','36','-c',ROOT,'-e','FM_HOME='+str(LAB),'claude'],e=launch_env)
    started=True
    time.sleep(5)
    pane=tmux('capture-pane','-p','-t','primary').stdout
    artifact('claude-private-pane.txt',pane)
    socket=tmux('display-message','-p','-t','primary','#{socket_path}').stdout.strip()
    server=tmux('display-message','-p','-t','primary','#{pid}').stdout.strip()
    window=tmux('display-message','-p','-t','primary','#{window_name}').stdout.strip()
    target='primary:'+window
    env['TMUX']=socket+','+server+',0'
    alive=run(['bash','-c','. "$1"; fm_backend_agent_alive tmux "$2"','_',ROOT/'bin/fm-backend.sh',target]).stdout.strip()
    artifact('endpoint-live.txt',f'private_socket={socket}\nwindow={target}\nrecovery_grade_agent_alive={alive}\npty_grid=120x36\n'+pane)
    assert alive=='alive', 'Actual Claude endpoint did not become recovery-grade alive'
    # Native read fixture is an external dependency, not Firstmate implementation.
    fake=LAB/'external-native'
    fake.mkdir()
    write(fake/'no-mistakes','''#!/usr/bin/env python3
import json, pathlib, sys, os, signal, time
p=pathlib.Path.cwd()
if (p/'stall').exists():
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    (p/'query.pid').write_text(str(os.getpid()))
    time.sleep(300)
a=sys.argv[1:]
if a==['daemon','status']: print('daemon running')
elif a==['axi']: print(json.loads((p/'native.json').read_text())['overview'],end='')
elif a[:2]==['axi','status']: print(json.loads((p/'native.json').read_text())['detail'],end='')
else: sys.exit(1)
''')
    (fake/'no-mistakes').chmod(0o755)
    env['PATH']=str(fake)+os.pathsep+env['PATH']
    write(LAB/'data/backlog.md','''## In flight
- [ ] predecessor - Retained failure (repo: sample) (kind: ship) (hold: source retention) (hold-kind: external)
- [ ] delivered - Review approval (repo: sample) (kind: ship) (hold: approve delivery) (hold-kind: captain)
- [ ] continuation - Current work (repo: sample) (kind: ship)
- [ ] review - Completed scout (repo: sample) (kind: scout) (hold: retain report) (hold-kind: external)

## Queued

## Done
''')
    for name,state in [('predecessor','failed'),('delivered','completed'),('continuation','running'),('review',None)]:
        wt=LAB/'projects'/name
        run(['git','init','-q','-b','fm/'+name,wt])
        run(['git','commit','-q','--allow-empty','-m','fixture'],cwd=wt)
        write(LAB/'state'/f'{name}.meta',f'backend=tmux\nwindow={target}\nworktree={wt}\nproject={wt}\nharness=claude\nkind={"scout" if name=="review" else "ship"}\nmode={"scout" if name=="review" else "no-mistakes"}\n')
        write(LAB/'state'/f'{name}.status','done: report ready\n' if name=='review' else 'paused: historical wait\n')
        record(name)
        if state: native(name,state)
    write(LAB/'data/review/report.md','# Completed disposable review\n')
    write(LAB/'state/predecessor.status','needs-decision [key=next-action]: choose the next action\n')
    d,_=snapshot('01-retained-versus-current')
    assert d['valid'] and {x['id'] for x in d['retained_attempts']}=={'predecessor','delivered','review'}
    assert [x['id'] for x in d['active_children']]==['continuation']
    assert any(x.get('key')=='next-action' for x in d['decisions_open'])
    assert any(x['id']=='delivered' for x in d['decisions_open'])
    assert d['counts']['landed']==0
    results.append({'scenario':'Retained terminal attempts do not replace current work or close approval','result':'pass','artifact':'01-retained-versus-current.json'})
    d,_=snapshot('01b-retained-projection-limit',FM_SNAPSHOT_SECONDMATE_CHILDREN='1')
    assert d['valid'] and d['counts']['retained_attempts']==3 and len(d['retained_attempts'])==1
    assert any(x['surface']=='retained_attempts' and x['count']==2 for x in d['omitted'])
    results.append({'scenario':'Projection limits disclose omitted retained attempts without changing logical completion','result':'pass','artifact':'01b-retained-projection-limit.json'})
    backlog=(LAB/'data/backlog.md').read_text()
    write(LAB/'data/backlog.md',backlog.replace(' (hold: source retention) (hold-kind: external)',''))
    d,_=snapshot('01c-terminal-without-hold')
    assert not d['valid'] and d['invalidity']=={'kind':'terminal_in_flight','ids':['predecessor']}
    assert all(x['id']!='predecessor' for x in d['retained_attempts'])
    write(LAB/'data/backlog.md',backlog)
    (LAB/'state/review.busy-state').unlink()
    d,_=snapshot('01d-report-without-lifecycle-evidence')
    assert not d['valid'] and 'review' in d['invalidity']['ids']
    assert all(x['id']!='review' for x in d['retained_attempts'])
    record('review')
    results.append({'scenario':'A terminal event without a hold or a scout report without lifecycle proof is not retained coverage','result':'pass','artifact':'01c-terminal-without-hold.json; 01d-report-without-lifecycle-evidence.json'})
    record('predecessor','busy')
    d,_=snapshot('02-terminal-worker-continuing')
    assert d['valid']
    assert any(x['id']=='predecessor' and x['runtime_activity']['state']=='busy' for x in d['retained_attempts'])
    assert any(x['id']=='predecessor' and x['source']=='claude-hook' for x in d['active_children'])
    assert any(x.get('key')=='next-action' for x in d['decisions_open'])
    results.append({'scenario':'A worker can continue after terminal validation without losing its open decision','result':'pass','artifact':'02-terminal-worker-continuing.json'})
    (LAB/'state/predecessor.busy-state').unlink()
    d,_=snapshot('03-unknown-activity')
    assert not d['valid'] and d['state']=='unknown'
    assert d['invalidity']=={'kind':'child_current_unavailable','ids':['predecessor']}
    assert any(x['id']=='predecessor' and x['runtime_activity']['state']=='unknown' for x in d['retained_attempts'])
    assert any(x.get('key')=='next-action' for x in d['decisions_open'])
    results.append({'scenario':'Unavailable activity is unknown, not idle, and preserves held evidence','result':'pass','artifact':'03-unknown-activity.json'})
    record('predecessor')
    native('predecessor','running')
    d,_=snapshot('04-live-native-continuation')
    assert d['valid'] and all(x['id']!='predecessor' for x in d['retained_attempts'])
    assert any(x['id']=='predecessor' for x in d['active_children'])
    native('predecessor','running',duplicate=True)
    d,_=snapshot('05-competing-native-ownership')
    assert not d['valid'] and d['state']=='unknown' and 'predecessor' in d['invalidity']['ids']
    assert all(x['id']!='predecessor' for x in d['retained_attempts'])
    assert any(x.get('key')=='next-action' for x in d['decisions_open'])
    results.append({'scenario':'Current native work wins, but competing ownership remains unknown','result':'pass','artifact':'04-live-native-continuation.json; 05-competing-native-ownership.json'})
    native('predecessor','failed')
    write(LAB/'projects/predecessor/stall','')
    d,elapsed=snapshot('06-bounded-stalled-native-read',FM_SNAPSHOT_CREW_STATE_TIMEOUT='3')
    assert elapsed<15 and not d['valid'] and d['state']=='unknown'
    assert 'predecessor' in d['invalidity']['ids']
    assert any(x.get('key')=='next-action' for x in d['decisions_open'])
    pid=int((LAB/'projects/predecessor/query.pid').read_text())
    statepath=pathlib.Path(f'/proc/{pid}/stat')
    state=statepath.read_text().split(') ')[1].split()[0] if statepath.exists() else 'gone'
    assert state in ('Z','gone'), f'query {pid} still running: {state}'
    artifact('06-native-read-bound-observation.json',{'runs':1,'elapsed_seconds':elapsed,'spread':'single run, not a benchmark','configured_snapshot_read_bound_seconds':3,'native_query_default_bound_seconds':10,'query_pid':pid,'query_state_after_snapshot':state,'limiter':'outer snapshot per-child timeout; external query starts and ignores TERM; full snapshot returns unknown','scope':'two runner levels, not the accepted unsupported three-level Perl cancellation chain'})
    perl_path=LAB/'perl-path'
    perl_path.mkdir()
    for tool in 'bash sh env python3 perl jq dirname mktemp cat rm mv mkdir date find sort head tail grep sed awk tr stat git uname ps basename wc chmod sleep xargs realpath readlink cmp cut touch flock rmdir cp id'.split():
        path=shutil.which(tool,path=env['PATH'])
        if path: (perl_path/tool).symlink_to(path)
    (perl_path/'no-mistakes').symlink_to(fake/'no-mistakes')
    mechanism=run(['bash','-c','. "$1"; fm_timeout_mechanism','_',ROOT/'bin/fm-timeout-lib.sh'],e=env|{'PATH':str(perl_path)}).stdout.strip()
    assert mechanism=='perl'
    (LAB/'projects/predecessor/query.pid').unlink()
    d,perl_elapsed=snapshot('06b-bounded-perl-native-read',FM_SNAPSHOT_CREW_STATE_TIMEOUT='3',PATH=str(perl_path))
    assert perl_elapsed<15 and not d['valid'] and 'predecessor' in d['invalidity']['ids']
    assert any(x.get('key')=='next-action' for x in d['decisions_open'])
    pid=int((LAB/'projects/predecessor/query.pid').read_text())
    statepath=pathlib.Path(f'/proc/{pid}/stat')
    state=statepath.read_text().split(') ')[1].split()[0] if statepath.exists() else 'gone'
    assert state in ('Z','gone'), f'Perl query {pid} still running: {state}'
    artifact('06b-perl-read-bound-observation.json',{'runs':1,'elapsed_seconds':perl_elapsed,'spread':'single run, not a benchmark','mechanism':mechanism,'configured_snapshot_read_bound_seconds':3,'native_query_default_bound_seconds':10,'query_pid':pid,'query_state_after_snapshot':state,'limiter':'snapshot per-child Perl alarm; real external query starts and ignores TERM','scope':'two runners only; no claim about accepted three-level Perl cancellation limitation'})
    (LAB/'projects/predecessor/stall').unlink()
    results.append({'scenario':'A stalled native query returns unknown within the snapshot read bound and is stopped','result':'pass','artifact':'06-bounded-stalled-native-read.json; 06-native-read-bound-observation.json; 06b-bounded-perl-native-read.json; 06b-perl-read-bound-observation.json'})
    record('predecessor','busy')
    # A genuinely unresponsive private server, not a mocked tmux response.
    os.kill(int(server), signal.SIGSTOP)
    try:
        d,elapsed=snapshot('07-bounded-stalled-endpoint',FM_SNAPSHOT_CREW_STATE_TIMEOUT='3')
    finally:
        os.kill(int(server), signal.SIGCONT)
    assert elapsed<18 and not d['valid'] and d['state']=='unknown'
    assert any(x['id']=='predecessor' and x['runtime_activity']['state']=='unknown' and x['runtime_activity']['source']=='endpoint-unverified' for x in d['retained_attempts'])
    assert all(x['id']!='predecessor' for x in d['active_children'])
    assert any(x.get('key')=='next-action' for x in d['decisions_open'])
    assert any(x['id']=='predecessor' and x['endpoint']['exists'] is None for x in d['endpoints'])
    artifact('07-endpoint-bound-observation.json',{'runs':1,'elapsed_seconds':elapsed,'spread':'single run, not a benchmark','per_read_bound_seconds':3,'limiter':'real private tmux server SIGSTOP blocks endpoint-presence and recovery-grade probes; independent reads expire sequentially','server_resumed':True})
    results.append({'scenario':'An unresponsive real endpoint is bounded and remains unknown, not dead or idle','result':'pass','artifact':'07-bounded-stalled-endpoint.json; 07-endpoint-bound-observation.json'})
    # Kill only this private server: the captured busy record must not look live.
    tmux('kill-server')
    started=False
    d,_=snapshot('08-busy-record-with-dead-endpoint')
    # All fixture tasks share this actual endpoint, so the scout loses its
    # current classifier too; its uncertainty must not erase native evidence.
    assert not d['valid'] and d['state']=='unknown'
    assert d['invalidity']=={'kind':'child_current_unavailable','ids':['review']}
    assert all(x['id']!='predecessor' for x in d['active_children'])
    assert any(x['id']=='predecessor' and x['runtime_activity']['state']=='dead' and x['runtime_activity']['source']=='endpoint-gone' for x in d['retained_attempts'])
    assert any(x.get('key')=='next-action' for x in d['decisions_open'])
    results.append({'scenario':'A stale busy record cannot survive positive endpoint death as active work','result':'pass','artifact':'08-busy-record-with-dead-endpoint.json'})
    with (LAB/'state/predecessor.status').open('a') as f:
        f.write('resolved [key=next-action]: next action recorded\n')
    d,_=snapshot('09-explicit-keyed-resolution')
    assert all(x.get('key')!='next-action' for x in d['decisions_open'])
    assert any(x['id']=='predecessor' and x['state']=='failed' for x in d['retained_attempts'])
    results.append({'scenario':'Explicit keyed resolution closes the decision without erasing the retained attempt','result':'pass','artifact':'09-explicit-keyed-resolution.json'})
except Exception:
    artifact('live-driver-failure.txt',traceback.format_exc())
    results.append({'scenario':'Live driver','result':'fail','error':traceback.format_exc()})
    raise
finally:
    if started:
        tmux('kill-server',check=False)
    # Reap only exact external-fixture queries if a check interrupted cleanup.
    for p in (LAB/'projects').glob('*/query.pid'):
        try:
            pid=int(p.read_text())
            args=pathlib.Path(f'/proc/{pid}/cmdline').read_bytes()
            if str(LAB).encode() in args: os.kill(pid,9)
        except (FileNotFoundError,ProcessLookupError): pass
    shutil.rmtree(LAB)
    artifact('live-scenario-results.json',{'results':results,'lab_removed':not LAB.exists(),'isolation':'real Firstmate scripts, real private tmux and Claude process; synthetic no-mistakes read-only response service; no production fleet or pipeline controls'})
