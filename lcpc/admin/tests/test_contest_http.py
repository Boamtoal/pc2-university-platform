"""Authenticated protocol tests. All data and listeners are isolated fixtures."""
import http.client,json,sys,tempfile,threading,unittest,zipfile,io
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]));sys.path.insert(0,str(Path(__file__).resolve().parent))
from core import password_hash
from server import App,Server
from test_contests import Fake
class ContestHTTP(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.temp=tempfile.TemporaryDirectory();cls.state=Path(cls.temp.name).resolve();cls.app=App(cls.state,0,Fake(cls.state));cls.server=Server(('127.0.0.1',0),cls.app);cls.port=cls.server.server_address[1];cls.origin='http://127.0.0.1:'+str(cls.port);cls.app.origins={cls.origin};cls.password='Fixture-test-password-42'
  with cls.app.store.db() as db:
   for name,role in [('owner','owner'),('operator','operator'),('viewer','viewer')]:db.execute('INSERT INTO users(username,password,role,must_change) VALUES(?,?,?,0)',(name,password_hash(cls.password),role))
  threading.Thread(target=cls.server.serve_forever,daemon=True).start()
 @classmethod
 def tearDownClass(cls):cls.server.shutdown();cls.server.server_close();cls.app.manager.close();cls.temp.cleanup()
 def request(self,path,data=None,token=None,csrf=None):
  h={'Host':self.origin.removeprefix('http://')}
  if data is not None:h.update({'Origin':self.origin,'Content-Type':'application/json'})
  if token:h['Cookie']=token
  if csrf:h['X-CSRF-Token']=csrf
  c=http.client.HTTPConnection('127.0.0.1',self.port,timeout=20);c.request('GET' if data is None else 'POST',path,json.dumps(data) if data is not None else None,h);r=c.getresponse();result=(r.status,dict(r.getheaders()),r.read());c.close();return result
 def login(self,name):
  status,headers,raw=self.request('/api/login',{'username':name,'password':self.password});self.assertEqual(status,200);return headers['Set-Cookie'].split(';')[0],json.loads(raw)['csrf']
 def post(self,path,fields,user='owner',context=None):
  token,csrf=self.login(user);return self.request(path,{'contestId':context or self.app.manager.data['selected'],**fields},token,csrf)
 def test_01_auth_roles_and_csrf(self):
  self.assertEqual(self.request('/api/contests')[0],401)
  for role in ('operator','viewer'):
   for op in ('create','activate','deactivate','archive','export','backup','recovery-key'):
    self.assertEqual(self.post('/api/contests/'+op,{},role)[0],403)
  token,csrf=self.login('owner');self.assertEqual(self.request('/api/contests/export',{'format':'csv','id':self.state.name},token)[0],403)
 def test_02_create_select_stale_mutation_and_second_activation(self):
  data={'title':'Protocol fixture','shortName':'FIX','slug':'protocol-fixture','durationMinutes':90,'penaltyMinutes':20,'workflow':'review','copyProblems':True,'copyResources':False,'confirm':'CONFIRM'}
  status,_,raw=self.post('/api/contests/create',data);self.assertEqual(status,200,raw);cid=json.loads(raw)['id']
  status,_,raw=self.post('/api/contests/activate',{'id':cid,'confirm':'CONFIRM'});self.assertEqual(status,409);self.assertIn(b'Another contest is active',raw);self.assertEqual(self.app.manager.data['active'],self.state.name)
  self.assertEqual(self.post('/api/contests/select',{'id':cid})[0],200)
  status,_,raw=self.post('/api/operation',{'operation':'team.create','args':{'name':'Wrong target','password':'Wrong-target-long-password'},'confirm':'CONFIRM'},context=self.state.name);self.assertEqual(status,409);self.assertIn(b'selected contest changed',raw)
  self.assertEqual(self.post('/api/operation',{'operation':'team.create','args':{'name':'New fixture team','password':'Correct-target-long-password'},'confirm':'CONFIRM'})[0],200)
  token,csrf=self.login('owner');status,_,raw=self.request('/api/snapshot',token=token);snapshot=json.loads(raw);self.assertEqual(len(snapshot['teams']),2);self.assertEqual(len([t for t in snapshot['teams'] if not t.get('testAccount')]),1);self.assertEqual(snapshot['runs'],[]);self.assertNotIn(b'Correct-target-long-password',raw)
  self.assertEqual(self.post('/api/contests/select',{'id':self.state.name})[0],200)
 def test_03_csv_download_pdf_download_and_archive_gate(self):
  status,headers,raw=self.post('/api/contests/export',{'id':self.state.name,'format':'csv'});self.assertEqual(status,200,raw[:200]);self.assertEqual(headers['Content-Type'],'application/zip');self.assertIn('submissions.csv',zipfile.ZipFile(io.BytesIO(raw)).namelist())
  status,headers,raw=self.post('/api/contests/export',{'id':self.state.name,'format':'pdf'});self.assertEqual(status,200,raw[:200]);self.assertTrue(raw.startswith(b'%PDF'))
  status,_,raw=self.post('/api/contests/archive',{'id':self.state.name,'confirm':'CONFIRM'});self.assertEqual(status,409)
 def test_04_no_arbitrary_template_restore_or_download_paths(self):
  self.assertEqual(self.post('/api/contests/download-backup',{'id':self.state.name,'backupId':'../../credentials.properties'})[0],400)
  self.assertEqual(self.post('/api/operation',{'operation':'draft.install','args':{},'confirm':'CONFIRM'})[0],400)
  self.assertEqual(self.post('/api/operation',{'operation':'runtime.shutdown','args':{},'confirm':'CONFIRM'})[0],400)
  self.assertEqual(self.post('/api/contests/recovery-key',{'id':self.state.name,'password':'Wrong-password','confirm':'CONFIRM'})[0],403)
 def test_05_private_problem_difficulty_reaches_dashboard_only(self):
  from problem_difficulty import save
  save(self.app.resources,{'alpha':{'value':1350,'estimated':True}})
  token,_=self.login('owner');status,_,raw=self.request('/api/snapshot',token=token)
  self.assertEqual(status,200);problem=json.loads(raw)['problems'][0]
  self.assertEqual(problem['difficulty'],1350);self.assertTrue(problem['difficultyEstimated'])
  self.assertEqual(self.request('/api/snapshot')[0],401)
  public=self.app.resources.publish_catalog(self.app.bridge.snapshot())
  self.assertNotIn('difficulty',public['problems'][0])
if __name__=='__main__':unittest.main(verbosity=2)
