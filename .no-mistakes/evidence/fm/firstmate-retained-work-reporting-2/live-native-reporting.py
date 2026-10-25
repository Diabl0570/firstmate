#!/usr/bin/env python3
"""Read synthetic historical native records through the real no-mistakes CLI.
No pipeline is initialized, run, resumed, aborted, or controlled. SQLite input
records are fixture data in a disposable NM_HOME, not claims of real executions.
The actual Claude endpoint stays at its trust screen, which is not answered.
"""
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import tempfile
import time

ROOT = Path.cwd()
OUT = Path('/home/kasper/.no-mistakes/evidence/01M5RW6VSY3JV2SWKMXPM1X127')
ENV = os.environ.copy()
for key in ('FM_ROOT_OVERRIDE','FM_STATE_OVERRIDE','FM_DATA_OVERRIDE','FM_CONFIG_OVERRIDE',
            'FM_PROJECTS_OVERRIDE','FM_HOME','NM_HOME','TMUX','FM_GATE_REFUSE_BYPASS',
            'FM_TEST_SEAM','TASKS_AXI_FILE','TASKS_AXI_BACKEND'):
    ENV.pop(key, None)
ENV.update(TMPDIR=str(ROOT/'.test-phase-tmp'), GIT_CONFIG_GLOBAL='/dev/null', GIT_CONFIG_NOSYSTEM='1')

def run(args, env=None, cwd=ROOT, check=True, timeout=45):
    p = subprocess.run([str(x) for x in args], env=env or ENV, cwd=cwd,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
    if check and p.returncode:
        raise AssertionError((args, p.returncode, p.stdout.decode(), p.stderr.decode()))
    return p

def save(name, obj):
    (OUT/name).write_text(json.dumps(obj, indent=2)+'\n')

lab = ROOT/'.l'
scratch = Path(tempfile.mkdtemp(prefix='live-native-', dir=ROOT/'.test-phase-tmp'))
run(['bin/fm-lab-home.sh','create',lab])
(lab/'tmux').mkdir()
ten = dict(ENV, TMUX_TMPDIR=str(lab/'tmux'))
tmux = ['tmux','-L','fm-lab']
try:
    # Keep the exact runbook CLI launch and non-zero terminal dimensions.
    cli_env = ten.copy()
    cli_env.pop('NO_MISTAKES_GATE',None)
    run(tmux+['new-session','-d','-s','primary','-n','primary','-x','120','-y','40',
              '-c',ROOT,'-e',f'FM_HOME={lab}','claude'],cli_env)
    time.sleep(3)
    (OUT/'live-native-claude-endpoint.txt').write_bytes(run(tmux+['capture-pane','-p','-t','primary'],ten).stdout)
    socket = run(tmux+['display-message','-p','-t','primary','#{socket_path}'],ten).stdout.decode().strip()
    env = dict(ENV, FM_HOME=str(lab), NM_HOME=str(scratch/'nm'),
               TMUX=f'{socket},0,0', FM_CREW_STATE_NO_FORGE='1',
               FM_ROOT_OVERRIDE=str(ROOT/'.test-phase-tmp/code-root'))
    # A read-only inventory command materializes the normal DB schema. It exits
    # uninitialized; we do not call `init` or create any running pipeline.
    run(['no-mistakes','runs','--limit','1'],env,check=False)
    db = sqlite3.connect(scratch/'nm/state.sqlite')
    now = int(time.time())
    for ident, status, target in [('predecessor','failed','primary:primary'),
                                   ('delivered','completed',''),
                                   ('continuation','running','')]:
        wt = lab/'projects'/ident
        run(['git','init','-q','-b','main',wt])
        (wt/'evidence.txt').write_text('protected baseline\n')
        run(['git','-C',wt,'add','evidence.txt'])
        run(['git','-C',wt,'-c','user.name=Fixture','-c','user.email=fixture@example.invalid',
             'commit','-q','-m','fixture baseline'])
        head = run(['git','-C',wt,'rev-parse','HEAD']).stdout.decode().strip()
        run(['git','-C',wt,'update-ref','refs/remotes/origin/main',head])
        run(['git','-C',wt,'checkout','-q','-b',f'fm/{ident}'])
        db.execute('INSERT INTO repos (id,working_path,upstream_url,created_at) VALUES (?,?,?,?)',
                   (ident,str(wt),'https://example.invalid/fixture.git',now))
        db.execute('INSERT INTO runs (id,repo_id,branch,head_sha,base_sha,status,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?)',
                   ('fixture-'+ident,ident,'fm/'+ident,head,head,status,now,now))
        (lab/'state'/f'{ident}.meta').write_text(
            f'window={target}\nbackend=tmux\nworktree={wt}\nproject={wt}\n'
            f'spawn_gen=fixture-{ident}\nendpoint_task_id={ident}\n'
            'harness=claude\nkind=ship\nmode=no-mistakes\n')
        (lab/'state'/f'{ident}.status').write_text('paused: historical attempt wording\n')
        gen = run(['bin/fm-busy-event.sh','arm',lab/'state',ident],env).stdout.decode().strip()
        run(['bin/fm-busy-event.sh','apply',lab/'state',ident,'idle','--gen',gen,
             '--source','claude-hook','--event','stop'],env)
    db.commit()
    (lab/'data/backlog.md').write_text('''## In flight
- [ ] predecessor - Retained failed attempt (repo: sample) (kind: ship) (hold: source retention) (hold-kind: external)
- [ ] delivered - Delivered attempt awaiting approval (repo: sample) (kind: ship) (hold: review delivery) (hold-kind: captain)
- [ ] continuation - Current continuation (repo: sample) (kind: ship)

## Queued

## Done
''')
    def snapshot(name):
        p = run(['bin/fm-fleet-snapshot.sh','--secondmate-home-summary'],env)
        data=json.loads(p.stdout)
        save(name+'.json',data)
        return data
    s=snapshot('live-native-retention')
    assert s['valid'] and s['state']=='captain_decision',s
    assert [a['id'] for a in s['retained_attempts']]==['delivered','predecessor'],s
    assert [a['id'] for a in s['active_children']]==['continuation'],s
    assert s['counts']['landed']==0 and any(d['id']=='delivered' for d in s['decisions_open']),s
    print('REAL NATIVE CLI / SEEDED HISTORY: retained failed+completed attempts; active continuation; approval preserved',flush=True)
    # Drive the actual snapshot and native inventory parser under both fallback
    # selections. gtimeout delegates to the normal installed GNU timeout binary,
    # not a multicall symlink whose argv[0] would select the wrong applet.
    for mode in ('perl','gtimeout'):
        tools=scratch/('tools-'+mode)
        tools.mkdir()
        for name in ('bash','perl','sleep','dirname','mktemp','cat','rm','git','ps',
                     'awk','sed','grep','head','tail','tr','stat','id','date','uname',
                     'env','wc','mkdir','ln','chmod','jq','python3','tmux','sort',
                     'cut','basename','cp','mv','readlink','expr','find','touch'):
            executable=shutil.which(name)
            if executable:
                (tools/name).symlink_to(executable)
        (tools/'no-mistakes').symlink_to(shutil.which('no-mistakes'))
        if mode=='gtimeout':
            runner=shutil.which('timeout') or shutil.which('gtimeout')
            assert runner,'external runner unavailable'
            (tools/'gtimeout').write_text('#!/usr/bin/env bash\nprintf "gtimeout\\n" >> "'+str(scratch/'gtimeout-used')+'"\nexec "'+runner+'" "$@"\n')
            (tools/'gtimeout').chmod(0o755)
        selected_env=dict(env,PATH=str(tools))
        mechanism=run([shutil.which('bash'),'-c','. "$1/bin/fm-timeout-lib.sh"; fm_timeout_mechanism','_',ROOT],selected_env).stdout.decode().strip()
        assert mechanism==mode,mechanism
        data=json.loads(run(['bin/fm-fleet-snapshot.sh','--secondmate-home-summary'],selected_env).stdout)
        save('live-native-'+mode+'-consumer.json',data)
        assert data['valid'] and [a['id'] for a in data['retained_attempts']]==['delivered','predecessor'],data
        assert [a['id'] for a in data['active_children']]==['continuation'],data
        if mode=='gtimeout':
            assert (scratch/'gtimeout-used').read_text().strip()
        print('REAL SNAPSHOT + NATIVE STDIN-CONSUMING INVENTORY: selected '+mechanism+'; retained and current records unchanged',flush=True)
    native=run(['no-mistakes','axi','status','--run','fixture-predecessor'],env,cwd=lab/'projects/predecessor')
    (OUT/'live-native-status.txt').write_bytes(native.stdout)

    gen=run(['bin/fm-busy-event.sh','arm',lab/'state','predecessor'],env).stdout.decode().strip()
    run(['bin/fm-busy-event.sh','apply',lab/'state','predecessor','busy','--gen',gen,
         '--source','claude-hook','--event','user-prompt-submit'],env)
    s=snapshot('live-native-busy-continuation')
    assert s['valid'] and any(a['id']=='predecessor' and a['source']=='claude-hook' for a in s['active_children']),s
    assert any(a['id']=='predecessor' and a['state']=='failed' and a['runtime_activity']['state']=='busy' for a in s['retained_attempts']),s
    print('REAL NATIVE CLI + REAL CLAUDE PROCESS: terminal attempt does not suppress a seeded busy lifecycle event',flush=True)

    (lab/'state/predecessor.status').write_text('needs-decision [key=next-action]: choose next action\n')
    # Suspend only this private lab's actual server, not a wrapper or fake CLI.
    # Native history remains readable while endpoint inventory stops answering.
    server_pid=int(run(tmux+['display-message','-p','-t','primary','#{pid}'],ten).stdout)
    import signal
    os.kill(server_pid,signal.SIGSTOP)
    try:
        stalled_env=dict(env,FM_SNAPSHOT_CREW_STATE_TIMEOUT='2')
        p=run(['bin/fm-fleet-snapshot.sh','--secondmate-home-summary'],stalled_env,timeout=15)
        stalled=json.loads(p.stdout)
        save('live-native-stalled-endpoint.json',stalled)
        assert not stalled['valid'] and stalled['invalidity']=={'kind':'child_current_unavailable','ids':['predecessor']},stalled
        assert any(a['id']=='predecessor' and a['state']=='failed' and a['runtime_activity']['state']=='unknown' for a in stalled['retained_attempts']),stalled
        assert any(d.get('key')=='next-action' for d in stalled['decisions_open']),stalled
        assert any(a['id']=='continuation' for a in stalled['active_children']),stalled
        print('REAL STOPPED PRIVATE TMUX SERVER: bounded probes return unknown; native attempt, continuation, hold, and open call survive',flush=True)
    finally:
        os.kill(server_pid,signal.SIGCONT)
    (lab/'state/predecessor.busy-state').unlink()
    s=snapshot('live-native-unknown-activity')
    assert not s['valid'] and s['invalidity']=={'kind':'child_current_unavailable','ids':['predecessor']},s
    assert any(d.get('key')=='next-action' for d in s['decisions_open']),s
    assert any(a['id']=='predecessor' for a in s['retained_attempts']),s
    assert any(a['id']=='continuation' for a in s['active_children']),s
    print('REAL NATIVE CLI: unknown worker activity preserves terminal evidence, current continuation, and the open call',flush=True)

    # A new native executing record outranks historical failed evidence. It is
    # static test data only: no process is asked to execute the synthetic run.
    db.execute('UPDATE runs SET status=?,updated_at=? WHERE id=?',('running',now+1,'fixture-predecessor'))
    db.commit()
    s=snapshot('live-native-new-executing-record')
    assert s['valid'] and any(a['id']=='predecessor' for a in s['active_children']),s
    assert not any(a['id']=='predecessor' for a in s['retained_attempts']),s
    print('REAL NATIVE CLI: newer executing input is active, not a retained terminal attempt',flush=True)

    db.execute('UPDATE runs SET status=? WHERE id=?',('failed','fixture-predecessor'))
    db.commit()
    gen=run(['bin/fm-busy-event.sh','arm',lab/'state','predecessor'],env).stdout.decode().strip()
    run(['bin/fm-busy-event.sh','apply',lab/'state','predecessor','busy','--gen',gen,
         '--source','claude-hook','--event','user-prompt-submit'],env)
    run(tmux+['new-window','-d','-t','primary:','-n','keeper','sleep','300'],ten)
    run(tmux+['kill-window','-t','primary:primary'],ten)
    s=snapshot('live-native-dead-endpoint')
    assert s['valid'] and any(a['id']=='predecessor' and a['runtime_activity']['state']=='dead' for a in s['retained_attempts']),s
    assert not any(a['id']=='predecessor' for a in s['active_children']),s
    assert any(d.get('key')=='next-action' for d in s['decisions_open']),s
    print('REAL CLOSED CLAUDE ENDPOINT: stale busy activity becomes dead; retained attempt and unresolved call remain',flush=True)

    # The workspace is dirty, so refusal precedes remote reads and lifecycle
    # changes. Verify the real endpoint and protected files survive refusal.
    db.execute('UPDATE runs SET status=? WHERE id=?',('failed','fixture-predecessor'))
    db.commit()
    wt=lab/'projects/predecessor'
    (wt/'evidence.txt').write_text('protected baseline\nuncommitted protected work\n')
    before=run(['git','-C',wt,'rev-parse','HEAD']).stdout
    lifecycle_env=dict(env)
    lifecycle_env.pop('FM_ROOT_OVERRIDE',None)
    p=run(['bin/fm-teardown.sh','predecessor'],lifecycle_env,check=False)
    (OUT/'live-cleanup-refusal.txt').write_bytes(p.stdout+p.stderr)
    assert p.returncode != 0 and b'REFUSED' in p.stdout+p.stderr,(p.stdout,p.stderr)
    assert before==run(['git','-C',wt,'rev-parse','HEAD']).stdout
    assert 'uncommitted protected work' in (wt/'evidence.txt').read_text()
    assert (lab/'state/predecessor.meta').exists()
    run(tmux+['has-session','-t','primary'],ten)
    print('REAL TEARDOWN: dirty unlanded work is refused; head, evidence, metadata, and private session preserved',flush=True)
    db.close()
finally:
    run(tmux+['kill-server'],ten,check=False)
    shutil.rmtree(lab)
    shutil.rmtree(scratch)
