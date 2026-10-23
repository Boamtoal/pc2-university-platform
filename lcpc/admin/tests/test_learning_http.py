import base64,json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import test_contest_http as helpers
from contests import write_json

class LearningHTTP(unittest.TestCase):
 setUpClass=classmethod(helpers.ContestHTTP.setUpClass.__func__)
 tearDownClass=classmethod(helpers.ContestHTTP.tearDownClass.__func__)
 request=helpers.ContestHTTP.request
 login=helpers.ContestHTTP.login
 post=helpers.ContestHTTP.post
 def url(self):return '/api/learning-reports?contestId='+self.app.manager.data['selected']
 def test_01_private_reports_require_owner_and_current_workspace(self):
  self.assertEqual(self.request(self.url())[0],401)
  for role in ('operator','viewer'):
   cookie,_=self.login(role);self.assertEqual(self.request(self.url(),token=cookie)[0],403)
   for action in ('material','generate','download'):self.assertEqual(self.post('/api/learning-reports/'+action,{},role)[0],403)
  cookie,_=self.login('owner');status,h,b=self.request(self.url(),token=cookie);self.assertEqual(status,200);self.assertEqual(json.loads(b)['eligibleTeams'][0]['login'],'team7');self.assertIn('no-store',h['Cache-Control']);self.assertNotIn(b'password',b)
  self.assertEqual(self.request(self.url()+'&contestId=other',token=cookie)[0],409)
 def test_02_material_upload_is_csrf_protected_bounded_and_linked_to_problem(self):
  payload={'problemId':'p1','kind':'solution','filename':'reference.cpp','base64':base64.b64encode(b'int main(){}').decode()}
  cookie,_=self.login('owner');self.assertEqual(self.request('/api/learning-reports/material',{'contestId':self.state.name,**payload},token=cookie)[0],403)
  self.assertEqual(self.post('/api/learning-reports/material',{**payload,'filename':'../../secret.cpp'})[0],400)
  self.assertEqual(self.post('/api/learning-reports/material',payload)[0],200)
  self.assertEqual(self.post('/api/learning-reports/material',payload,context='other')[0],409)
 def test_03_generation_cannot_read_live_storage(self):
  self.assertEqual(self.post('/api/learning-reports/generate',{})[0],409);self.assertIsNone(self.app.manager.job)
 def test_04_download_checks_export_and_team_membership(self):
  self.assertEqual(self.post('/api/learning-reports/download',{'exportId':'../../secret'})[0],400)
  export_id='a'*32;folder=self.app.resources.base/'learning-reports'/export_id;folder.mkdir(parents=True)
  write_json(folder/'manifest.json',{'complete':True,'contestId':self.state.name,'teams':[{'login':'team7'}]});(folder/'team7.zip').write_bytes(b'fixture-team-seven-only')
  self.assertEqual(self.post('/api/learning-reports/download',{'exportId':export_id,'team':'team2'})[0],404)
  status,headers,body=self.post('/api/learning-reports/download',{'exportId':export_id,'team':'team7'});self.assertEqual(status,200);self.assertEqual(body,b'fixture-team-seven-only');self.assertEqual(headers['Content-Type'],'application/zip')
  self.assertEqual(self.post('/api/learning-reports/download',{'exportId':export_id,'team':['team7']})[0],404)

if __name__=='__main__':unittest.main()
