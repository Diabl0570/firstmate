"""Drive the real firstmate poller and real gh through an isolated TLS forge endpoint.
Only the dependency endpoint is a fixture; no product command is replaced.
"""
import collections, copy, http.server, json, os, pathlib, shutil, ssl, subprocess, threading, time, traceback
ROOT=pathlib.Path.cwd(); LAB=ROOT/'.test-contributions-lab'
EVID=pathlib.Path('/home/kasper/.no-mistakes/evidence/01M4CAREGRG77NQ13T77SQ85F7')
HEAD='a'*40; URL='https://github.com/o/r/pull/8'; NOW='2026-09-16T08:00:00Z'
ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);ctx.load_cert_chain(LAB/'cert.pem',LAB/'key.pem')
mode={}; calls=[]; lock=threading.Lock(); results=[]; transcript=[]
class Handler(http.server.BaseHTTPRequestHandler):
 def log_message(self,*args): pass
 def do_CONNECT(self):
  if self.path not in ('api.github.com:443','github.com:443'):
   self.send_error(403);return
  self.send_response(200);self.end_headers()
  self.connection=ctx.wrap_socket(self.connection,server_side=True)
  self.rfile=self.connection.makefile('rb');self.wfile=self.connection.makefile('wb');self.close_connection=False
 def do_GET(self): self.handle_forge()
 def do_POST(self): self.handle_forge()
 def handle_forge(self):
  body=self.rfile.read(int(self.headers.get('Content-Length','0')))
  path=self.path.split('?')[0]
  if path=='/graphql': stage='closing'
  elif path.endswith('/check-runs'):stage='checks'
  elif path.endswith('/statuses'):stage='statuses'
  elif path.endswith('/reviews'):stage='reviews'
  elif path.endswith('/events'):stage='issue-events'
  elif '/pulls/' in path and path.endswith('/comments'):stage='inline'
  elif path.endswith('/comments'):stage='comments'
  elif path=='/repos/o/r':stage='repo'
  else:stage='core'
  entry={'method':self.command,'path':self.path,'stage':stage}
  if body:entry['body']=json.loads(body)
  with lock:calls.append(entry)
  settings=dict(mode)
  if stage in settings.get('delay',{}):time.sleep(settings['delay'][stage])
  if stage in settings.get('fail',{}):
   status=settings['fail'][stage]
   message='PRIVATE_DIAGNOSTIC_SENTINEL https://private.invalid/repo Authorization: private-header private-response-body'
   if settings.get('oversized'):message='x'*5000+message
   self.respond(status,{'message':message});return
  if stage=='closing':
   if settings.get('graphql_error'):
    self.respond(200,{'errors':[{'message':'PRIVATE_DIAGNOSTIC_SENTINEL forbidden','type':'FORBIDDEN'}],'data':{'repository':{'pullRequest':None}}});return
   self.respond(200,{'data':{'repository':{'pullRequest':{'headRefOid':('b'*40 if settings.get('drift') else HEAD),'reviewDecision':'APPROVED','id':'PR_fixture','number':8}}}});return
  if stage=='core':
   if path.endswith('/9') and settings.get('schema'):data={'state':'open','user':None}
   elif '/issues/' in path:data={'state':'open','user':{'login':'author'},'labels':[]}
   else:data={'state':'open','user':{'login':'author'},'head':{'sha':HEAD},'draft':False,'mergeable':True,'merged_at':None}
  elif stage=='checks':data={'check_runs':[{'name':'test','id':1,'status':'completed','conclusion':'success','started_at':NOW}]}
  elif stage=='repo':data={'permissions':{'push':False}}
  else:data=[]
  self.respond(200,data)
 def respond(self,status,data):
  encoded=json.dumps(data).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(encoded)));self.end_headers()
  try:self.wfile.write(encoded)
  except (BrokenPipeError,ConnectionResetError):pass
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler);threading.Thread(target=server.serve_forever,daemon=True).start()
base_env={k:v for k,v in os.environ.items() if not k.startswith(('GH_','GITHUB_','FM_','TASKS_AXI_')) and k not in ('NO_PROXY','no_proxy','HTTPS_PROXY','https_proxy','HTTP_PROXY','http_proxy','ALL_PROXY','all_proxy')}
base_env.update(GH_TOKEN='disposable-fixture-token',SSL_CERT_FILE=str(LAB/'cert.pem'),HTTPS_PROXY=f'http://127.0.0.1:{server.server_port}',HTTP_PROXY=f'http://127.0.0.1:{server.server_port}',NO_PROXY='',GH_PROMPT_DISABLED='1',GH_NO_UPDATE_NOTIFIER='1',TMPDIR=str(LAB/'tmp'),FM_CONTRIBUTIONS_NOW=NOW)
def fresh(name,owners=('delivery',),url=URL):
 home=LAB/name
 if home.exists():shutil.rmtree(home)
 for d in ('data','state','config','projects','home','gh-config'): (home/d).mkdir(parents=True,exist_ok=True)
 (home/'data/backlog.md').write_text('# Backlog\n\n## Queued\n'+''.join(f'- [ ] {task} - Contribution {url} (repo: sample) (kind: ship)\n' for task in owners))
 for task in owners:
  (home/'data'/task).mkdir()
  record={'schema':'fm-contributions.v1','task':task,'records':[{'url':url,'kind':('issue' if '/issues/' in url else 'pr'),'checked_at':'2026-09-15T08:00:00Z','error':None,'observation':{'head':HEAD,'state':'open','draft':False,'mergeable':'mergeable','review_decision':'APPROVED','can_merge':False,'checks':[{'name':'test','id':1,'status':'completed','conclusion':'success','started_at':NOW}],'reviews':[],'events':[]},'verdict':{'head':HEAD,'actor':'maintainer','source':URL+'#issuecomment-99','summary':'awaiting maintainer'},'pending':[{'token':'preserved','type':'comment','source':URL+'#issuecomment-99','head':None,'body':'existing signal'}],'seen':['preserved'],'notified':['preserved']}]}
  if '/issues/' in url:record['records'][0]['observation']['ready']=False
  (home/'data'/task/'contributions.json').write_text(json.dumps(record,indent=2)+'\n')
 return home

def saved(home,task='delivery'):return json.loads((home/'data'/task/'contributions.json').read_text())['records'][0]
def poll(home,settings,extra=None,script='bin/fm-contributions.sh'):
 global mode
 mode=settings;calls.clear()
 env=base_env.copy();env.update(HOME=str(home/'home'),GH_CONFIG_DIR=str(home/'gh-config'),FM_HOME=str(home),FM_ROOT_OVERRIDE=str(ROOT),FM_STATE_OVERRIDE=str(home/'state'),FM_DATA_OVERRIDE=str(home/'data'),FM_CONFIG_OVERRIDE=str(home/'config'),FM_PROJECTS_OVERRIDE=str(home/'projects'))
 if extra:env.update(extra)
 before_bytes={f.parent.name:f.read_bytes() for f in (home/'data').glob('*/contributions.json')}
 start=time.monotonic();p=subprocess.run([str(ROOT/script),'poll'],env=env,text=True,capture_output=True,timeout=35);elapsed=time.monotonic()-start
 requests=copy.deepcopy(calls)
 trace={'home':home.name,'script':script,'settings':settings,'extra_env':extra or {},'exit':p.returncode,'elapsed_seconds':round(elapsed,3),'stdout':p.stdout,'stderr':p.stderr,'requests':requests,'records_before':{task:json.loads(raw) for task,raw in before_bytes.items()},'record_bytes_unchanged':{task:(home/'data'/task/'contributions.json').read_bytes()==raw for task,raw in before_bytes.items()},'records':{f.parent.name:json.loads(f.read_text()) for f in (home/'data').glob('*/contributions.json')},'wake_queue':(home/'state/.wake-queue').read_text() if (home/'state/.wake-queue').exists() else ''}
 transcript.append(trace)
 assert p.returncode==0,trace
 assert not p.stderr,trace
 assert not trace['wake_queue'],trace
 assert 'PRIVATE_DIAGNOSTIC_SENTINEL' not in p.stdout+json.dumps(trace['records'])+p.stderr,trace
 counts=collections.Counter((r['method'],r['path']) for r in requests)
 assert all(n==1 for n in counts.values()),('retry',counts)
 for r in requests:
  assert r['method']=='GET' or (r['path']=='/graphql' and 'mutation' not in r['body']['query']),r
 return p.stdout.strip(),requests,elapsed

def diagnostic(stage,status):return f'forge read failed at {stage} (HTTP {status}; exit 1)'
def assert_error(home,out,error,url=URL,prior=None):
 assert out==f'contributions: observation unavailable for {url}: {error}',out
 row=saved(home);assert row['error']==error,row
 if prior:
  for k in ('observation','verdict','pending','seen','notified'):assert row[k]==prior[k],(k,row,prior)

def scenario(name,fn):
 index=len(transcript)
 try:fn();results.append({'name':name,'result':'pass','live':True,'evidence':f'live-transcript.json entries {index+1}–{len(transcript)}','reason':''});print('PASS',name,flush=True)
 except Exception as exc:
  results.append({'name':name,'result':'fail','live':True,'evidence':f'live-transcript.json from entry {index+1}','reason':str(exc)});traceback.print_exc()

def stages():
 for stage,status in [('core',404),('comments',403),('reviews',502),('inline',500),('checks',500),('statuses',500),('repo',403),('closing',503)]:
  home=fresh('stage-'+stage);prior=saved(home);out,req,_=poll(home,{'fail':{stage:status}});assert_error(home,out,diagnostic(stage,status),prior=prior)
  assert len(req)==(1 if stage=='core' else 8 if stage=='closing' else 7),req
 for stage in ('comments','issue-events'):
  url='https://github.com/o/r/issues/8';home=fresh('issue-'+stage,url=url);prior=saved(home);out,req,_=poll(home,{'fail':{stage:500}});assert_error(home,out,diagnostic(stage,500),url,prior);assert len(req)==3,req

def parallel():
 home=fresh('parallel');prior=saved(home);out,req,_=poll(home,{'fail':{'checks':500,'statuses':502},'delay':{'checks':0.3}})
 assert_error(home,out,diagnostic('checks',500)+'; '+diagnostic('statuses',502),prior=prior);assert len(req)==7,req
 home=fresh('all-parallel');prior=saved(home);stages=['checks','comments','inline','repo','reviews','statuses'];out,req,_=poll(home,{'fail':dict.fromkeys(stages,500)});assert_error(home,out,'; '.join(diagnostic(s,500) for s in stages),prior=prior);assert len(req)==7,req

def unavailable():
 home=fresh('graphql-no-http');prior=saved(home);out,_,_=poll(home,{'graphql_error':True});assert_error(home,out,'forge read failed at closing (exit 1; HTTP status unavailable)',prior=prior)
 home=fresh('oversized');prior=saved(home);out,_,_=poll(home,{'fail':{'reviews':500},'oversized':True});assert_error(home,out,'forge read failed at reviews (exit 1; HTTP status unavailable)',prior=prior)

def episodes():
 home=fresh('episodes',owners=('delivery','duplicate'));prior=saved(home)
 out,req,_=poll(home,{'fail':{'checks':500}});assert_error(home,out,diagnostic('checks',500),prior=prior);assert saved(home,'duplicate')['error']==saved(home)['error'];assert len(req)==7
 out,req,_=poll(home,{'fail':{'checks':500}});assert out=='';assert len(req)==7
 out,req,_=poll(home,{});assert out=='';assert len(req)==8
 for task in ('delivery','duplicate'):
  r=saved(home,task);assert r['error'] is None;assert r['observation']['head']==HEAD
  for k in ('pending','verdict','notified'):assert r[k]==prior[k],r
 out,req,_=poll(home,{'fail':{'checks':500}});assert_error(home,out,diagnostic('checks',500));assert len(req)==7

def drift():
 home=fresh('drift');prior=saved(home);out,req,_=poll(home,{'drift':True});assert_error(home,out,'head changed during observation',prior=prior);assert len(req)==8

def bounds():
 for name,extra,target in [('five-second',{},5),('one-second',{'FM_CONTRIBUTIONS_BUDGET':'1'},1),('watcher-cap',{'FM_CONTRIBUTIONS_BUDGET':'25','FM_CHECK_TIMEOUT':'4'},1)]:
  home=fresh('bound-'+name);path=home/'data/delivery/contributions.json';prior=path.read_bytes();out,req,elapsed=poll(home,{'delay':{'core':7}},extra)
  assert out=='';assert path.read_bytes()==prior;assert len(req)==1,req;assert target<=elapsed<target+4,elapsed

def schema():
 home=fresh('schema',owners=('delivery','second'))
 path=home/'data/second/contributions.json';data=json.loads(path.read_text());data['records'][0]['url']='https://github.com/o/r/pull/9';path.write_text(json.dumps(data)+'\n');prior=saved(home,'second')
 backlog=home/'data/backlog.md';backlog.write_text(backlog.read_text().replace('- [ ] second - Contribution '+URL,'- [ ] second - Contribution https://github.com/o/r/pull/9'))
 out,req,_=poll(home,{'fail':{'reviews':500},'schema':True},{'FM_CONTRIBUTIONS_BUDGET':'25'})
 assert out.splitlines()==[f'contributions: observation unavailable for {URL}: '+diagnostic('reviews',500),'contributions: observation unavailable for https://github.com/o/r/pull/9: forge observation unavailable or changed during read'],out
 r=saved(home,'second');assert r['error']=='forge observation unavailable or changed during read'
 for k in ('observation','verdict','pending'):assert r[k]==prior[k]
 assert len(req)==8,req

def baseline():
 home=fresh('baseline');prior=saved(home);out,req,_=poll(home,{'fail':{'checks':500,'statuses':502}},script='bin/.test-contributions-baseline.sh')
 assert out==f'contributions: observation unavailable for {URL}',out
 assert saved(home)['error']=='forge observation unavailable or changed during read';assert len(req)==7,req
 for k in ('observation','verdict','pending','seen','notified'):assert saved(home)[k]==prior[k]

try:
 scenario('HTTP failures report the correct PR and issue read stage, HTTP status and native exit without retries or forge writes',stages)
 scenario('Concurrent failed reads produce stable ordered sanitized diagnostics and preserve saved evidence',parallel)
 scenario('Missing and beyond-4096-byte HTTP status is not fabricated and private response text never escapes',unavailable)
 scenario('Shared owners wake once per failure episode; healthy recovery clears errors without consuming pending signals or verdicts',episodes)
 scenario('Head changes report a distinct fixed reason and reject mixed-head observations',drift)
 scenario('Five-second read cap, explicit smaller budget and watcher budget cap remain silent and byte-preserving',bounds)
 scenario('Malformed response on the next URL cannot inherit a preceding HTTP diagnostic',schema)
 scenario('Before-change replay confirms the formerly generic message with identical request count and preserved state',baseline)
finally:
 server.shutdown();server.server_close()
 (EVID/'live-transcript.json').write_text(json.dumps(transcript,indent=2)+'\n')
 (EVID/'live-scenarios.json').write_text(json.dumps(results,indent=2)+'\n')
 (EVID/'live-transcript.txt').write_text('\n\n'.join(f"{i+1}. {t['home']} ({t['script']})\nexit={t['exit']}, elapsed={t['elapsed_seconds']}s\nstdout: {t['stdout'].strip() or '(silent)'}\nstderr: {t['stderr'].strip() or '(silent)'}\nrequests: {', '.join(r['stage'] for r in t['requests'])}\nstored error: "+'; '.join(f"{task}: {d['records'][0]['error']}" for task,d in t['records'].items()) for i,t in enumerate(transcript))+'\n')
if any(s['result']=='fail' for s in results):raise SystemExit(1)
