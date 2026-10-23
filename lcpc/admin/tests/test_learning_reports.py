import base64,copy,hashlib,io,json,sys,tempfile,unittest,zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from core import Store,Error
from test_contests import Fake
from contests import ContestManager
from learning_reports import participants,save_material,material,build_team,package_tree,generate,checked_file,activity,export_ready

class Learning(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.state=Path(self.temp.name);self.store=Store(self.state);self.bridge=Fake(self.state);self.snapshot=self.bridge.snapshot()
  self.snapshot['runs'][0].update(problemId='p1',language='C++',elapsedMinutes=12.5,automaticVerdict='Accepted',workflowState='Accepted')
  self.snapshot['problems'][0].update(difficulty=1350,difficultyEstimated=True)
  self.snapshot['teams'] += [{'login':'team2','name':'Inactive'},{'login':'team3','name':'Activity only'},{'login':'team99999','name':'PRIVATE DIAGNOSTIC','testAccount':True}]
  self.raw=self.state/'native';self.raw.mkdir();self.target=self.state/'team-folder';self.target.mkdir()
  def item(name,body):
   (self.raw/name).write_bytes(body);return {'path':name,'available':True,'sha256':hashlib.sha256(body).hexdigest(),'bytes':len(body)}
  self.native={'problems':[{'id':'p1','validator':'CLICS','tests':[{'number':1,'input':item('input',b'1 2\n'),'expected':item('answer',b'3\n')}]}],
   'runs':[{'number':4,'site':1,'team':'team7','problemId':'p1','sources':[dict(item('source',b'int main(){return 0;}\n'),name='../../submission.cpp')],'reports':[{'verdict':'Accepted','executeExitCode':0,'outputs':{'executionStdout':item('stdout',b'3\n')}}],'history':[],'cases':{'counts':{'total':1,'passed':1,'failed':0,'notValidated':0,'notRecorded':0},'tests':[{'number':1,'status':'Passed','verdict':'Accepted','elapsedMS':1}]}}]}
 def tearDown(self):self.temp.cleanup()
 def test_only_real_participation_qualifies_and_no_unverified_claims(self):
  rows=participants(self.snapshot,{'team3':{'events':{'page.open':1}},'team99999':{'events':{'page.open':2}}})
  self.assertEqual([r['login'] for r in rows],['team7','team3'])
  from infra.participant_activity import ActivityStore
  observed=ActivityStore(self.state);observed.record('page.open',login='team3');observed.record('heartbeat',login='team2');observed.record('page.open',reported='team2')
  self.assertEqual(set(activity(self.state)),{'team3'})
 def test_live_export_requires_finished_and_paused_clock(self):
  manager=SimpleNamespace(data={'active':'current'});row={'id':'current','status':'active'};snapshot=copy.deepcopy(self.snapshot)
  snapshot['contest'].update(running=False,remainingSeconds=0);self.assertTrue(export_ready(manager,row,snapshot))
  snapshot['contest']['running']=True;self.assertFalse(export_ready(manager,row,snapshot))
  snapshot['contest'].update(running=False,remainingSeconds=60);self.assertFalse(export_ready(manager,row,snapshot))
 def test_references_are_scoped_and_never_executed(self):
  values={'problemId':'p1','kind':'solution','filename':'reference.cpp','base64':base64.b64encode(b'int main(){}').decode()}
  save_material(self.store,self.snapshot,values);saved=material(self.store,self.snapshot['problems'][0]);self.assertEqual(saved['solution']['file'].read_bytes(),b'int main(){}')
  for change in ({'filename':'../../secret.cpp'},{'filename':'attack.sh'},{'base64':'invalid'},{'problemId':'another'}):
   with self.assertRaises(Error):save_material(self.store,self.snapshot,{**values,**change})
 def test_team_evidence_preserves_actual_expected_and_unknown_association(self):
  save_material(self.store,self.snapshot,{'problemId':'p1','kind':'solution','filename':'reference.cpp','base64':base64.b64encode(b'int main(){return 1;}').decode()})
  report=build_team(self.store,self.snapshot,self.snapshot['teams'][0],{},self.native,self.raw,self.target,'2026-10-21T12:00:00+00:00')
  self.assertEqual(report['attempts'],1);p=report['problems'][0];self.assertEqual(p['difficulty'],1350)
  self.assertEqual((self.target/p['tests'][0]['expected']['path']).read_bytes(),b'3\n');run=p['attempts'][0]
  self.assertFalse(p['historicRevisionAvailable']);self.assertTrue(run['comparisonAvailable']);self.assertIn('return 0',run['sources'][0]['preview']['text']);self.assertFalse(run['examples'][0]['historicAssociationAvailable'])
  self.assertEqual(run['reports'][0]['outputs']['executionStdout']['preview']['text'],'3\n');self.assertNotIn('password',json.dumps(report));self.assertNotIn('Inactive',json.dumps(report))
  output=self.state/'team.zip';package_tree(self.target,output)
  with zipfile.ZipFile(output) as archive:self.assertTrue(all('..' not in Path(n).parts for n in archive.namelist()))
 def test_cross_team_evidence_or_path_escape_is_rejected(self):
  self.native['runs'][0]['team']='team2'
  with self.assertRaisesRegex(Error,'does not belong'):build_team(self.store,self.snapshot,self.snapshot['teams'][0],{},self.native,self.raw,self.target,'now')
  with self.assertRaises(Error):checked_file(self.raw,'../admin-dashboard/dashboard.sqlite3')
 def test_generation_requires_offline_server_and_cleans_failed_pdf(self):
  app=SimpleNamespace(store=self.store,resources=self.store,bridge=self.bridge);manager=ContestManager(app)
  try:
   with self.assertRaisesRegex(Error,'Finish'):manager.start_job('learning',manager.selected()['id'],'owner')
   manager.data['active']=None;row=manager.selected();row['status']='inactive';self.bridge.data=self.snapshot;manager.job={'status':'running'}
   with patch('contest_runtime.runtime_lock',side_effect=__import__('contextlib').nullcontext),patch('contest_runtime.controller',return_value=SimpleNamespace(pid_for=lambda _:None)),patch('learning_reports.extract_native',return_value=self.native),patch('learning_reports.build_team',side_effect=Error(409,'fixture incomplete')),patch('learning_replay.run',return_value=({},self.raw,0)):
    with self.assertRaisesRegex(Error,'fixture incomplete'):generate(manager,row)
   self.assertEqual(list((self.store.base/'learning-reports').iterdir()),[])
  finally:manager.close()

if __name__=='__main__':unittest.main()
