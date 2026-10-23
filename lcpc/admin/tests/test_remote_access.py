"""Real verified TLS on loopback fixtures; never opens the actual dashboard to a LAN."""
import http.client,json,socket,ssl,sys,tempfile,threading,time,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]));sys.path.insert(0,str(Path(__file__).resolve().parent))
from server import App,Server
from core import Error,password_hash
from test_contests import Fake
import remote_access

class RemoteSecurity(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.temp=tempfile.TemporaryDirectory();state=Path(cls.temp.name).resolve();cls.app=App(state,0,Fake(state));cls.password='Fixture-remote-test-password-42'
  with cls.app.store.db() as db:
   for name,role in [('owner','owner'),('operator','operator'),('viewer','viewer'),('outsider','owner')]:db.execute('INSERT INTO users(username,password,role,must_change) VALUES(?,?,?,0)',(name,password_hash(cls.password),role))
  cls.local=Server(('127.0.0.1',0),cls.app);cls.local_origin='http://127.0.0.1:'+str(cls.local.server_port);cls.app.origins={cls.local_origin}
  context=cls.app.remote.certificates('127.0.0.1');cls.tls=Server(('127.0.0.1',0),cls.app,remote=True,tls_context=context)
  cls.port_patch=patch.object(remote_access,'PORT',cls.tls.server_port);cls.port_patch.start();cls.app.remote.save({'enabled':True,'bind':'127.0.0.1'});cls.remote_origin=cls.app.remote.origin
  cls.ctx=ssl.create_default_context(cafile=str(cls.app.store.base/'remote-access/ca.crt'))
  for server in (cls.local,cls.tls):threading.Thread(target=server.serve_forever,daemon=True).start()
 @classmethod
 def tearDownClass(cls):
  for server in (cls.local,cls.tls):server.shutdown();server.server_close()
  cls.port_patch.stop();cls.app.manager.close();cls.temp.cleanup()
 def setUp(self):
  self.app.remote.save({'enabled':True,'bind':'127.0.0.1'})
  with self.app.store.db() as db:
   db.execute('DELETE FROM remote_grants')
   for name in ('owner','operator','viewer'):db.execute('INSERT INTO remote_grants VALUES(?,?,?,?)',(name,'127.0.0.1','fixture',time.time()+3600))
 def request(self,path,data=None,auth=None,remote=False,origin=None,headers=None):
  base=self.remote_origin if remote else self.local_origin;h={'Host':base.split('//')[1]}
  if data is not None:h.update({'Content-Type':'application/json','Origin':origin or base});data={'contestId':self.app.manager.data['selected'],**data}
  if auth:h['Cookie']=auth[0];h['X-CSRF-Token']=auth[1]
  h.update(headers or {})
  c=http.client.HTTPSConnection('127.0.0.1',self.tls.server_port,context=self.ctx,timeout=10) if remote else http.client.HTTPConnection('127.0.0.1',self.local.server_port,timeout=10)
  try:c.request('POST' if data is not None else 'GET',path,None if data is None else json.dumps(data),h);r=c.getresponse();return r.status,dict(r.getheaders()),r.read()
  finally:c.close()
 def login(self,username='owner',remote=False):
  status,h,b=self.request('/api/login',{'username':username,'password':self.password},remote=remote);self.assertEqual(status,200,b);return h['Set-Cookie'].split(';')[0],json.loads(b)['csrf']
 def test_01_verified_tls_secure_cookie_named_user_and_session_binding(self):
  status,h,b=self.request('/api/login',{'username':'owner','password':self.password},remote=True);self.assertEqual(status,200,b);self.assertIn('__Host-lcpc_admin_remote=',h['Set-Cookie']);self.assertIn('Secure',h['Set-Cookie']);self.assertIn('HttpOnly',h['Set-Cookie']);self.assertTrue(json.loads(b)['remote'])
  auth=h['Set-Cookie'].split(';')[0],json.loads(b)['csrf'];status,h,b=self.request('/api/me',auth=auth,remote=True);self.assertEqual(status,200);self.assertEqual(json.loads(b)['role'],'owner')
  forged=('lcpc_admin='+auth[0].split('=',1)[1],auth[1]);self.assertEqual(self.request('/api/me',auth=forged)[0],401)
  token=auth[0].split('=',1)[1];self.assertIsNone(self.app.store.session(token,'192.168.10.99','remote'));self.assertIsNotNone(self.app.store.session(token,'127.0.0.1','remote'))
 def test_02_approved_ip_cannot_use_a_different_unapproved_account(self):
  self.assertEqual(self.request('/api/login',{'username':'outsider','password':self.password},remote=True)[0],403)
  with self.app.store.db() as db:db.execute("UPDATE remote_grants SET ip='192.168.10.50' WHERE username='owner'")
  self.assertEqual(self.request('/api/login',{'username':'owner','password':self.password},remote=True)[0],403)
 def test_03_remote_owner_cannot_approve_ips_or_download_trust_material(self):
  auth=self.login(remote=True)
  for path in ['/api/remote-access','/api/remote-access/ca']:self.assertEqual(self.request(path,auth=auth,remote=True)[0],403)
  self.assertEqual(self.request('/api/remote-access/approve',{'username':'owner','ip':'192.168.10.77','hours':8,'password':self.password,'confirm':'CONFIRM'},auth,True)[0],403)
 def test_04_csrf_origin_host_and_roles_remain_enforced_over_https(self):
  auth=self.login('viewer',True)
  self.assertEqual(self.request('/api/operation',{'operation':'clock.start','args':{},'confirm':'CONFIRM'},auth,True)[0],403)
  auth=self.login(remote=True)
  self.assertEqual(self.request('/api/logout',{},(auth[0],''),True)[0],403)
  self.assertEqual(self.request('/api/logout',{},auth,True,origin='http://evil.invalid')[0],403)
  self.assertEqual(self.request('/api/me',auth=auth,remote=True,headers={'Host':'evil.invalid'})[0],403)
 def test_05_expiry_and_disabling_access_apply_to_existing_sessions(self):
  auth=self.login(remote=True)
  with self.app.store.db() as db:db.execute('UPDATE remote_grants SET expires=? WHERE username=?',(time.time()-1,'owner'))
  self.assertEqual(self.request('/api/me',auth=auth,remote=True)[0],403)
  self.app.remote.save({'enabled':False,'bind':'127.0.0.1'})
  with self.assertRaises((OSError,ssl.SSLError,http.client.HTTPException)):self.request('/api/me',auth=auth,remote=True)
  self.assertEqual(self.request('/api/me',auth=self.login())[0],200)
 def test_06_local_approval_requires_reauthentication_and_revocation_ends_sessions(self):
  auth=self.login();data={'username':'operator','ip':'192.168.10.25','hours':8,'confirm':'CONFIRM'}
  self.assertEqual(self.request('/api/remote-access/approve',data,auth)[0],403)
  self.assertEqual(self.request('/api/remote-access/approve',{**data,'password':self.password},auth)[0],200)
  token,_,_=self.app.store.login('operator',self.password,'','192.168.10.25','remote');self.assertTrue(self.app.remote.permitted('192.168.10.25','operator'))
  self.assertEqual(self.request('/api/remote-access/revoke',{**data,'password':self.password},auth)[0],200)
  self.assertFalse(self.app.remote.permitted('192.168.10.25','operator'));self.assertIsNone(self.app.store.session(token))
 def test_07_rebinding_public_ips_subnets_and_unassigned_server_addresses_are_rejected(self):
  for value in ('0.0.0.0','127.0.0.1','8.8.8.8','192.168.10.0/24','::1','localhost','192.168.10.1:8092'):
   with self.assertRaises(Error):remote_access.private_ip(value)
  self.assertEqual(remote_access.private_ip('192.168.10.25'),'192.168.10.25')
  with patch('remote_access.local_addresses',return_value=[]):
   with self.assertRaises(Error):self.app.remote.configure(True,'192.168.10.3')
 def test_08_forwarded_headers_cannot_bypass_the_actual_peer_ip_gate(self):
  with self.app.store.db() as db:db.execute("UPDATE remote_grants SET ip='192.168.10.25'")
  with self.assertRaises((OSError,ssl.SSLError,http.client.HTTPException)):self.request('/',remote=True,headers={'X-Forwarded-For':'192.168.10.25','X-LCPC-Peer':'192.168.10.25'})
  with self.app.store.db() as db:self.assertTrue(db.execute("SELECT 1 FROM remote_attempts WHERE ip='127.0.0.1'").fetchone())
 def test_09_listener_enable_disable_preserves_local_access_and_ends_remote_sessions(self):
  auth=self.login();remote_auth=self.login(remote=True)
  with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
  with patch.object(remote_access,'PORT',port),patch('remote_access.private_ip',return_value='127.0.0.1'),patch('remote_access.local_addresses',return_value=[{'ip':'127.0.0.1','interface':'fixture'}]):
   self.app.remote.configure(True,'127.0.0.1')
   try:
    c=http.client.HTTPSConnection('127.0.0.1',port,context=self.ctx,timeout=10);c.request('GET','/api/me',headers={'Cookie':remote_auth[0]});r=c.getresponse();self.assertEqual(r.status,200);r.read();c.close()
   finally:self.app.remote.configure(False,'')
   self.assertIsNone(self.app.remote.server)
  self.assertIsNone(self.app.store.session(remote_auth[0].split('=',1)[1]));self.assertEqual(self.request('/api/me',auth=auth)[0],200)

if __name__=='__main__':unittest.main()
