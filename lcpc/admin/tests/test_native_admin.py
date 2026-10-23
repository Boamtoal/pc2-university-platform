import base64,http.client,io,json,sys,tempfile,threading,time,unittest,zipfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]));sys.path.insert(0,str(Path(__file__).resolve().parent))
from core import password_hash,Error
from server import App,Server
from native_admin import prepare_replay,sensitive
from test_contests import Fake
class NativeFake(Fake):
 def __init__(self,state):super().__init__(state);self.writes=[]
 def call(self,op,args=None):
  args=args or {};self.calls.append((op,args))
  if op=='admin.catalog':return {'sections':[],'permissions':['LOGIN'],'groups':[],'accounts':[],'problems':[],'languages':[],'reports':[]}
  if op=='admin.query':return {'rows':[],'domain':args['section']}
  if op=='admin.tests':return {'rows':[{'test':1,'input':'01.in','answer':'01.ans'}]}
  if op=='admin.logs':return {'text':'fixture [REDACTED]','truncated':False}
  if op=='admin.report':return {'text':'Native report fixture'}
  if op=='source':return {'files':[{'name':'main.cpp','base64':base64.b64encode(('int x = '+str(args['number'])+';').encode()).decode()}]}
  if op=='admin.execute':
   if args['command']=='configuration.preview':return {'token':'a'*32,'count':1,'changes':[{'action':'update','record':'Fixture group'}]}
   if args.get('preview'):return {'ok':True,'count':len(args['rows'])}
   self.writes.append(args)
   if args['command'] in ('accounts.bulk','accounts.import','configuration.commit'):return {'ok':True,'count':1,'credentials':[{'site':1,'login':'team9','name':'Fixture nine','password':'Fixture-generated-password-42'}]}
   return {'ok':True}
  raise Error(400,'Unknown fixture operation')
class NativeHTTP(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.temp=tempfile.TemporaryDirectory();cls.state=Path(cls.temp.name).resolve();cls.fake=NativeFake(cls.state);cls.app=App(cls.state,0,cls.fake);cls.server=Server(('127.0.0.1',0),cls.app);cls.port=cls.server.server_address[1];cls.origin='http://127.0.0.1:'+str(cls.port);cls.app.origins={cls.origin};cls.password='Native-test-owner-password'
  with cls.app.store.db() as db:
   for name,role in [('owner','owner'),('operator','operator'),('viewer','viewer')]:db.execute('INSERT INTO users(username,password,role,must_change) VALUES(?,?,?,0)',(name,password_hash(cls.password),role))
  threading.Thread(target=cls.server.serve_forever,daemon=True).start()
 @classmethod
 def tearDownClass(cls):cls.server.shutdown();cls.server.server_close();cls.app.manager.close();cls.temp.cleanup()
 def request(self,path,data=None,cookie=None,csrf=None):
  headers={'Host':self.origin.split('//')[1]}
  if data is not None:headers.update({'Origin':self.origin,'Content-Type':'application/json'})
  if cookie:headers['Cookie']=cookie
  if csrf:headers['X-CSRF-Token']=csrf
  c=http.client.HTTPConnection('127.0.0.1',self.port,timeout=10);c.request('GET' if data is None else 'POST',path,None if data is None else json.dumps(data),headers);r=c.getresponse();out=(r.status,dict(r.getheaders()),r.read());c.close();return out
 def login(self,user='owner'):
  status,h,b=self.request('/api/login',{'username':user,'password':self.password});self.assertEqual(status,200);return h['Set-Cookie'].split(';')[0],json.loads(b)['csrf']
 def post(self,path,data,user='owner'):
  cookie,csrf=self.login(user);return self.request(path,{'contestId':self.app.manager.data['selected'],**data},cookie,csrf)
 def action(self,args,**extra):return self.post('/api/native/execute',{'args':args,'confirm':'CONFIRM','reason':'Fixture native action',**extra})
 def test_01_owner_only_catalog_and_private_data(self):
  self.assertEqual(self.request('/api/native/catalog')[0],401)
  for role in ('viewer','operator'):
   cookie,csrf=self.login(role)
   self.assertEqual(self.request('/api/native/catalog',cookie=cookie)[0],403)
   self.assertEqual(self.post('/api/native/tests',{'id':'p1'},role)[0],403)
   self.assertEqual(self.post('/api/native/execute',{'args':{'command':'save'},'confirm':'CONFIRM','reason':'Fixture reason'},role)[0],403)
  cookie,csrf=self.login();self.assertEqual(self.request('/api/native/catalog',cookie=cookie)[0],200)
 def test_02_csrf_context_and_explicit_command_allowlist(self):
  before=len(self.fake.writes);cookie,csrf=self.login();payload={'contestId':self.state.name,'args':{'command':'clocks.pauseAll'},'confirm':'CONFIRM','reason':'Fixture action'}
  self.assertEqual(self.request('/api/native/execute',payload,cookie)[0],403)
  payload['contestId']='wrong-workspace';self.assertEqual(self.request('/api/native/execute',payload,cookie,csrf)[0],409)
  self.assertEqual(self.action({'command':'runtime.shutdown'})[0],400)
  self.assertEqual(self.action({'command':'save','domain':'groups','directory':'/tmp/private'})[0],400)
  self.assertEqual(len(self.fake.writes),before)
 def test_03_sensitive_mutations_require_owner_reauth(self):
  before=len(self.fake.writes)
  for args in ({'command':'save','domain':'accounts','fields':{}},{'command':'save','domain':'languages','fields':{}},{'command':'submit.onBehalf'},{'command':'run.rejudgeBatch'},{'command':'configuration.commit','token':'a'*32}):
   self.assertEqual(self.action(args)[0],403)
  self.assertEqual(len(self.fake.writes),before)
  self.assertEqual(self.action({'command':'save','domain':'groups','fields':{'DisplayName':'Division'}})[0],200)
 def test_04_credential_download_does_not_enter_audit(self):
  status,h,b=self.action({'command':'accounts.bulk','type':'TEAM','site':1,'count':1,'prefix':'Team'},password=self.password);self.assertEqual(status,200);self.assertEqual(h['Content-Type'],'text/csv; charset=utf-8');self.assertIn(b'Fixture-generated-password-42',b)
  self.assertNotIn('Fixture-generated-password-42',self.app.store.dbpath.read_bytes().decode('latin1'))
  with self.app.store.db() as db:events=''.join(row[0] for row in db.execute('SELECT details FROM audit'))
  self.assertNotIn(self.password,events);self.assertNotIn('Fixture-generated-password-42',events)
 def test_05_csv_preview_omits_passwords_and_commit_consumes_plan(self):
  data=base64.b64encode(b'name,type,password\nCSV fixture,TEAM,CSV-private-password-42\n').decode();status,h,b=self.post('/api/native/import-preview',{'base64':data});self.assertEqual(status,200);value=json.loads(b);self.assertNotIn(b'CSV-private-password-42',b)
  token=value['token'];self.assertEqual(self.action({'command':'accounts.import','token':token},password=self.password)[0],200)
  self.assertEqual(self.action({'command':'accounts.import','token':token},password=self.password)[0],409)
 def test_06_private_reports_and_log_path_restrictions(self):
  self.assertEqual(self.post('/api/native/report',{'report':'AccountsReport'})[0],403)
  status,h,b=self.post('/api/native/report',{'report':'AccountsReport','password':self.password});self.assertEqual(status,200);self.assertIn('attachment',h['Content-Disposition'])
  self.assertEqual(self.post('/api/native/logs',{'role':'../../credentials.properties'})[0],400)
  self.assertEqual(self.post('/api/native/logs',{'role':'server'})[0],200)
 def test_07_configuration_preview_is_readonly_and_commit_zip(self):
  before=len(self.fake.writes);status,h,b=self.post('/api/native/configuration-preview',{'bundle':{'format':'PC2-DASHBOARD-CONFIG-1','domain':'groups','records':[]}});self.assertEqual(status,200);self.assertEqual(len(self.fake.writes),before)
  token=json.loads(b)['token'];status,h,b=self.action({'command':'configuration.commit','token':token},password=self.password);self.assertEqual(status,200);self.assertEqual(h['Content-Type'],'application/zip')
  with zipfile.ZipFile(io.BytesIO(b)) as archive:self.assertIn('created-account-credentials.csv',archive.namelist())
 def test_08_compare_is_readonly_and_source_never_audited(self):
  before=len(self.fake.writes);status,h,b=self.post('/api/native/compare',{'runs':[{'number':1,'site':1},{'number':2,'site':1}]});self.assertEqual(status,200);self.assertIn('int x = 1',json.loads(b)['diff']);self.assertEqual(len(self.fake.writes),before)
  with self.app.store.db() as db:self.assertNotIn('int x',str([tuple(r) for r in db.execute('SELECT details FROM audit')]))
 def test_09_reset_requires_backup_and_exact_workspace(self):
  args={'command':'reset.perform'};self.assertEqual(self.action(args,password=self.password,resetContestId='wrong')[0],400)
  self.assertEqual(self.action(args,password=self.password,resetContestId=self.state.name)[0],409)
 def test_10_staged_playback_zip_path_and_reference_limits(self):
  def package(entries):
   out=io.BytesIO()
   with zipfile.ZipFile(out,'w') as archive:
    for name,value in entries.items():archive.writestr(name,value)
   return base64.b64encode(out.getvalue()).decode()
  for entries in ({'../x.txt':'x','playback.txt':'event'},{'playback.txt':'RUN|../credentials.properties'},{'playback.txt':'RUN|/etc/passwd'},{'playback.txt':'RUN|$HOME/key'},{'playback.txt':'RUN|main.exe','main.exe':'x'}):
   with self.assertRaises(Error):prepare_replay(self.app.resources,package(entries))
  directory,main=prepare_replay(self.app.resources,package({'playback.txt':'action=RUN_SUBMIT|mainfile=main.cpp|id=1','main.cpp':'int main() {}'}));self.assertTrue((directory/main).exists());self.assertIn(str(directory/'main.cpp'),(directory/main).read_text())
 def test_12_refresh_failure_does_not_lose_created_credentials(self):
  original=self.fake.snapshot
  def unavailable(*args,**kwargs):raise Error(503,'Fixture refresh interruption')
  self.fake.snapshot=unavailable
  try:
   status,h,b=self.action({'command':'accounts.bulk','type':'TEAM','site':1,'count':1,'prefix':'Team'},password=self.password);self.assertEqual(status,200);self.assertIn(b'Fixture-generated-password-42',b)
  finally:self.fake.snapshot=original
 def test_11_empty_import_and_malformed_fields_fail_closed(self):
  self.assertEqual(self.post('/api/native/import-preview',{'base64':''})[0],400)
  self.assertEqual(self.action({'command':'save','domain':'languages','fields':[]})[0],400)
if __name__=='__main__':unittest.main(verbosity=2)
