import base64,http.client,json,sys,tempfile,threading,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]));sys.path.insert(0,str(Path(__file__).resolve().parent))
from core import password_hash,Error
from server import App,Server
from test_contests import Fake
class ReviewFake(Fake):
 def __init__(self,state):
  super().__init__(state);self.data['runs'][0].update(problemId='p1',language='C++',elapsedMinutes=1)
 def call(self,op,args=None):
  self.calls.append((op,args))
  if op=='diagnostics':return {'verdict':'Wrong Answer','final':True,'counts':{'total':1,'failed':1},'tests':[{'number':1,'status':'Failed','verdict':'Wrong Answer'}],'reports':[{'verdict':'Wrong Answer','executeExitCode':139}]}
  if op=='source':return {'files':[{'name':'fixture.cpp','base64':base64.b64encode(b'fixture source').decode()}]}
  if op=='test-data':return {'number':args['test'],'input':{'available':False},'expected':{'available':False}}
  raise Error(400,'Unexpected fixture operation')
class ReviewRoutes(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.temp=tempfile.TemporaryDirectory();cls.fake=ReviewFake(Path(cls.temp.name));cls.app=App(cls.temp.name,0,cls.fake);cls.server=Server(('127.0.0.1',0),cls.app);cls.origin='http://127.0.0.1:'+str(cls.server.server_port);cls.app.origins={cls.origin};cls.password='Fixture-review-password-42'
  with cls.app.store.db() as db:db.execute('INSERT INTO users(username,password,role,must_change) VALUES(?,?,?,0)',('owner',password_hash(cls.password),'owner'))
  threading.Thread(target=cls.server.serve_forever,daemon=True).start()
 @classmethod
 def tearDownClass(cls):cls.server.shutdown();cls.server.server_close();cls.app.manager.close();cls.temp.cleanup()
 def request(self,path,data=None,cookie=None):
  headers={'Host':self.origin.split('//')[1],'Origin':self.origin,'Content-Type':'application/json'}
  if cookie:headers['Cookie']=cookie
  c=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=10);c.request('GET' if data is None else 'POST',path,None if data is None else json.dumps(data),headers);r=c.getresponse();result=(r.status,dict(r.getheaders()),r.read());c.close();return result
 def login(self):return self.request('/api/login',{'username':'owner','password':self.password})[1]['Set-Cookie'].split(';')[0]
 def url(self,path='submission-review',extra=''):
  return '/api/'+path+'?contestId='+self.app.manager.data['selected']+('&problemId=p1' if path=='problem-review' else '&site=1&number=4')+extra
 def test_01_shell_has_no_private_data_and_api_requires_authentication(self):
  for path in ['/review.html','/review.js','/review.css']:
   status,h,b=self.request(path);self.assertEqual(status,200);self.assertNotIn(b'fixture source',b);self.assertIn('no-store',h['Cache-Control']);self.assertIn("frame-ancestors 'none'",h['Content-Security-Policy'])
  self.assertEqual(self.request(self.url())[0],401)
 def test_02_review_preserves_official_verdict_and_reports_separate_execution_evidence(self):
  before=json.dumps(self.fake.data,sort_keys=True);status,h,b=self.request(self.url(),cookie=self.login());self.assertEqual(status,200);value=json.loads(b);self.assertEqual(value['evidence']['verdict'],'Wrong Answer');self.assertEqual(value['evidence']['reports'][0]['executeExitCode'],139);self.assertEqual(value['submission']['number'],4);self.assertEqual(value['problem']['id'],'p1');self.assertEqual(json.dumps(self.fake.data,sort_keys=True),before);self.assertNotIn('files',value)
  self.assertTrue(all(op in ('diagnostics',) for op,args in self.fake.calls))
 def test_03_stale_workspace_invalid_records_and_duplicate_ids_are_rejected_before_private_reads(self):
  cookie=self.login();before=len(self.fake.calls)
  for url,status in [(self.url().replace('contestId=','contestId=wrong-'),409),(self.url()+'&contestId=other',409),(self.url()+'&number=5',400),(self.url().replace('number=4','number=999'),404),(self.url().replace('number=4','number=-1'),400)]:self.assertEqual(self.request(url,cookie=cookie)[0],status)
  self.assertEqual(len(self.fake.calls),before)
 def test_04_source_and_reference_reads_reject_an_old_review_workspace(self):
  cookie=self.login();before=len(self.fake.calls)
  for op in ['source','diagnostics','test-data']:self.assertEqual(self.request('/api/'+op+'?contestId=stale&site=1&number=4&test=1',cookie=cookie)[0],409)
  self.assertEqual(len(self.fake.calls),before)
 def test_05_problem_review_reads_metadata_without_executing_or_loading_test_files(self):
  before=len(self.fake.calls);status,h,b=self.request(self.url('problem-review'),cookie=self.login());self.assertEqual(status,200);self.assertEqual(json.loads(b)['problem']['name'],'Alpha');self.assertEqual(len(self.fake.calls),before);self.assertNotIn(b'fixture source',b)
 def test_06_busy_contest_does_not_read_another_judging_context(self):
  self.app.manager.job={'status':'running'}
  try:self.assertEqual(self.request(self.url(),cookie=self.login())[0],409)
  finally:self.app.manager.job=None
if __name__=='__main__':unittest.main()
