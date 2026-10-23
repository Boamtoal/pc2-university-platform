#!/usr/bin/env python3
"""Local organizer control, with optional HTTPS access for explicitly approved LAN administrators."""
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from http.cookies import SimpleCookie,CookieError
from pathlib import Path
from urllib.parse import urlsplit,parse_qs
import argparse,base64,hashlib,hmac,json,mimetypes,os,re,secrets,signal,ssl,sys,threading,time
sys.path.insert(0,str(Path(__file__).resolve().parent))
from core import Store,Bridge,Error,require,password_hash,password_policy,password_ok,totp,stamp,digest,ROOT,prepare_judge_data
from totp_setup import provisioning as totp_provisioning
from contests import ContestManager,write_json
from problem_difficulty import annotate as annotate_difficulties
from native_admin import handle as native_route
from participant_activity import route as participant_route,activity_store,ActivityMonitor
from participant_test import route as participant_test_route
from participant_access import access as participant_access
from remote_access import RemoteAccess,route as remote_route
from dashboard_branding import route as branding_route
from participant_identity import route as participant_identity_route,publish as publish_identity
from team_connections import route as connections_route
from notifications import route as notifications_route
from submission_review import route as review_route,query as review_query
from scoreboards import route as scoreboards_route
from contest_exports import report_data,csv_report,pdf_report
from learning_reports import route as learning_route
from schedule_time import countries as schedule_countries,preview as schedule_preview,normalize as normalize_schedule
COOKIE='lcpc_admin'
MUTATIONS={'clock.start','clock.pause','clock.extend','contest.update','team.update','team.create','problem.update','clarification.answer','announcement','judgement','run.rejudge','judging.workflow','run.approve'}
OWNER_OPS={'judgement','run.rejudge','judging.workflow','run.approve'}

def validate_operation(op,args):
 schema={
  'judging.workflow':{'mode':str},'run.approve':{'number':int,'site':int,'reason':str,'expectedJudgement':str},
  'clock.start':{},'clock.pause':{},'clock.extend':{'seconds':int},
  'contest.update':{'title':str,'shortName':str,'freezeRemaining':str,'thawed':bool,'scheduledStart':str,'scheduledLocal':str,'scheduleCountry':str,'scheduleTimeZone':str,'scheduleOccurrence':int},
  'team.update':{'login':str,'name':str,'enabled':bool,'visible':bool,'password':str},
  'team.create':{'name':str,'password':str},
  'problem.update':{'id':str,'name':str,'timeLimit':int,'memoryLimit':int,'active':bool,'colorName':str,'colorRGB':str},
  'clarification.answer':{'number':int,'site':int,'answer':str,'all':bool},
  'announcement':{'message':str},'judgement':{'number':int,'site':int,'judgement':str,'reason':str},
  'run.rejudge':{'number':int,'site':int,'reason':str}}
 optional={'colorName','colorRGB','password','scheduledStart','scheduledLocal','scheduleCountry','scheduleTimeZone','scheduleOccurrence'}
 for key,kind in schema[op].items():
  if key not in args:require(key in optional,'Missing '+key);continue
  require(type(args[key]) is kind,'Invalid '+key)
  if kind is str:require(len(args[key])<=8000 and '\x00' not in args[key],'Invalid '+key)
 require(not(set(args)-set(schema[op])),'Unexpected operation arguments')
 if op=='contest.update':
  require(1<=len(args['title'].strip())<=200 and 1<=len(args['shortName'].strip())<=80,'Use a contest title of 1–200 characters and short name of 1–80 characters')
  require(re.fullmatch('[0-9]{2,3}:[0-5][0-9]:[0-5][0-9]',args['freezeRemaining']),'Use HH:MM:SS for freeze')
 if op in ('team.create','team.update','problem.update'):require(1<=len(args['name'].strip())<=200,'Use a name of 1–200 characters')
 if op=='judging.workflow':require(args['mode'] in ('automatic','review','human'),'Invalid judging workflow')
 if op=='problem.update':require(1<=args['timeLimit']<=10 and 32<=args['memoryLimit']<=1024,'Settings exceed the isolated judge policy')
 if op=='problem.update':validate_problem_color(args)
 if op=='clock.extend':require(60<=args['seconds']<=86400,'Add 1–1440 minutes')
 if 'password' in args and args['password']:password_policy(args['password'])

def validate_problem_color(args):
 if 'colorName' in args or 'colorRGB' in args:
  require(type(args.get('colorName')) is str and 1<=len(args['colorName'].strip())<=80 and '\x00' not in args['colorName'],'Use a balloon color name of 1–80 characters')
  require(type(args.get('colorRGB')) is str and re.fullmatch('#[0-9A-Fa-f]{6}',args['colorRGB']),'Use a balloon color in #RRGGBB format')

class App:
 def __init__(self,state,port=8091,bridge=None):
  self.store=Store(state);self.resources=self.store;self.bridge=bridge or Bridge(self.store.state);self.manager=ContestManager(self);self.port=port;self.origins={'http://127.0.0.1:'+str(port),'http://localhost:'+str(port)};self.remote=RemoteAccess(self)
 def status(self):
  state=self.resources.state;preferences=self.resources.schedule_preferences();participant=participant_access(self);server_access=participant if participant['active'] else participant_access(self,active_workspace=True)
  return {'pc2Connected':bool(self.bridge.process and self.bridge.process.poll() is None),'scope':'Local + approved remote administrators' if self.remote.config()['enabled'] else 'This computer only','transport':'Local HTTP / approved LAN HTTPS' if self.remote.config()['enabled'] else 'Loopback HTTP','uptimeSeconds':int(time.time()-self.store.boot),'state':state.name,'timezone':preferences['timeZone'],'schedulePreferences':preferences,'contestId':self.manager.data['selected'],'contestStatus':self.manager.selected()['status'],'activeContestId':self.manager.data['active'],'busy':self.manager.busy(),'participantAccess':participant,'serverAccess':server_access,'resourceBytes':sum(r['size'] for r in self.resources.resources()),'maxUploadMiB':20}
class Handler(BaseHTTPRequestHandler):
 protocol_version='HTTP/1.1';server_version='Organizer';sys_version=''
 def log_message(self,*args):pass
 @property
 def app(self):return self.server.app
 @property
 def remote(self):return bool(getattr(self.server,'remote',False))
 @property
 def cookie_name(self):return '__Host-lcpc_admin_remote' if self.remote else COOKIE
 def token(self):
  try:
   c=SimpleCookie();c.load(self.headers.get('Cookie',''));return c[self.cookie_name].value if self.cookie_name in c else ''
  except CookieError:return ''
 def cookie(self,token='',delete=False):return self.cookie_name+'='+token+'; Path=/; HttpOnly; SameSite=Strict'+('; Secure' if self.remote else '')+('; Max-Age=0' if delete else '')
 def send(self,status,body,kind='application/json',headers=None):
  if isinstance(body,(dict,list)):body=json.dumps(body,ensure_ascii=False).encode()
  if isinstance(body,str):body=body.encode()
  self.send_response(status);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(body)))
  for k,v in {'Cache-Control':'no-store, private','X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer','X-Frame-Options':'DENY','Cross-Origin-Resource-Policy':'same-origin','Permissions-Policy':'camera=(), microphone=(), geolocation=()','Content-Security-Policy':"default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' blob:; connect-src 'self'; font-src 'self'; base-uri 'none'; object-src 'none'; frame-ancestors 'none'; form-action 'self'",**(headers or {})}.items():self.send_header(k,v)
  self.end_headers()
  if self.command!='HEAD':self.wfile.write(body)
 def guard(self):
  if self.remote:
   require(isinstance(self.connection,ssl.SSLSocket),'HTTPS required',403);require(self.app.remote.permitted(self.client_address[0]),'This IP has not been approved for remote dashboard access.',403);origins={self.app.remote.origin};scheme='https://'
  else:require(self.client_address[0]=='127.0.0.1','Local access only',403);origins=self.app.origins;scheme='http://'
  host=self.headers.get('Host','');require(scheme+host in origins,'Unrecognized host',403)
  origin=self.headers.get('Origin')
  require(not origin or origin in origins,'Cross-origin request denied',403)
  public_shell=self.command in ('GET','HEAD') and urlsplit(self.path).path in ('/','/index.html','/app.js','/scoreboards.js','/scoreboard-model.js','/scoreboard-base.css','/contest-clock.js','/contest-clock.css','/scoreboards.css','/run-details.js','/schedule.js','/contests.js','/administrator.js','/workspace-nav.js','/guide.js','/guide-content.js','/guide.css','/participant-activity.js','/participant-test.js','/team-connections.js','/remote-access.js','/dashboard-branding.js','/participant-identity-editor.js','/learning-reports.js','/download-feedback.js','/download-feedback.css','/participant-theme.js','/notifications.js','/row-interactions.js','/review.html','/review.js','/review.css','/dashboard-theme.css','/api/dashboard-branding','/api/dashboard-branding/logo','/app.css','/assets/omu-logo.png','/assets/lcpc-logo.png','/assets/pc2-logo.png','/assets/icpc-logo.png')
  require(public_shell or self.headers.get('Sec-Fetch-Site','none') in ('none','same-origin'),'Cross-site request denied',403)
  if self.command not in ('GET','HEAD'):require(origin in origins,'A same-origin request is required',403)
  require(not self.headers.get('Transfer-Encoding'),'Chunked requests are not accepted',400)
 def body(self):
  require(self.headers.get('Content-Type','').split(';')[0].strip()=='application/json','Send JSON',415)
  try:length=int(self.headers.get('Content-Length','0'))
  except ValueError:raise Error(400,'Invalid content length')
  limit=8*1024*1024 if self.path=='/api/participant-identity' else 29*1024*1024 if self.path in ('/api/resources/upload','/api/problems/create','/api/native/execute','/api/native/import-preview','/api/native/configuration-preview') else 2*1024*1024 if self.path in ('/api/dashboard-branding','/api/learning-reports/material') else 64*1024
  require(0<length<=limit,'Request body too large',413)
  try:data=json.loads(self.rfile.read(length))
  except (ValueError,UnicodeError):raise Error(400,'Invalid JSON')
  require(isinstance(data,dict),'Expected a JSON object');return data
 def user(self,role='viewer'):
  user=self.app.store.session(self.token(),self.client_address[0],'remote' if self.remote else 'local');require(user,'Sign in required',401)
  if self.remote:require(self.app.remote.permitted(self.client_address[0],user['username']),'This account is not approved for this IP.',403)
  rank={'viewer':0,'operator':1,'owner':2};require(rank.get(user['role'],-1)>=rank[role],'Insufficient permission',403)
  if user['must_change']:require(self.path in ('/api/me','/api/password','/api/logout'),'Change the temporary password first',403)
  if self.command not in ('GET','HEAD'):require(hmac.compare_digest(self.headers.get('X-CSRF-Token',''),user['csrf']),'Request verification failed',403)
  self.actor=user['username'];return user
 def do_HEAD(self):self.do_GET()
 def do_GET(self):self.handle_request()
 def do_POST(self):self.handle_request()
 def handle_request(self):
  self.actor='anonymous';self.connection.settimeout(15)
  try:
   self.guard()
   with self.app.manager.lock:self.route()
  except Error as error:
   path=urlsplit(self.path).path[:150]
   self.app.store.audit(self.actor,'request.denied','denied',self.client_address[0],{'path':path,'status':error.status},('warning','Rejected administrator request: '+str(error)) if error.status in (403,413,415,429) else None)
   if self.command not in ('GET','HEAD'):self.close_connection=True
   self.send(error.status,{'error':str(error)})
  except (BrokenPipeError,ConnectionResetError):pass
  except Exception as error:
   self.app.store.audit(self.actor,'request.error','error',self.client_address[0],{'type':type(error).__name__},('error','An administrator request failed; check service health.'))
   self.close_connection=True;self.send(500,{'error':'The operation failed. Check the activity log before retrying.'})
  finally:
   if self.remote and urlsplit(self.path).path.startswith('/api/'):
    self.app.store.audit(self.actor,'remote.request','observed',self.client_address[0],{'method':self.command,'path':urlsplit(self.path).path[:150]})
 def route(self):
  path=urlsplit(self.path).path;store=self.app.store;resources=self.app.resources;manager=self.app.manager
  if self.command in ('GET','HEAD'):
   assets={'/learning-reports.js':'learning-reports.js','/':'index.html','/index.html':'index.html','/app.js':'app.js','/run-details.js':'run-details.js','/schedule.js':'schedule.js','/contests.js':'contests.js','/administrator.js':'administrator.js','/workspace-nav.js':'workspace-nav.js','/guide.js':'guide.js','/guide-content.js':'guide-content.js','/guide.css':'guide.css','/participant-activity.js':'participant-activity.js','/participant-test.js':'participant-test.js','/team-connections.js':'team-connections.js','/remote-access.js':'remote-access.js','/dashboard-branding.js':'dashboard-branding.js','/participant-identity-editor.js':'participant-identity-editor.js','/notifications.js':'notifications.js','/row-interactions.js':'row-interactions.js','/review.html':'review.html','/review.js':'review.js','/review.css':'review.css','/app.css':'app.css'}
   shared={'/download-feedback.js':('lcpc/branding/download-feedback.js','text/javascript; charset=utf-8'),'/download-feedback.css':('lcpc/branding/download-feedback.css','text/css; charset=utf-8'),'/participant-theme.js':('lcpc/branding/participant-theme.js','text/javascript; charset=utf-8'),'/contest-clock.js':('lcpc/branding/contest-clock.js','text/javascript; charset=utf-8'),'/contest-clock.css':('lcpc/branding/contest-clock.css','text/css; charset=utf-8'),'/scoreboards.js':('lcpc/public-standings/scoreboards.js','text/javascript; charset=utf-8'),'/scoreboards.css':('lcpc/public-standings/scoreboards.css','text/css; charset=utf-8'),'/scoreboard-model.js':('lcpc/branding/scoreboard-model.js','text/javascript; charset=utf-8'),'/scoreboard-base.css':('lcpc/branding/standings.css','text/css; charset=utf-8')}
   if path in shared:
    file,kind=shared[path];self.send(200,(ROOT/file).read_bytes(),kind);return
   if path in assets:
    p=ROOT/'lcpc/admin-ui'/assets[path];self.send(200,p.read_bytes(),{'html':'text/html; charset=utf-8','js':'text/javascript; charset=utf-8','css':'text/css; charset=utf-8'}[p.suffix[1:]]);return
   if path in ('/assets/omu-logo.png','/assets/lcpc-logo.png','/assets/pc2-logo.png','/assets/icpc-logo.png'):
    self.send(200,(ROOT/'lcpc/branding/assets'/Path(path).name).read_bytes(),'image/png');return
   if branding_route(self,path):return
   user=self.user()
   if remote_route(self,path):return
   if native_route(self,path):return
   if participant_route(self,path):return
   if participant_test_route(self,path):return
   if connections_route(self,path):return
   if review_route(self,path):return
   if learning_route(self,path):return
   if scoreboards_route(self,path):return
   if participant_identity_route(self,path):return
   if notifications_route(self,path):return
   if path=='/api/contests':self.send(200,manager.listing());return
   if path=='/api/timezones':self.send(200,{'countries':schedule_countries()});return
   if path=='/api/me':self.send(200,{'username':user['username'],'role':user['role'],'csrf':user['csrf'],'mustChange':bool(user['must_change']),'totpEnabled':bool(user['totp']),'remote':self.remote});return
   if path=='/api/snapshot':
    if manager.busy():
     cached=getattr(self.app.bridge,'cached',None)
     if cached is None and manager.selected()['status']=='draft':cached=self.app.bridge.snapshot()
     if cached is None:
      saved=resources.base/'last-snapshot.json';cached=json.loads(saved.read_text()) if saved.exists() else None
     require(cached,'Contest operation in progress. Open Contests for progress.',409)
    else:
     cached=self.app.bridge.snapshot()
     if manager.data['selected']==manager.data['active']:write_json(resources.base/'last-snapshot.json',cached)
    value={**annotate_difficulties(cached,resources),'resources':resources.resources(),'system':self.app.status()}
    if user['role']=='owner':
     try:
      value['participantActivitySummary']=activity_store(self.app).summary() if not manager.busy() or (resources.state/'participant-activity/activity.sqlite3').exists() else {'paused':True}
      if manager.data['active']==manager.data['selected'] and getattr(getattr(self.app,'participant_monitor',None),'failed',False):value['participantActivitySummary']['unavailable']=True
     except Exception:value['participantActivitySummary']={'unavailable':True}
     with store.db() as db:value['securitySummary']={'unacknowledged':db.execute('SELECT count(*) FROM alerts WHERE acknowledged=0').fetchone()[0]}
    self.send(200,value);return
   if path in ('/api/source','/api/diagnostics','/api/test-data'):
    q=review_query(self)
    try:args={'number':int(q.get('number',[''])[0]),'site':int(q.get('site',['1'])[0])}
    except ValueError:raise Error(400,'Invalid submission')
    require(1<=args['number']<=2147483647 and 1<=args['site']<=999,'Invalid submission')
    op={'/api/source':'source','/api/diagnostics':'diagnostics','/api/test-data':'test-data'}[path]
    if op=='test-data':
     try:args['test']=int(q.get('test',[''])[0])
     except ValueError:raise Error(400,'Invalid test number')
     require(1<=args['test']<=10000,'Invalid test number')
    data=self.app.bridge.call(op,args);store.audit(self.actor,'submission.'+op,'success',details={**args,'contestId':manager.data['selected']});self.send(200,data);return
   if path=='/api/resources/trash':
    self.user('operator');self.send(200,{'resources':resources.resources(deleted=True)});return
   if path=='/api/security':
    self.user('owner')
    with store.db() as db:
     events=[dict(r) for r in db.execute('SELECT * FROM audit ORDER BY id DESC LIMIT 300')]
     alerts=[dict(r) for r in db.execute('SELECT * FROM alerts ORDER BY id DESC LIMIT 300')]
     users=[dict(r) for r in db.execute('SELECT username,role,must_change,enabled,length(totp)>0 AS totpEnabled FROM users')]
     sessions=[dict(r) for r in db.execute('SELECT token AS id,username,created,seen,peer,channel FROM sessions ORDER BY seen DESC')]
    self.send(200,{'events':events,'alerts':alerts,'users':users,'sessions':sessions,'integrity':store.verify_audit()});return
   match=re.fullmatch('/api/resources/([a-f0-9]{32})/download',path)
   if match:
    row=next((r for r in resources.resources() if r['id']==match[1]),None);require(row,'Resource not found',404)
    body=(resources.uploads/row['id']).read_bytes();require(hashlib.sha256(body).hexdigest()==row['sha256'],'Resource integrity check failed',409)
    self.send(200,body,row['mime'],{'Content-Disposition':'attachment; filename="resource'+Path(row['filename']).suffix.lower()+'"'});return
   raise Error(404,'Not found')
  require(self.command=='POST','Method not allowed',405);data=self.body()
  if path=='/api/login':
   if self.remote:require(self.app.remote.permitted(self.client_address[0],data.get('username','')),'Remote login is not approved for this account and IP.',403)
   token,user,csrf=store.login(data.get('username'),data.get('password'),data.get('code',''),self.client_address[0],'remote' if self.remote else 'local');self.send(200,{'username':user['username'],'role':user['role'],'csrf':csrf,'mustChange':bool(user['must_change']),'totpEnabled':bool(user['totp']),'remote':self.remote},'application/json',{'Set-Cookie':self.cookie(token)});return
  user=self.user()
  if remote_route(self,path,data):return
  if branding_route(self,path,data):return
  if participant_identity_route(self,path,data):return
  if notifications_route(self,path,data):return
  if learning_route(self,path,data):return
  if path.startswith('/api/native/'):
   if native_route(self,path,data):return
  if participant_route(self,path,data):return
  if participant_test_route(self,path,data):return
  if connections_route(self,path,data):return
  if path=='/api/logout':
   with store.db() as db:db.execute('DELETE FROM sessions WHERE token=?',(digest(self.token()),))
   store.audit(self.actor,'logout','success');self.send(200,{'ok':True},headers={'Set-Cookie':self.cookie(delete=True)});return
  if path.startswith('/api/contests/'):
   self.user('owner');manager.guard(data);op=path.rsplit('/',1)[1]
   if op=='select':manager.select(data.get('id'));store.audit(self.actor,'contest.select','success',details={'id':data.get('id')});self.send(200,{'ok':True});return
   if op=='create':
    require(data.get('confirm')=='CONFIRM','Confirmation required');result=manager.create(data);store.audit(self.actor,'contest.create','success',details={'id':result['id'],'template':manager.data['selected']});self.send(200,result);return
   cid=data.get('id');row=manager.row(cid)
   if op in ('activate','deactivate','backup','recover'):
    require(data.get('confirm')=='CONFIRM','Confirmation required');self.send(202,manager.start_job(op,cid,self.actor));return
   if op=='release-stopped':
    require(data.get('confirm')=='CONFIRM','Confirmation required');self.send(200,manager.release_stopped(cid));store.audit(self.actor,'contest.release-stopped','success',details={'id':cid});return
   if op in ('archive','unarchive'):
    require(data.get('confirm')=='CONFIRM','Confirmation required');self.send(200,manager.archive(cid,op=='archive'));store.audit(self.actor,'contest.'+op,'success',details={'id':cid});return
   if op=='draft-settings':
    require(row['status']=='draft','Only draft settings may be changed here',409);require(data.get('confirm')=='CONFIRM','Confirmation required');path=Path(row['state'])/'admin-dashboard/draft.json';draft=json.loads(path.read_text())
    require(type(data.get('durationMinutes')) is int and 1<=data['durationMinutes']<=1440,'Duration must be 1–1440 minutes');require(type(data.get('penaltyMinutes')) is int and 0<=data['penaltyMinutes']<=120,'Penalty must be 0–120 minutes')
    draft['contest']['lengthSeconds']=data['durationMinutes']*60;draft['penaltyMinutes']=data['penaltyMinutes'];write_json(path,draft);store.audit(self.actor,'contest.draft-settings','success',details={'id':cid});self.send(200,{'ok':True});return
   if op=='export':
    require(data.get('format') in ('csv','pdf'),'Choose CSV or PDF');value=report_data(manager,row);body=csv_report(value) if data['format']=='csv' else pdf_report(value);ext='zip' if data['format']=='csv' else 'pdf'
    store.audit(self.actor,'contest.export','success',details={'id':cid,'format':data['format']});self.send(200,body,'application/zip' if ext=='zip' else 'application/pdf',{'Content-Disposition':'attachment; filename="'+cid+'-report.'+ext+'"'});return
   if op=='download-backup':
    bid=data.get('backupId','');require(isinstance(bid,str) and re.fullmatch('[a-f0-9]{32}',bid),'Invalid backup');folder=manager.base/'backups'/bid;require((folder/'manifest.json').exists(),'Backup not found',404);metadata=json.loads((folder/'manifest.json').read_text());require(metadata['contestId']==cid,'Backup does not belong to this contest',409)
    body=(folder/'backup.zip').read_bytes();store.audit(self.actor,'contest.backup-download','success',details={'id':cid,'backupId':bid});self.send(200,body,'application/zip',{'Content-Disposition':'attachment; filename="'+cid+'-backup.zip"'});return
   if op=='recovery-key':
    require(data.get('confirm')=='CONFIRM','Confirmation required')
    with store.db() as db:owner=db.execute('SELECT * FROM users WHERE username=?',(self.actor,)).fetchone()
    require(password_ok(data.get('password',''),owner['password']),'Current password is incorrect',403);require(not owner['totp'] or any(hmac.compare_digest(totp(owner['totp'],time.time()+n*30),str(data.get('code',''))) for n in (-1,0,1)),'A valid authenticator code is required',403)
    import io,zipfile
    folder=ROOT/'.local/backup-keys';require((folder/'recipient.key').exists(),'Create a full backup first',409);body=io.BytesIO()
    with zipfile.ZipFile(body,'w') as archive:
     for name in ('recipient.key','recipient.crt'):archive.write(folder/name,name)
     archive.writestr('README.txt','Keep this recovery key separately from your backup archives. Anyone with this key can decrypt ALL archives encrypted for it. Store it securely off this server. Never share it with teams.\n')
    store.audit(self.actor,'contest.recovery-key-download','success',details={'id':cid},alert=('warning','The backup recovery key was downloaded by an owner.'));self.send(200,body.getvalue(),'application/zip',{'Content-Disposition':'attachment; filename="lcpc-recovery-key.zip"'});return
   raise Error(404,'Not found')
  if path=='/api/schedule/preview':
   self.send(200,schedule_preview(data.get('local',''),data.get('country'),data.get('timeZone'),data.get('instant')));return
  if path=='/api/password':
   store.change_password(user['username'],data.get('current',''),data.get('password',''),data.get('code',''));store.audit(self.actor,'password.changed','success');self.send(200,{'ok':True},headers={'Set-Cookie':self.cookie(delete=True)});return
  if path=='/api/operation':
   self.user('operator');manager.guard(data);manager.allow_native_mutation();op=data.get('operation');require(op in MUTATIONS,'Unsupported operation');args=data.get('args',{});require(isinstance(args,dict),'Invalid arguments')
   if op in OWNER_OPS:self.user('owner')
   require(data.get('confirm')=='CONFIRM','Explicit confirmation is required')
   validate_operation(op,args)
   if op=='team.update':
    from test_team import LOGIN
    require(args['login']!=LOGIN,'The reserved test account is managed from Participant test & access',409)
   preferences=None
   if op=='contest.update':args,preferences=normalize_schedule(args,self.app.bridge.snapshot()['contest'].get('scheduledStart'))
   # Audit intent before calling the bridge, then separately record its outcome.
   safe={'contestId':manager.data['selected'],**{key:value for key,value in args.items() if key in ('login','id','number','site','seconds','reason','mode','expectedJudgement','scheduledStart','scheduleTimeZone')}}
   if preferences:safe['scheduleCountry']=preferences['country']
   store.audit(self.actor,op,'requested',details=safe)
   try:result=self.app.bridge.call(op,args)
   except Exception:
    store.audit(self.actor,op,'failed',details=safe,alert=('error','PC2 did not confirm '+op));raise
   if preferences:resources.save_schedule_preferences(preferences)
   resources.publish_catalog(self.app.bridge.snapshot(fresh=True));store.audit(self.actor,op,'success',details=safe);self.send(200,result);return
  if path=='/api/problems/create':
   self.user('owner');manager.guard(data);manager.allow_native_mutation();require(data.get('confirm')=='CONFIRM','Confirmation required')
   args=data.get('args',{});require(isinstance(args,dict),'Invalid problem settings');snapshot=self.app.bridge.snapshot(fresh=True)
   require(not snapshot['contest']['running'],'Pause the contest before adding a judged problem',409)
   require(args.get('template') in {p['id'] for p in snapshot['problems']} or (manager.selected()['status']=='draft' and args.get('template')=='__default__'),'Choose an existing sandbox profile')
   require(isinstance(args.get('name'),str) and 1<=len(args['name'].strip())<=200,'Invalid problem name')
   require(re.fullmatch('[A-Z]{1,3}',str(args.get('letter',''))),'Use an uppercase problem letter')
   require(type(args.get('timeLimit')) is int and 1<=args['timeLimit']<=10,'Time limit must be 1–10 seconds')
   require(type(args.get('memoryLimit')) is int and 32<=args['memoryLimit']<=1024,'Memory limit must be 32–1024 MiB')
   validate_problem_color(args)
   directory=prepare_judge_data(resources,data.get('base64'))
   safe={key:args[key] for key in ('name','letter','timeLimit','memoryLimit','template')};safe.update({key:args[key] for key in ('colorName','colorRGB') if key in args});safe['directory']=str(directory)
   store.audit(self.actor,'problem.create','requested',details={'letter':args['letter'],'name':args['name'],'contestId':manager.data['selected']})
   result=self.app.bridge.call('problem.create',safe);resources.publish_catalog(self.app.bridge.snapshot(fresh=True));store.audit(self.actor,'problem.create','success',details={'id':result.get('id'),'letter':args['letter'],'contestId':manager.data['selected']});self.send(200,result);return
  if path.startswith('/api/resources/'):
   self.user('operator');manager.guard(data);manager.allow_native_mutation();snapshot=self.app.bridge.snapshot();problem_ids={p['id'] for p in snapshot['problems']}|{'__contest__'}
   if path=='/api/resources/upload':
    require(data.get('problem') in problem_ids,'Choose an existing problem')
    require((data.get('kind')=='booklet')==(data.get('problem')=='__contest__'),'Booklets belong to the contest; statements and helpers belong to a problem')
    rid=resources.upload(data);store.audit(self.actor,'resource.upload','success',details={'id':rid,'problem':data['problem'],'kind':data['kind'],'language':data.get('language'),'contestId':manager.data['selected']});self.send(200,{'ok':True,'id':rid,'published':False});return
   require(data.get('confirm')=='CONFIRM','Explicit confirmation is required')
   rid=data.get('id');candidates=resources.resources(deleted=path=='/api/resources/restore');row=next((r for r in candidates if r['id']==rid),None);require(row,'Resource not found',404)
   with resources.db() as db:
    if path=='/api/resources/publish':
     require(type(data.get('published')) is bool,'Invalid publication flag');published=data['published'];require(row['problem'] in problem_ids,'The linked problem no longer exists')
     if published and row['kind'] in ('statement','booklet'):db.execute('UPDATE resources SET published=0 WHERE problem=? AND kind=? AND language=?',(row['problem'],row['kind'],row['language']))
     db.execute('UPDATE resources SET published=? WHERE id=?',(int(published),rid));event='resource.publish' if published else 'resource.unpublish'
    elif path=='/api/resources/restore':db.execute('UPDATE resources SET deleted=0,published=0 WHERE id=?',(rid,));event='resource.restore'
    elif path=='/api/resources/delete':db.execute('UPDATE resources SET deleted=1,published=0 WHERE id=?',(rid,));event='resource.delete'
    else:raise Error(404,'Not found')
   resources.publish_catalog(snapshot);store.audit(self.actor,event,'success',details={'id':rid,'problem':row['problem'],'contestId':manager.data['selected']});self.send(200,{'ok':True});return
  if path=='/api/totp/setup':
   secret=base64.b32encode(secrets.token_bytes(20)).decode().rstrip('=')
   with store.db() as db:
    row=db.execute('SELECT * FROM users WHERE username=?',(self.actor,)).fetchone();require(password_ok(data.get('password',''),row['password']),'Current password is incorrect',403);require(not row['totp'],'Two-step verification is already enabled',409)
    db.execute('UPDATE users SET pending_totp=?,pending_totp_created=? WHERE username=?',(secret,time.time(),self.actor))
   self.send(200,totp_provisioning(secret,self.actor));return
  if path=='/api/totp/enable':
   with store.db() as db:
    row=db.execute('SELECT * FROM users WHERE username=?',(self.actor,)).fetchone();require(row['pending_totp'] and row['pending_totp_created']>time.time()-300 and hmac.compare_digest(totp(row['pending_totp']),str(data.get('code',''))),'Invalid verification code',403)
    db.execute('UPDATE users SET totp=pending_totp,pending_totp=\'\',last_totp=? WHERE username=?',(int(time.time()//30),self.actor));db.execute('DELETE FROM sessions WHERE username=? AND token<>?',(self.actor,digest(self.token())))
   store.audit(self.actor,'totp.enabled','success');self.send(200,{'ok':True});return
  if path=='/api/totp/disable':
   with store.db() as db:
    row=db.execute('SELECT * FROM users WHERE username=?',(self.actor,)).fetchone();require(password_ok(data.get('password',''),row['password']) and row['totp'] and hmac.compare_digest(totp(row['totp']),str(data.get('code',''))),'Invalid password or verification code',403)
    db.execute('UPDATE users SET totp=\'\' WHERE username=?',(self.actor,))
   store.audit(self.actor,'totp.disabled','success',alert=('warning','Two-step verification was disabled for '+self.actor));self.send(200,{'ok':True});return
  self.user('owner')
  if path=='/api/users/create':
   username=data.get('username','');require(re.fullmatch('[a-z][a-z0-9_-]{2,31}',username),'Use 3–32 lowercase letters, digits, _ or -');require(data.get('role') in ('owner','operator','viewer'),'Invalid role');password_policy(data.get('password'))
   with store.db() as db:
    require(not db.execute('SELECT 1 FROM users WHERE username=?',(username,)).fetchone(),'Username exists',409);db.execute('INSERT INTO users(username,password,role) VALUES(?,?,?)',(username,password_hash(data['password']),data['role']))
   store.audit(self.actor,'user.created','success',details={'username':username,'role':data['role']});self.send(200,{'ok':True});return
  if path=='/api/users/disable':
   username=data.get('username');require(username!=self.actor,'You cannot disable your current account');require(data.get('confirm')=='CONFIRM','Confirmation required')
   with store.db() as db:db.execute('UPDATE users SET enabled=0 WHERE username=?',(username,));db.execute('DELETE FROM sessions WHERE username=?',(username,))
   store.audit(self.actor,'user.disabled','success',details={'username':username});self.send(200,{'ok':True});return
  if path=='/api/sessions/revoke':
   with store.db() as db:db.execute('DELETE FROM sessions WHERE token=?',(data.get('id',''),))
   store.audit(self.actor,'session.revoked','success');self.send(200,{'ok':True});return
  if path=='/api/alerts/acknowledge':
   with store.db() as db:db.execute('UPDATE alerts SET acknowledged=1 WHERE id=?',(data.get('id'),))
   store.audit(self.actor,'alert.acknowledged','success',details={'id':data.get('id')});self.send(200,{'ok':True});return
  raise Error(404,'Not found')
class Server(ThreadingHTTPServer):
 daemon_threads=True;request_queue_size=24
 def __init__(self,address,app,remote=False,tls_context=None):self.app=app;self.remote=remote;self.tls_context=tls_context;self.slots=threading.BoundedSemaphore(8);super().__init__(address,Handler)
 def get_request(self):
  sock,addr=super().get_request();sock.settimeout(5 if self.remote else 15)
  if self.remote:
   if not self.app.remote.permitted(addr[0]):sock.close();self.app.remote.denied(addr[0]);raise OSError('Unapproved remote IP')
   sock=self.tls_context.wrap_socket(sock,server_side=True,do_handshake_on_connect=False)
  return sock,addr
 def process_request(self,request,address):
  if not self.slots.acquire(False):request.close();return
  try:super().process_request(request,address)
  except Exception:self.slots.release();raise
 def process_request_thread(self,request,address):
  try:
   if self.remote:request.do_handshake();request.settimeout(15)
   super().process_request_thread(request,address)
  except (ssl.SSLError,OSError):self.shutdown_request(request)
  finally:self.slots.release()
def main():
 os.umask(0o077);parser=argparse.ArgumentParser();parser.add_argument('--state',required=True);parser.add_argument('--port',type=int,default=8091);parser.add_argument('--prepare-learning',action='store_true');args=parser.parse_args()
 app=App(args.state,args.port);require(app.store.dbpath.exists(),'Initialize dashboard first');server=Server(('127.0.0.1',args.port),app)
 def stop(*_):threading.Thread(target=server.shutdown,daemon=True).start()
 signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
 app.store.audit('system','dashboard.started','success');print('Organizer dashboard: http://127.0.0.1:'+str(args.port),flush=True)
 observer=ActivityMonitor(app);app.participant_monitor=observer;observer.start()
 if args.prepare_learning:app.manager.start_job('learning',app.manager.data['selected'],'system')
 try:app.remote.start()
 except Exception as error:app.remote.error='Remote HTTPS could not start. Review Remote dashboard access from the server.';app.store.audit('system','remote.start-failed','failed',details={'type':type(error).__name__},alert=('error',app.remote.error))
 try:server.serve_forever(poll_interval=.3)
 finally:app.remote.stop();observer.close();app.manager.close();server.server_close();app.store.audit('system','dashboard.stopped','success')
if __name__=='__main__':main()
