"""Guide routes contain public documentation only, without exposing private files."""
import http.client,sys,tempfile,threading,unittest
from unittest.mock import patch
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]));sys.path.insert(0,str(Path(__file__).resolve().parent))
from server import App,Server
from test_contests import Fake
class GuideHTTP(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.temp=tempfile.TemporaryDirectory();state=Path(cls.temp.name);cls.app=App(state,0,Fake(state));cls.server=Server(('127.0.0.1',0),cls.app);cls.port=cls.server.server_address[1];cls.app.port=cls.port;cls.app.origins={'http://127.0.0.1:'+str(cls.port)};threading.Thread(target=cls.server.serve_forever,daemon=True).start()
 @classmethod
 def tearDownClass(cls):cls.server.shutdown();cls.server.server_close();cls.app.manager.close();cls.temp.cleanup()
 def get(self,path,method='GET',headers=None):
  conn=http.client.HTTPConnection('127.0.0.1',self.port,timeout=5);conn.request(method,path,headers=headers or {});r=conn.getresponse();out=(r.status,dict(r.getheaders()),r.read());conn.close();return out
 def test_documentation_and_all_credit_logos_have_explicit_static_routes(self):
  for path,mime in [('/guide.js','text/javascript'),('/guide-content.js','text/javascript'),('/guide.css','text/css'),*[(f'/assets/{name}-logo.png','image/png') for name in ('pc2','icpc','omu','lcpc')]]:
   status,headers,body=self.get(path);self.assertEqual(status,200,path);self.assertIn(mime,headers['Content-Type']);self.assertTrue(body);self.assertIn("script-src 'self'",headers['Content-Security-Policy'])
 def test_docs_do_not_open_arbitrary_source_or_private_contest_routes(self):
  for path in ['/docs/guide.json','/assets/credentials.properties','/.local/credentials.properties','/api/snapshot']:
   self.assertIn(self.get(path)[0],(401,404),path)
 def test_static_guide_is_not_a_mutation_endpoint(self):self.assertIn(self.get('/guide.js','POST')[0],(400,401,403,404))
 def test_manuals_require_sign_in_and_serve_only_the_two_fixed_files(self):
  for lang in ('en','ar'):self.assertEqual(self.get('/api/manuals/'+lang)[0],401)
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);manuals=root/'docs/manuals';manuals.mkdir(parents=True)
   for lang in ('en','ar'):(manuals/('University_Contest_Platform_User_Guide_'+lang.upper()+'.pdf')).write_bytes(b'%PDF-1.7\npublic guide fixture')
   with patch('server.ROOT',root),patch.object(self.app.store,'session',return_value={'username':'guide-viewer','role':'viewer','must_change':False}):
    for lang in ('en','ar'):
     status,headers,body=self.get('/api/manuals/'+lang);self.assertEqual(status,200);self.assertEqual(headers['Content-Type'],'application/pdf');self.assertTrue(body.startswith(b'%PDF-'));self.assertIn(lang.upper()+'.pdf',headers['Content-Disposition']);self.assertEqual(int(headers['Content-Length']),len(body))
    self.assertEqual(self.get('/api/manuals/en','HEAD')[2],b'')
    for path in ('/api/manuals/fr','/api/manuals/../../.local/secrets','/docs/manuals/University_Contest_Platform_User_Guide_EN.pdf'):self.assertEqual(self.get(path)[0],404)
    (manuals/'University_Contest_Platform_User_Guide_AR.pdf').unlink();self.assertEqual(self.get('/api/manuals/ar')[0],404)
 def test_temporary_password_must_be_changed_before_manual_access(self):
  with patch.object(self.app.store,'session',return_value={'username':'new-viewer','role':'viewer','must_change':True}):self.assertEqual(self.get('/api/manuals/en')[0],403)
if __name__=='__main__':unittest.main()
