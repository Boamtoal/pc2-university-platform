"""Isolated participant gateway; no connection to an actual contest."""
import http.client,json,sys,tempfile,threading,unittest
from pathlib import Path
from types import SimpleNamespace
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'infra'))
from infra.login_gateway import Server as Gateway
from infra.result_notifications import payload
from infra.frontend_results import install,BEFORE,AFTER
from infra.branding import install_result_notifications
TOKEN='11111111-1111-4111-8111-111111111111'
OTHER='22222222-2222-4222-8222-222222222222'

class Backend(BaseHTTPRequestHandler):
 def log_message(self,*_):pass
 def do_GET(self):
  token=self.headers.get('team_id','');valid=token in (TOKEN,OTHER);rows=[{'id':'1-1','problem':'Private problem of '+('team1' if token==TOKEN else 'team2'),'language':'C++17','isFinal':True,'isPreliminary':False,'judgement':'Accepted','source':'PRIVATE SOURCE','expectedOutput':'PRIVATE EXPECTED'}]
  if token==TOKEN:rows.extend([{'id':'2-1','problem':'B','isFinal':False,'isPreliminary':True,'judgement':'Wrong Answer'},{'id':'3-1','problem':'C','isFinal':True,'isPreliminary':True,'judgement':'Accepted'}])
  raw=json.dumps(rows if valid else {'error':'denied'}).encode();self.send_response(200 if valid else 401);self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)

class Routes(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.temp=tempfile.TemporaryDirectory();cls.backend=ThreadingHTTPServer(('127.0.0.1',0),Backend);threading.Thread(target=cls.backend.serve_forever,daemon=True).start()
  cls.gateway=Gateway(('127.0.0.1',0),SimpleNamespace(state_tag=cls.temp.name,backend=cls.backend.server_port));threading.Thread(target=cls.gateway.serve_forever,daemon=True).start()
 @classmethod
 def tearDownClass(cls):cls.gateway.shutdown();cls.gateway.server_close();cls.backend.shutdown();cls.backend.server_close();cls.temp.cleanup()
 def get(self,token=None,cookie=False,path='/api/teams/result-notifications'):
  headers={}
  if token:headers['Cookie' if cookie else 'team_id']='lcpc_team_session='+token if cookie else token
  c=http.client.HTTPConnection('127.0.0.1',self.gateway.server_port,timeout=10);c.request('GET',path,headers=headers);r=c.getresponse();out=r.status,dict(r.getheaders()),r.read();c.close();return out
 def test_authentication_header_and_standalone_cookie_access(self):
  self.assertEqual(self.get()[0],401);self.assertEqual(self.get('33333333-3333-4333-8333-333333333333')[0],401)
  for cookie in (False,True):
   status,h,raw=self.get(TOKEN,cookie);self.assertEqual(status,200);self.assertIn('no-store',h['Cache-Control']);self.assertNotIn(TOKEN,raw.decode())
 def test_final_only_allowlist_and_no_private_judge_evidence(self):
  status,h,raw=self.get(TOKEN);data=json.loads(raw);self.assertEqual(data['runs'][0]['verdict'],'Accepted');self.assertTrue(data['runs'][0]['final'])
  for row in data['runs'][1:]:self.assertFalse(row['final']);self.assertEqual(row['verdict'],'')
  self.assertNotIn('PRIVATE',raw.decode());self.assertNotIn('source',raw.decode());self.assertNotIn('expectedOutput',raw.decode())
 def test_no_team_selector_and_session_scopes_are_distinct(self):
  first=json.loads(self.get(TOKEN)[2]);other=json.loads(self.get(OTHER)[2]);self.assertNotEqual(first['scope'],other['scope']);self.assertIn('team1',first['runs'][0]['problem']);self.assertNotIn('team2',str(first))
  self.assertEqual(self.get(TOKEN,path='/api/teams/result-notifications?team=team2')[0],400)

class Deployment(unittest.TestCase):
 def test_hook_is_version_checked_idempotent_and_retains_vendor_fallback(self):
  with tempfile.TemporaryDirectory() as directory:
   path=Path(directory)/'main.js';path.write_text('prefix;'+BEFORE+';suffix');install(directory);first=path.read_text();self.assertIn(AFTER,first);self.assertIn('else this.enableRunsNotifications',first);install(directory);self.assertEqual(path.read_text(),first)
   path.write_text('unknown bundle');
   with self.assertRaises(RuntimeError):install(directory)
   self.assertEqual(path.read_text(),'unknown bundle')
 def test_every_html_surface_receives_the_same_alert_controller_without_content_changes(self):
  with tempfile.TemporaryDirectory() as directory:
   state=Path(directory);web=state/'wti/WebContent/WTI-UI';web.mkdir(parents=True);(web/'main.js').write_text(BEFORE)
   pages=[web/'index.html',web/'standings/index.html',state/'participant-resources/instructions/index.html',state/'participant-resources/problems/index.html']
   for p in pages:p.parent.mkdir(parents=True,exist_ok=True);p.write_text('<html><head></head><body>KEEP CUSTOM CONTENT<script src="main.js?v=old"></script></body></html>')
   install_result_notifications(state,hook=True);install_result_notifications(state,hook=True)
   for p in pages:
    text=p.read_text();self.assertEqual(text.count('result-notifications.js'),1);self.assertEqual(text.count('result-notifications.css'),1);self.assertIn('KEEP CUSTOM CONTENT',text)
   self.assertIn('main.js?v=lcpc-results-1',(web/'index.html').read_text())
 def test_hook_matches_the_bundled_vendor_without_changing_the_original_archive_or_bundle(self):
  import hashlib,shutil
  source=Path(__file__).resolve().parents[3]/'work/wti/WebTeamInterface-1.1/WebContent/WTI-UI/main.js'
  before=hashlib.sha256(source.read_bytes()).hexdigest()
  with tempfile.TemporaryDirectory() as directory:
   target=Path(directory)/'main.js';shutil.copyfile(source,target);install(directory);self.assertEqual(target.read_text().count(AFTER),1);install(directory)
  self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(),before)
 def test_missing_or_string_final_flags_never_release_results(self):
  data=payload('/tmp/fixture',TOKEN,[{'id':'1-1','isFinal':'true','judgement':'Accepted'},{'id':'2-1','judgement':'Wrong Answer'},{'id':'3-1','isFinal':True,'judgement':''}]);self.assertTrue(all(not r['final'] and not r['verdict'] for r in data['runs']))

if __name__=='__main__':unittest.main()
