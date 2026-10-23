import base64,concurrent.futures,copy,http.client,json,sys,tempfile,threading,time,unittest
from pathlib import Path
from types import SimpleNamespace
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]));sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'infra'))
from infra.participant_activity import ActivityStore
from infra.login_gateway import Server as Gateway
TOKEN='11111111-1111-4111-8111-111111111111'
class StoreTests(unittest.TestCase):
 def setUp(self):self.temp=tempfile.TemporaryDirectory();self.store=ActivityStore(self.temp.name)
 def tearDown(self):self.temp.cleanup()
 def test_metadata_only_and_verified_identity(self):
  s=self.store;s.bind(TOKEN,'team1');s.telemetry({'client':'a'*32,'reportedTeam':'team2','events':[{'event':'browser.error','details':{'errorType':'TypeError','password':'PRIVATE PASSWORD','source':'PRIVATE SOURCE','token':TOKEN,'message':'PRIVATE MESSAGE','url':'https://private.invalid/?token='+TOKEN}}]},TOKEN,'192.168.10.22')
  row=s.query()['events'][0];self.assertEqual(row['team'],'team1');self.assertEqual(row['source'],'browser');self.assertEqual(row['details']['errorType'],'TypeError');raw=s.path.read_bytes().decode('latin1');self.assertNotIn('PRIVATE',raw);self.assertNotIn(TOKEN,raw);self.assertNotIn('session_hash',str(s.query()))
 def test_unverified_old_sessions_are_not_promoted(self):
  s=self.store;s.telemetry({'client':'a'*32,'reportedTeam':'team9','events':[{'event':'page.open','details':{'page':'runs'}}]},TOKEN,'192.168.10.22');row=s.query()['events'][0];self.assertEqual(row['team'],'');self.assertEqual(row['reported_team'],'team9')
 def test_native_history_and_observed_verdict_changes(self):
  s=self.store;snap={'runs':[{'number':3,'site':1,'team':'team1','verdict':'Pending','final':False}],'teams':[]};s.observe(snap);s.observe(snap);self.assertEqual(len(s.query()['events']),1);self.assertTrue(s.query()['events'][0]['details']['historical']);snap['runs'][0].update(final=True,verdict='Wrong Answer');s.observe(snap);self.assertEqual(s.query()['events'][0]['event'],'submission.updated');self.assertEqual(s.summary()['unresolved'],0)
 def test_signal_gaps_are_inferred_and_recover(self):
  s=self.store;s.bind(TOKEN,'team1');data={'client':'a'*32,'events':[{'event':'heartbeat','details':{'page':'runs'}}]};s.telemetry(data,TOKEN,'192.168.10.22');s.sweep(time.time()+241);self.assertEqual(s.summary()['unresolved'],1);self.assertEqual(s.query()['events'][0]['source'],'observer');s.telemetry(data,TOKEN,'192.168.10.22');self.assertEqual(s.summary()['unresolved'],0);s.unbind(TOKEN);s.sweep(time.time()+200);self.assertEqual(s.summary()['unresolved'],0)
 def test_anonymous_pages_do_not_create_missing_signal_incidents(self):
  s=self.store;s.telemetry({'client':'a'*32,'events':[{'event':'page.open','details':{}}]},'','192.168.10.22');s.sweep(time.time()+200);self.assertEqual(s.summary()['unresolved'],0);self.assertEqual(s.query()['clients'],[])
 def test_chain_concurrency_tamper_and_retention_anchor(self):
  s=self.store
  with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(lambda n:s.record('request.completed',details={'status':200}),range(24)))
  self.assertTrue(s.verify()['valid']);s.MAX_EVENTS=10
  with s.db() as db:s._prune(db,time.time())
  self.assertEqual(s.summary()['events'],10);self.assertTrue(s.verify()['valid']);self.assertTrue(s.verify()['retainedChain'])
  with s.db() as db:db.execute("UPDATE events SET severity='error' WHERE id=(SELECT max(id) FROM events)")
  self.assertFalse(s.verify()['valid'])
 def test_incident_acknowledge_resolve_and_recurrence(self):
  s=self.store;s.record('browser.error',login='team1',source='browser',severity='error',incident=True);iid=s.query()['issues'][0]['id'];s.resolve(iid,'acknowledge','owner');self.assertEqual(s.query()['issues'][0]['state'],'acknowledged');s.resolve(iid,'resolve','owner');self.assertEqual(s.summary()['unresolved'],0);s.record('browser.error',login='team1',source='browser',severity='error',incident=True);self.assertEqual(s.query()['issues'][0]['state'],'open');self.assertEqual(s.query()['issues'][0]['count'],2)
class Backend(BaseHTTPRequestHandler):
 def log_message(self,*_):pass
 def reply(self,status,data):
  raw=json.dumps(data).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
 def do_POST(self):
  data=json.loads(self.rfile.read(int(self.headers['Content-Length'])));self.server.seen.append((self.path,data))
  if self.path=='/api/teams/login':self.reply(200,{'teamId':TOKEN}) if data.get('password')=='fixture-password' else self.reply(401,{'error':'denied'})
  else:self.reply(200,{'ok':True})
 def do_GET(self):self.reply(200,False if self.path.endswith('/options') else []) if self.headers.get('team_id')==TOKEN else self.reply(401,{'error':'denied'})
 def do_DELETE(self):self.reply(200,{'ok':True})
class GatewayTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.temp=tempfile.TemporaryDirectory();cls.state=Path(cls.temp.name);(cls.state/'network').mkdir();cls.backend=ThreadingHTTPServer(('127.0.0.1',0),Backend);cls.backend.seen=[];threading.Thread(target=cls.backend.serve_forever,daemon=True).start();cls.gateway=Gateway(('127.0.0.1',0),SimpleNamespace(state_tag=str(cls.state),backend=cls.backend.server_port));threading.Thread(target=cls.gateway.serve_forever,daemon=True).start();cls.origin='http://127.0.0.1:'+str(cls.gateway.server_port);(cls.state/'network/profile.json').write_text(json.dumps({'origin':cls.origin,'transport':'http'}))
 @classmethod
 def tearDownClass(cls):cls.gateway.shutdown();cls.gateway.server_close();cls.backend.shutdown();cls.backend.server_close();cls.temp.cleanup()
 def req(self,path,data=None,token=None,origin=None,method=None,request_key=None):
  h={'Host':self.origin.split('//')[1],'Content-Type':'application/json','Origin':origin or self.origin,'X-LCPC-Peer':'192.168.10.22'}
  if token:h['team_id']=token
  if request_key:h['Idempotency-Key']=request_key
  c=http.client.HTTPConnection('127.0.0.1',self.gateway.server_port,timeout=10);c.request(method or ('POST' if data is not None else 'GET'),path,None if data is None else json.dumps(data),h);r=c.getresponse();result=r.status,dict(r.getheaders()),r.read();c.close();return result
 def test_01_login_binding_and_no_secret_in_log(self):
  status,h,b=self.req('/api/teams/login',{'teamName':'team1','password':'fixture-password'});self.assertEqual(status,200);self.assertIn('X-LCPC-Request-ID',h);self.assertEqual(self.gateway.activity.identity(TOKEN),'team1');self.assertNotIn('fixture-password',str(self.gateway.activity.query()))
 def test_02_gateway_keeps_submission_policy_and_does_not_log_source(self):
  self.req('/api/teams/login',{'teamName':'team1','password':'fixture-password'});data={'probName':'Fixture problem','language':'GNU C++17 (Isolated Linux ARM64)','mainFile':{'fileName':'main.cpp','byteData':base64.b64encode(b'PRIVATE STUDENT CODE').decode()},'isTest':False}
  self.assertEqual(self.req('/api/teams/run',data,TOKEN)[0],200);self.assertEqual(self.backend.seen[-1][1]['mainFile']['fileName'],'submission.cpp');self.assertNotIn('PRIVATE STUDENT CODE',str(self.gateway.activity.query()));data['isTest']=True;self.assertEqual(self.req('/api/teams/run',data,TOKEN)[0],400)
 def test_03_read_requests_and_backend_denials_are_logged(self):
  status,h,b=self.req('/api/contest/problems');self.assertEqual(status,401);self.assertEqual(self.gateway.activity.query()['events'][0]['details']['status'],401);self.assertEqual(self.req('/api/teams/run',token=TOKEN)[0],200)
 def test_04_client_endpoint_is_origin_checked_and_ignores_identity_claim(self):
  data={'client':'a'*32,'reportedTeam':'team999','events':[{'event':'browser.error','details':{'errorType':'TypeError','message':'DO NOT LOG'}}]};self.assertEqual(self.req('/api/teams/activity',data,TOKEN,origin='http://evil.invalid')[0],403);self.assertEqual(self.req('/api/teams/activity',data,TOKEN)[0],202);self.assertEqual(self.gateway.activity.query()['events'][0]['team'],'team1');self.assertNotIn('DO NOT LOG',str(self.gateway.activity.query()));data['events']=[{'event':'invented','details':{}}];self.assertEqual(self.req('/api/teams/activity',data,TOKEN)[0],400)
 def test_05_logout_removes_diagnostic_binding_and_protects_resources(self):
  self.assertEqual(self.req('/problems/A.pdf')[0],302);self.assertEqual(self.req('/api/teams/logout',token=TOKEN,method='DELETE')[0],200);self.assertEqual(self.gateway.activity.identity(TOKEN),'')
 def test_06_retried_submission_does_not_reach_the_native_backend_twice(self):
  data={'probName':'Receipt fixture','language':'GNU C++17 (Isolated Linux ARM64)','mainFile':{'fileName':'main.cpp','byteData':base64.b64encode(b'int main(){}').decode()},'isTest':False}
  before=len([p for p,b in self.backend.seen if p=='/api/teams/run']);key='e'*32
  self.assertEqual(self.req('/api/teams/run',data,TOKEN,request_key=key)[0],200)
  self.assertEqual(self.req('/api/teams/run',data,TOKEN,request_key=key)[0],200)
  self.assertEqual(len([p for p,b in self.backend.seen if p=='/api/teams/run']),before+1)
 def test_07_temporary_session_check_failure_does_not_claim_expired_login(self):
  from infra.login_gateway import Handler
  data={'probName':'Unavailable fixture','language':'GNU C++17 (Isolated Linux ARM64)','mainFile':{'fileName':'main.cpp','byteData':base64.b64encode(b'int main(){}').decode()},'isTest':False}
  before=len(self.backend.seen)
  with patch.object(Handler,'validate_session',return_value=503):
   status,headers,body=self.req('/api/teams/run',data,TOKEN,request_key='f'*32)
  self.assertEqual(status,503);self.assertIn(b'session has been preserved',body);self.assertEqual(len(self.backend.seen),before)
if __name__=='__main__':unittest.main()
