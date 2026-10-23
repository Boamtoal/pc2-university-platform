import base64,hashlib,http.client,io,json,sys,tempfile,threading,time,unittest,zipfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'infra'))
from core import Store,Error,password_hash,totp,prepare_judge_data
from server import App,Server,validate_operation
from participant_resources import file_response

class FakeBridge:
 process=None
 def __init__(self):self.calls=[]
 def snapshot(self,fresh=False):return {'contest':{},'problems':[{'id':'problem-a','letter':'A','name':'Alpha','active':True}],'runs':[],'teams':[]}
 def call(self,op,args=None):self.calls.append((op,args));return {'ok':True}
 def close(self):pass

class DashboardSecurity(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.temp=tempfile.TemporaryDirectory();cls.fake=FakeBridge();cls.app=App(cls.temp.name,0,cls.fake);cls.server=Server(('127.0.0.1',0),cls.app);cls.port=cls.server.server_address[1];cls.app.origins={'http://127.0.0.1:'+str(cls.port)}
  cls.password='Long test-only password 42!'
  with cls.app.store.db() as db:
   for user,role in [('owner','owner'),('reader','viewer'),('operator','operator')]:db.execute('INSERT INTO users(username,password,role,must_change) VALUES(?,?,?,0)',(user,password_hash(cls.password),role))
  cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
 @classmethod
 def tearDownClass(cls):cls.server.shutdown();cls.server.server_close();cls.temp.cleanup()
 def request(self,path,body=None,cookie=None,csrf=None,origin=None,host=None):
  headers={'Host':host or '127.0.0.1:'+str(self.port)}
  if body is not None:body={'contestId':self.app.manager.data['selected'],**body}
  if body is not None:headers.update({'Origin':origin or next(iter(self.app.origins)),'Content-Type':'application/json'})
  if cookie:headers['Cookie']=cookie
  if csrf:headers['X-CSRF-Token']=csrf
  connection=http.client.HTTPConnection('127.0.0.1',self.port,timeout=10);connection.request('POST' if body is not None else 'GET',path,body=json.dumps(body) if body is not None else None,headers=headers);response=connection.getresponse();raw=response.read();result=(response.status,dict(response.getheaders()),raw);connection.close();return result
 def login(self,user='owner'):
  status,headers,raw=self.request('/api/login',{'username':user,'password':self.password});self.assertEqual(status,200);return headers['Set-Cookie'].split(';')[0],json.loads(raw)['csrf']
 def test_01_unauthenticated_sensitive_endpoints(self):
  self.assertEqual(self.request('/workspace-nav.js')[0],200)
  for path in ['/api/snapshot','/api/timezones','/api/security','/api/diagnostics?number=1','/api/test-data?number=1&test=1','/api/source?number=1','/api/resources/'+'0'*32+'/download']:
   self.assertEqual(self.request(path)[0],401)
 def test_02_rebinding_and_cross_origin(self):
  self.assertEqual(self.request('/',host='attacker.test:'+str(self.port))[0],403)
  self.assertEqual(self.request('/api/login',{'username':'owner','password':self.password},origin='https://attacker.test')[0],403)
 def test_03_cookie_and_csrf(self):
  cookie,csrf=self.login();status,headers,raw=self.request('/')
  self.assertIn("frame-ancestors 'none'",headers['Content-Security-Policy']);self.assertEqual(headers['X-Frame-Options'],'DENY')
  self.assertEqual(self.request('/api/logout',{},cookie=cookie)[0],403)
  self.assertEqual(self.request('/api/logout',{},cookie=cookie,csrf=csrf)[0],200)
  self.assertEqual(self.request('/api/snapshot',cookie=cookie)[0],401)
 def test_04_role_boundaries(self):
  cookie,csrf=self.login('reader')
  self.assertEqual(self.request('/api/security',cookie=cookie)[0],403)
  self.assertEqual(self.request('/api/operation',{'operation':'clock.start','args':{},'confirm':'CONFIRM'},cookie,csrf)[0],403)
  self.assertNotIn(('clock.start',{}),self.fake.calls)
 def test_05_explicit_confirmation_and_operation_allowlist(self):
  cookie,csrf=self.login()
  self.assertEqual(self.request('/api/operation',{'operation':'clock.start','args':{}},cookie,csrf)[0],400)
  self.assertEqual(self.request('/api/operation',{'operation':'arbitrary.shell','args':{},'confirm':'CONFIRM'},cookie,csrf)[0],400)
 def test_06_resource_publication_and_unpublication(self):
  cookie,csrf=self.login();pdf=b'%PDF-1.7\n1 0 obj\n<<>>\nendobj\n%%EOF'
  payload={'problem':'problem-a','kind':'statement','language':'ar','label':'Arabic statement','filename':'arabic.pdf','base64':base64.b64encode(pdf).decode()}
  status,_,raw=self.request('/api/resources/upload',payload,cookie,csrf);self.assertEqual(status,200);rid=json.loads(raw)['id']
  self.app.store.publish_catalog(self.fake.snapshot());self.assertEqual(file_response(self.temp.name,'/problems/files/'+rid)[0],404)
  self.assertEqual(self.request('/api/resources/publish',{'id':rid,'published':True,'confirm':'CONFIRM'},cookie,csrf)[0],200)
  self.assertEqual(file_response(self.temp.name,'/problems/files/'+rid)[1],pdf)
  self.assertEqual(self.request('/api/resources/publish',{'id':rid,'published':False,'confirm':'CONFIRM'},cookie,csrf)[0],200)
  self.assertEqual(file_response(self.temp.name,'/problems/files/'+rid)[0],404)
 def test_07_upload_rejections(self):
  store=self.app.store;payload={'problem':'problem-a','kind':'statement','language':'en','label':'Test','filename':'../evil.pdf','base64':base64.b64encode(b'%PDF-1.7\n%%EOF').decode()}
  with self.assertRaises(Error):store.upload(payload)
  payload['filename']='evil.pdf';payload['base64']=base64.b64encode(b'%PDF-1.7 /JavaScript (secret)\n%%EOF').decode()
  with self.assertRaises(Error):store.upload(payload)
  data=io.BytesIO()
  with zipfile.ZipFile(data,'w') as z:z.writestr('../escape.txt','bad')
  payload.update(kind='helper',filename='sample.zip',base64=base64.b64encode(data.getvalue()).decode())
  with self.assertRaises(Error):store.upload(payload)
 def test_08_session_expiration_and_hashing(self):
  token,_,_=self.app.store.login('reader',self.password,'','test-only-ip')
  with self.app.store.db() as db:
   self.assertIsNone(db.execute('SELECT 1 FROM sessions WHERE token=?',(token,)).fetchone());db.execute('UPDATE sessions SET seen=0 WHERE token=?',(hashlib.sha256(token.encode()).hexdigest(),))
  self.assertIsNone(self.app.store.session(token))
 def test_09_audit_integrity_and_secret_redaction(self):
  self.assertTrue(self.app.store.verify_audit()['valid']);log=(self.app.store.base/'audit.jsonl').read_text();self.assertNotIn(self.password,log);self.assertNotIn('secret)',log)
  with tempfile.TemporaryDirectory() as folder:
   store=Store(folder);store.audit('test','action','success')
   with store.db() as db:db.execute("UPDATE audit SET outcome='tampered'")
   self.assertFalse(store.verify_audit()['valid'])
 def test_10_totp_standard_vector(self):self.assertEqual(totp('GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ',59),'287082')
 def test_11_must_change_password_gate(self):
  with self.app.store.db() as db:db.execute("UPDATE users SET must_change=1 WHERE username='reader'")
  cookie,csrf=self.login('reader');self.assertEqual(self.request('/api/snapshot',cookie=cookie)[0],403);self.assertEqual(self.request('/api/me',cookie=cookie)[0],200)
  with self.app.store.db() as db:db.execute("UPDATE users SET must_change=0 WHERE username='reader'")
 def test_12_totp_requires_password_and_expires(self):
  cookie,csrf=self.login()
  self.assertEqual(self.request('/api/totp/setup',{},cookie,csrf)[0],403)
  status,headers,raw=self.request('/api/totp/setup',{'password':self.password},cookie,csrf);self.assertEqual(status,200);setup=json.loads(raw);secret=setup['secret']
  self.assertIn('no-store',headers['Cache-Control']);self.assertIn('<svg ',setup['qrSvg']);self.assertIn('Authenticator setup QR code',setup['qrSvg']);self.assertNotIn(secret,setup['qrSvg'])
  with self.app.store.db() as db:db.execute("UPDATE users SET pending_totp_created=0 WHERE username='owner'")
  self.assertEqual(self.request('/api/totp/enable',{'code':totp(secret)},cookie,csrf)[0],403)
  with self.app.store.db() as db:db.execute("UPDATE users SET pending_totp='',pending_totp_created=0 WHERE username='owner'")
 def test_13_typed_settings_limits(self):
  for args in ({'seconds':True},{'seconds':-1},{'seconds':999999},{'seconds':60,'shell':'bad'}):
   with self.assertRaises(Error):validate_operation('clock.extend',args)
  with self.assertRaises(Error):validate_operation('problem.update',{'id':'p','name':'P','timeLimit':11,'memoryLimit':256,'active':True})
  valid={'id':'p','name':'P','timeLimit':2,'memoryLimit':256,'active':True,'colorName':'Red','colorRGB':'#ff0000'}
  validate_operation('problem.update',valid)
  for change in ({'colorRGB':'red;display:none'},{'colorName':''},{'colorRGB':True}):
   with self.assertRaises(Error):validate_operation('problem.update',{**valid,**change})
  validate_operation('clock.extend',{'seconds':300})
 def test_14_private_judge_archive(self):
  def encoded(files):
   raw=io.BytesIO()
   with zipfile.ZipFile(raw,'w') as archive:
    for name,content in files.items():archive.writestr(name,content)
   return base64.b64encode(raw.getvalue()).decode()
  for files in ({'a.in':'1'},{'../a.in':'1','../a.ans':'2'},{'a.in':'1','a.exe':'bad'}):
   with self.assertRaises(Error):prepare_judge_data(self.app.store,encoded(files))
  directory=prepare_judge_data(self.app.store,encoded({'tests/a.in':'1','tests/a.ans':'2'}))
  self.assertEqual((directory/'0001.in').read_text(),'1');self.assertEqual((directory/'0001.ans').read_text(),'2')
  self.assertTrue(directory.is_relative_to(self.app.store.base/'judge-data'))
 def test_15_recoverable_resource_removal(self):
  cookie,csrf=self.login();rid=self.app.store.upload({'problem':'problem-a','kind':'helper','language':'none','label':'Sample','filename':'sample.txt','base64':base64.b64encode(b'sample').decode()})
  self.assertEqual(self.request('/api/resources/delete',{'id':rid,'confirm':'CONFIRM'},cookie,csrf)[0],200)
  self.assertIn(rid,[r['id'] for r in self.app.store.resources(deleted=True)])
  self.assertEqual(self.request('/api/resources/restore',{'id':rid,'confirm':'CONFIRM'},cookie,csrf)[0],200)
  row=next(r for r in self.app.store.resources() if r['id']==rid);self.assertEqual(row['published'],0)
  self.assertTrue((self.app.store.uploads/rid).exists())
 def test_16_private_diagnostics_and_bounded_queries(self):
  cookie,csrf=self.login('reader')
  self.assertEqual(self.request('/api/diagnostics?number=1&site=1',cookie=cookie)[0],200)
  self.assertIn(('diagnostics',{'number':1,'site':1}),self.fake.calls)
  self.assertEqual(self.request('/api/test-data?number=1&site=1&test=1',cookie=cookie)[0],200)
  for query in ('number=-1&test=1','number=1&test=0','number=1&test=10001','number=1&test=../../secret','number=bad&test=1'):
   self.assertEqual(self.request('/api/test-data?'+query,cookie=cookie)[0],400)
 def test_17_judging_workflow_owner_only(self):
  for username in ('reader','operator'):
   cookie,csrf=self.login(username)
   for operation,args in [('judging.workflow',{'mode':'review'}),('run.approve',{'number':1,'site':1,'reason':'Reviewed source','expectedJudgement':'Yes'})]:
    self.assertEqual(self.request('/api/operation',{'operation':operation,'args':args,'confirm':'CONFIRM'},cookie,csrf)[0],403)
  with self.assertRaises(Error):validate_operation('judging.workflow',{'mode':'unsafe'})
  validate_operation('judging.workflow',{'mode':'review'})
 def test_18_calendar_preview_and_normalized_schedule(self):
  cookie,csrf=self.login()
  self.assertEqual(self.request('/api/timezones',cookie=cookie)[0],200)
  payload={'local':'2026-03-08T02:30','country':'US','timeZone':'America/New_York'}
  self.assertEqual(self.request('/api/schedule/preview',payload,cookie=cookie)[0],403)
  status,_,raw=self.request('/api/schedule/preview',payload,cookie,csrf);self.assertEqual(status,200);self.assertFalse(json.loads(raw)['valid'])
  args={'title':'Fixture','shortName':'Fixture','freezeRemaining':'00:45:00','thawed':False,'scheduledLocal':'2026-10-20T14:30','scheduleCountry':'NP','scheduleTimeZone':'Asia/Kathmandu'}
  self.assertEqual(self.request('/api/operation',{'operation':'contest.update','args':args,'confirm':'CONFIRM'},cookie,csrf)[0],200)
  actual=self.fake.calls[-1][1];self.assertEqual(actual['scheduledStart'],'2026-10-20T08:45:00Z');self.assertNotIn('scheduledLocal',actual);self.assertNotIn('scheduleCountry',actual)
  self.assertEqual(self.app.store.schedule_preferences()['timeZone'],'Asia/Kathmandu')
  self.app.store.save_schedule_preferences({'country':'LY','timeZone':'Africa/Tripoli'})
if __name__=='__main__':unittest.main(verbosity=2)
