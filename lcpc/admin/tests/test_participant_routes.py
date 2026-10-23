import csv,http.client,io,json,sys,tempfile,threading,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]));sys.path.insert(0,str(Path(__file__).resolve().parent))
from core import password_hash
from server import App,Server
from participant_activity import activity_store
from test_contests import Fake
class Routes(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.temp=tempfile.TemporaryDirectory();cls.state=Path(cls.temp.name).resolve();cls.fake=Fake(cls.state);cls.app=App(cls.state,0,cls.fake);cls.http=Server(('127.0.0.1',0),cls.app);cls.origin='http://127.0.0.1:'+str(cls.http.server_port);cls.app.origins={cls.origin};cls.password='Fixture-owner-password-42'
  with cls.app.store.db() as db:
   for role in ['owner','operator','viewer']:db.execute('INSERT INTO users(username,password,role,must_change) VALUES(?,?,?,0)',(role,password_hash(cls.password),role))
  threading.Thread(target=cls.http.serve_forever,daemon=True).start()
 @classmethod
 def tearDownClass(cls):cls.http.shutdown();cls.http.server_close();cls.app.manager.close();cls.temp.cleanup()
 def req(self,path,data=None,cookie=None,csrf=None):
  headers={'Host':self.origin.split('//')[1],'Origin':self.origin,'Content-Type':'application/json'}
  if cookie:headers['Cookie']=cookie
  if csrf:headers['X-CSRF-Token']=csrf
  c=http.client.HTTPConnection('127.0.0.1',self.http.server_port,timeout=10);c.request('GET' if data is None else 'POST',path,None if data is None else json.dumps(data),headers);r=c.getresponse();out=r.status,dict(r.getheaders()),r.read();c.close();return out
 def login(self,role='owner'):
  _,h,b=self.req('/api/login',{'username':role,'password':self.password});return h['Set-Cookie'].split(';')[0],json.loads(b)['csrf']
 def post(self,path,data,role='owner',csrf=True):
  cookie,token=self.login(role);return self.req(path,{'contestId':self.app.manager.data['selected'],**data},cookie,token if csrf else None)
 def test_01_owner_boundary_and_static_modules(self):
  self.assertEqual(self.req('/api/participant-activity')[0],401)
  for role in ['operator','viewer']:
   cookie,_=self.login(role);self.assertEqual(self.req('/api/participant-activity',cookie=cookie)[0],403);self.assertEqual(self.req('/api/participant-test',cookie=cookie)[0],403)
  for script in ['/participant-activity.js','/participant-test.js','/row-interactions.js']:self.assertEqual(self.req(script)[0],200)
 def test_02_query_export_csrf_and_incident_management(self):
  store=activity_store(self.app);store.record('browser.error',login='team7',source='browser',severity='error',incident=True);cookie,_=self.login();status,h,b=self.req('/api/participant-activity?team=team7',cookie=cookie);self.assertEqual(status,200);self.assertEqual(json.loads(b)['events'][0]['team'],'team7');iid=json.loads(b)['issues'][0]['id'];self.assertEqual(self.post('/api/participant-activity/issue',{'id':iid,'action':'resolve'},csrf=False)[0],403);self.assertEqual(self.post('/api/participant-activity/issue',{'id':iid,'action':'resolve'})[0],200);self.assertEqual(self.post('/api/participant-activity/integrity',{})[0],200);status,h,b=self.post('/api/participant-activity/export',{'filters':{'team':'team7'}});self.assertEqual(status,200);self.assertIn(b'browser.error',b)
 def test_03_workspace_isolation_and_invalid_filters(self):
  cookie,_=self.login();self.assertEqual(self.req('/api/participant-activity?team=team7%27%20OR%201=1',cookie=cookie)[0],400);self.assertEqual(self.req('/api/participant-activity?path=/private',cookie=cookie)[0],400);self.assertEqual(self.post('/api/participant-activity/issue',{'contestId':'other','id':1,'action':'resolve'})[0],409)
 def test_04_prepare_rehearsal_reauth_and_no_auto_switch_or_start(self):
  before=self.app.manager.data['active'];arguments={'durationMinutes':120,'publishResources':True,'confirm':'CONFIRM'};self.assertEqual(self.post('/api/participant-test/prepare',arguments)[0],403);status,h,b=self.post('/api/participant-test/prepare',{**arguments,'password':self.password});self.assertEqual(status,200);self.assertIn('text/csv',h['Content-Type']);row=next(csv.DictReader(io.StringIO(b.decode('utf-8-sig'))));self.assertEqual(row['login'],'team1');self.assertGreaterEqual(len(row['password']),32);self.assertEqual(self.app.manager.data['active'],before);self.assertEqual(self.app.manager.data['selected'],before);new=self.app.manager.row(row['contestId']);self.assertEqual(new['status'],'draft');draft=json.loads((Path(new['state'])/'admin-dashboard/draft.json').read_text());self.assertEqual(len(draft['problems']),1);self.assertEqual(len(draft['teams']),2);self.assertEqual(len([t for t in draft['teams'] if not t.get('testAccount')]),1);self.assertNotIn('runs',draft);self.assertFalse(any(op in ('clock.start','runtime.shutdown') for op,args in self.fake.calls));self.assertNotIn(row['password'],self.app.store.dbpath.read_bytes().decode('latin1'))
 def test_05_connection_monitor_roles_scope_and_alert_cursor(self):
  for role in ['viewer','operator']:
   cookie,_=self.login(role);self.assertEqual(self.req('/api/team-connections?contestId='+self.app.manager.data['selected'],cookie=cookie)[0],403)
  cookie,_=self.login();self.assertEqual(self.req('/api/team-connections?contestId=wrong',cookie=cookie)[0],409)
  store=activity_store(self.app);store.record('connection.signal_missing',login='team7',source='observer',severity='warning')
  status,h,b=self.req('/api/team-connections/alerts?contestId='+self.app.manager.data['selected'],cookie=cookie);self.assertEqual(status,200);value=json.loads(b);self.assertTrue(any(r['team']=='team7' for r in value['alerts']));self.assertNotIn('session_hash',b.decode());self.assertEqual(self.req('/api/team-connections?contestId='+self.app.manager.data['selected'],cookie=cookie)[0],200)
 def test_06_manual_checklist_rejects_stale_configuration(self):
  cookie,_=self.login();status,h,b=self.req('/api/participant-test',cookie=cookie);value=json.loads(b);args={'configuration':value['configuration'],'results':{'global|login':'passed'}}
  self.assertEqual(self.post('/api/participant-test/checklist',args,csrf=False)[0],403);self.assertEqual(self.post('/api/participant-test/checklist',args)[0],200);self.assertEqual(self.post('/api/participant-test/checklist',{**args,'configuration':'stale'})[0],409);self.assertEqual(self.post('/api/participant-test/checklist',{**args,'results':{'global|inject':'passed'}})[0],400)
 def test_07_branding_public_reads_and_owner_only_writes(self):
  status,h,b=self.req('/api/dashboard-branding');self.assertEqual(status,200);value=json.loads(b);self.assertEqual(self.req('/dashboard-theme.css')[0],200);self.assertEqual(self.req('/api/dashboard-branding/logo')[0],200)
  args={'version':value['version'],'reset':True}
  self.assertEqual(self.post('/api/dashboard-branding',args,role='viewer')[0],403);self.assertEqual(self.post('/api/dashboard-branding',args,csrf=False)[0],403);self.assertEqual(self.post('/api/dashboard-branding',args)[0],200)
 def test_08_private_test_account_reauth_roles_csrf_scope_and_secret_redaction(self):
  from test_team import LOGIN
  previous=self.app.manager.data['selected'];created=self.app.manager.create({'title':'Private test fixture','shortName':'TEST','slug':'private-test-fixture','durationMinutes':120,'penaltyMinutes':20,'workflow':'review','copyProblems':True,'copyResources':False})
  self.app.manager.select(created['id'])
  try:
   for role in ['viewer','operator']:self.assertEqual(self.post('/api/participant-test/test-account',{'password':self.password},role=role)[0],403)
   self.assertEqual(self.post('/api/participant-test/test-account',{'password':self.password},csrf=False)[0],403)
   self.assertEqual(self.post('/api/participant-test/test-account',{'password':'incorrect'})[0],403)
   self.assertEqual(self.post('/api/participant-test/test-account',{'password':self.password,'contestId':previous})[0],409)
   status,h,b=self.post('/api/participant-test/test-account',{'password':self.password});self.assertEqual(status,200);row=next(csv.DictReader(io.StringIO(b.decode('utf-8-sig'))));self.assertEqual(row['login'],LOGIN);self.assertGreaterEqual(len(row['password']),32)
   cookie,_=self.login();status,h,raw=self.req('/api/participant-test',cookie=cookie);self.assertEqual(status,200);self.assertTrue(json.loads(raw)['testAccount']['available']);self.assertNotIn(row['password'],raw.decode());self.assertIn('no-store',h['Cache-Control'])
   status,h,raw=self.req('/api/snapshot',cookie=cookie);self.assertEqual(status,200);self.assertNotIn(row['password'],raw.decode());self.assertNotIn(row['password'],self.app.store.dbpath.read_bytes().decode('latin1'))
   self.assertEqual(self.post('/api/operation',{'operation':'team.update','args':{'login':LOGIN,'name':'Expose test','enabled':True,'visible':True},'confirm':'CONFIRM'})[0],409)
  finally:self.app.manager.select(previous)
if __name__=='__main__':unittest.main()
