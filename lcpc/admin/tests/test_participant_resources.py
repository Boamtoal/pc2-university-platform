"""Isolated gateway checks. Never connects to the real contest."""
import base64,http.client,json,os,socket,subprocess,sys,tempfile,threading,time,unittest
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core import Store
TOKEN='00000000-0000-0000-0000-000000000001'
class Backend(BaseHTTPRequestHandler):
 def log_message(self,*_):pass
 def do_GET(self):
  self.send_response(200 if self.headers.get('team_id')==TOKEN else 401);self.end_headers()
class ParticipantResources(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.temp=tempfile.TemporaryDirectory();cls.state=Path(cls.temp.name);cls.store=Store(cls.state)
  for route in ('instructions','problems'):
   folder=cls.state/'participant-resources'/route;folder.mkdir(parents=True);(folder/'index.html').write_text('<h1>'+route+'</h1>')
  # A stale static PDF must never bypass the published resource catalog.
  (cls.state/'participant-resources/problems/A.pdf').write_bytes(b'stale private PDF')
  cls.rid=cls.store.upload({'problem':'p','kind':'statement','language':'en','label':'English','filename':'A.pdf','base64':base64.b64encode(b'%PDF-1.7\n%%EOF').decode()})
  cls.snapshot={'problems':[{'id':'p','letter':'A','active':True}]};cls.store.publish_catalog(cls.snapshot)
  cls.backend=ThreadingHTTPServer(('127.0.0.1',0),Backend);threading.Thread(target=cls.backend.serve_forever,daemon=True).start()
  with socket.socket() as sock:sock.bind(('127.0.0.1',0));cls.port=sock.getsockname()[1]
  script=Path(__file__).resolve().parents[2]/'infra/login_gateway.py'
  cls.process=subprocess.Popen([sys.executable,'-B',str(script),'--port',str(cls.port),'--backend',str(cls.backend.server_port),'--state-tag',str(cls.state)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  for _ in range(50):
   try:
    with socket.create_connection(('127.0.0.1',cls.port),timeout=.1):break
   except OSError:time.sleep(.05)
  else:raise RuntimeError('Fixture gateway did not start')
 @classmethod
 def tearDownClass(cls):cls.process.terminate();cls.process.wait(timeout=5);cls.backend.shutdown();cls.backend.server_close();cls.temp.cleanup()
 def get(self,path,authenticated=False):
  conn=http.client.HTTPConnection('127.0.0.1',self.port,timeout=5);conn.request('GET',path,headers={'Cookie':'lcpc_team_session='+TOKEN} if authenticated else {});r=conn.getresponse();result=(r.status,dict(r.getheaders()),r.read());conn.close();return result
 def test_public_instructions_and_private_problems(self):
  self.assertEqual(self.get('/instructions/')[0],200)
  self.assertEqual(self.get('/api/teams/resources')[0],401)
  for path in ('/problems/','/problems/A.pdf','/problems/files/'+self.rid):self.assertEqual(self.get(path)[0],302)
 def test_catalog_and_publication(self):
  self.assertEqual(self.get('/problems/A.pdf',True)[0],404)
  with self.store.db() as db:db.execute('UPDATE resources SET published=1 WHERE id=?',(self.rid,))
  self.store.publish_catalog(self.snapshot)
  self.assertEqual(self.get('/problems/A.pdf',True)[0],200)
  self.assertEqual(self.get('/problems/files/'+self.rid,True)[0],200)
  self.assertEqual(len(json.loads(self.get('/api/teams/resources',True)[2])['problems'][0]['resources']),1)
  with self.store.db() as db:db.execute('UPDATE resources SET published=0 WHERE id=?',(self.rid,))
  self.store.publish_catalog(self.snapshot)
 def test_no_path_or_legacy_bypass(self):
  for path in ('/instructions/../problems/A.pdf','/instructions/%2e%2e/probleMs/A.pdf','/problems/../admin-dashboard/dashboard.sqlite3','/problems/catalog.json','/instructions/../catalog.json'):
   self.assertEqual(self.get(path,True)[0],404)
if __name__=='__main__':unittest.main(verbosity=2)
