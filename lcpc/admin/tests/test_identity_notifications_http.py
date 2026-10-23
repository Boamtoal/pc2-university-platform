import copy,http.client,json,sys,tempfile,threading,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]));sys.path.insert(0,str(Path(__file__).resolve().parent))
from core import password_hash
from server import App,Server
from test_contests import Fake
from participant_identity import load,version
class PrivateFeatures(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.temp=tempfile.TemporaryDirectory();cls.app=App(cls.temp.name,0,Fake(Path(cls.temp.name)));cls.http=Server(('127.0.0.1',0),cls.app);cls.origin='http://127.0.0.1:'+str(cls.http.server_port);cls.app.origins={cls.origin};cls.password='Fixture-private-identity-inbox-42'
  with cls.app.store.db() as db:
   for role in ('owner','viewer'):db.execute('INSERT INTO users(username,password,role,must_change) VALUES(?,?,?,0)',(role,password_hash(cls.password),role))
  threading.Thread(target=cls.http.serve_forever,daemon=True).start()
 @classmethod
 def tearDownClass(cls):cls.http.shutdown();cls.http.server_close();cls.app.manager.close();cls.temp.cleanup()
 def request(self,path,data=None,auth=None,csrf=True):
  headers={'Host':self.origin.split('//')[1],'Origin':self.origin,'Content-Type':'application/json'}
  if auth:headers['Cookie']=auth[0]
  if auth and csrf:headers['X-CSRF-Token']=auth[1]
  conn=http.client.HTTPConnection('127.0.0.1',self.http.server_port,timeout=10);conn.request('GET' if data is None else 'POST',path,None if data is None else json.dumps(data),headers);response=conn.getresponse();out=(response.status,dict(response.getheaders()),response.read());conn.close();return out
 def login(self,role='owner'):
  status,h,b=self.request('/api/login',{'username':role,'password':self.password});self.assertEqual(status,200);return h['Set-Cookie'].split(';')[0],json.loads(b)['csrf']
 def url(self):return '/api/participant-identity?contestId='+self.app.manager.data['selected']
 def payload(self):
  value=load(self.app.resources);return {**value,'version':version(value),'contestId':self.app.manager.data['selected'],'logos':[{k:v for k,v in logo.items() if k!='image'} for logo in value['logos']]}
 def test_01_owner_only_and_no_unauthenticated_private_configuration(self):
  for path in (self.url(),'/api/notifications'):
   self.assertEqual(self.request(path)[0],401);self.assertEqual(self.request(path,auth=self.login('viewer'))[0],403)
  status,h,b=self.request(self.url(),auth=self.login());self.assertEqual(status,200);self.assertNotIn(b'base64',b)
  logo=json.loads(b)['logos'][0];status,h,b=self.request(logo['url'],auth=self.login());self.assertEqual(status,200);self.assertEqual(h['Content-Type'],'image/png')
 def test_02_identity_requires_csrf_scoped_workspace_and_optimistic_version(self):
  auth=self.login();data=self.payload();self.assertEqual(self.request('/api/participant-identity',data,auth,csrf=False)[0],403)
  self.assertEqual(self.request('/api/participant-identity',{**data,'contestId':'stale'},auth)[0],409)
  data['name']='Scoped university';self.assertEqual(self.request('/api/participant-identity',data,auth)[0],200)
  self.assertEqual(self.request('/api/participant-identity',data,auth)[0],409);self.assertEqual(self.app.bridge.calls,[])
 def test_03_notification_read_state_requires_owner_and_csrf_and_keeps_history(self):
  self.app.store.audit('fixture','fixture.alert','denied',alert=('warning','Private inbox fixture'));auth=self.login();status,h,b=self.request('/api/notifications',auth=auth);self.assertEqual(status,200);rows=json.loads(b)['notifications'];nid=next(r['id'] for r in rows if r['message']=='Private inbox fixture')
  self.assertEqual(self.request('/api/notifications/read',{'id':nid},auth,csrf=False)[0],403)
  self.assertEqual(self.request('/api/notifications/read',{'id':nid},self.login('viewer'))[0],403)
  self.assertEqual(self.request('/api/notifications/read',{'id':nid},auth)[0],200)
  rows=json.loads(self.request('/api/notifications',auth=auth)[2])['notifications'];row=next(r for r in rows if r['id']==nid);self.assertTrue(row['read_at'])
  with self.app.store.db() as db:self.assertEqual(db.execute('SELECT acknowledged FROM alerts WHERE message=?',('Private inbox fixture',)).fetchone()[0],0)
 def test_04_invalid_filters_and_duplicate_scopes_fail_closed(self):
  auth=self.login();self.assertEqual(self.request(self.url()+'&contestId=another',auth=auth)[0],409)
  for q in ('category=all','after=-1','category=security&category=connection','unknown=1'):self.assertEqual(self.request('/api/notifications?'+q,auth=auth)[0],400)
if __name__=='__main__':unittest.main()
