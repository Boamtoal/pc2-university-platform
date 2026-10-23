import copy,io,json,sys,tempfile,unittest,zipfile
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from contests import DraftBridge,write_json,read_json
from core import Error
from test_team import LOGIN,NUMBER,credentials,ensure_draft,official
from contest_exports import csv_report

class DiagnosticAccount(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.state=Path(self.temp.name)
  self.path=self.state/'admin-dashboard/draft.json'
  write_json(self.path,{'contest':{'lengthSeconds':7200},'penaltyMinutes':20,'workflow':'review','teams':[{'number':1,'login':'team1','name':'Official','password':'unchanged-official-password','visible':True,'enabled':True}],'problems':[],'languages':[]})
 def tearDown(self):self.temp.cleanup()
 def test_migration_is_idempotent_keeps_official_credentials_and_snapshot_has_no_passwords(self):
  before=copy.deepcopy(read_json(self.path)['teams'][0]);bridge=DraftBridge(self.state);first=read_json(self.path);again=DraftBridge(self.state)
  self.assertEqual(read_json(self.path),first);self.assertEqual(first['teams'][0],before)
  account=first['teams'][-1];self.assertEqual(account['login'],LOGIN);self.assertFalse(account['visible']);self.assertGreaterEqual(len(account['password']),32)
  snap=again.snapshot();self.assertNotIn(account['password'],json.dumps(snap));self.assertNotIn('password',snap['teams'][-1]);self.assertTrue(snap['teams'][-1]['testAccount'])
 def test_new_official_team_numbering_and_reserved_visibility_protection(self):
  bridge=DraftBridge(self.state);bridge.call('team.create',{'name':'Second','password':'long-fixture-password-2'})
  self.assertEqual([r['number'] for r in official(bridge.snapshot()['teams'])],[1,2])
  with self.assertRaises(Error):bridge.call('team.update',{'login':LOGIN,'name':'Visible','enabled':True,'visible':True})
  self.assertFalse(next(t for t in bridge.snapshot()['teams'] if t['login']==LOGIN)['visible'])
 def test_contests_have_independent_passwords_and_credential_access_needs_selected_managed_account(self):
  first=DraftBridge(self.state);other=self.state/'other';write_json(other/'admin-dashboard/draft.json',read_json(self.path));draft=read_json(other/'admin-dashboard/draft.json');draft['teams']=official(draft['teams']);write_json(other/'admin-dashboard/draft.json',draft);DraftBridge(other)
  self.assertNotEqual(read_json(self.path)['teams'][-1]['password'],read_json(other/'admin-dashboard/draft.json')['teams'][-1]['password'])
  manager=SimpleNamespace(data={'selected':'current','active':None},selected=lambda:{'id':'current','state':str(self.state),'status':'draft'})
  result=credentials(SimpleNamespace(manager=manager,bridge=first));self.assertEqual(result['login'],LOGIN)
 def test_changed_live_password_is_retrieved_from_native_and_retained_privately_offline(self):
  bridge=DraftBridge(self.state);manager=SimpleNamespace(data={'selected':'current','active':'current'},selected=lambda:{'state':str(self.state),'status':'active'})
  live={'login':LOGIN,'password':'changed-live-test-password','name':'Organizer Test Team'}
  native=SimpleNamespace(snapshot=lambda:bridge.snapshot(),call=lambda op:live)
  app=SimpleNamespace(manager=manager,bridge=native);self.assertEqual(credentials(app)['password'],live['password'])
  cache=self.state/'admin-dashboard/test-team-access.json';self.assertEqual(cache.stat().st_mode&0o777,0o600)
  manager.data['active']=None;(self.state/'secured').touch();self.assertEqual(credentials(app)['password'],live['password'])
 def test_collision_never_overwrites_an_existing_participant(self):
  data=read_json(self.path);data['teams'].append({'login':LOGIN,'number':NUMBER,'name':'Existing','password':'must-stay-private'});write_json(self.path,data)
  with self.assertRaisesRegex(Error,'already in use'):ensure_draft(self.path)
  self.assertEqual(read_json(self.path),data)
 def test_csv_separates_test_attempts_and_roster(self):
  bridge=DraftBridge(self.state);snap=bridge.snapshot();snap['runs']=[{'team':'team1','number':1},{'team':LOGIN,'number':2}]
  data={'snapshot':snap,'exportedAt':'now','contestId':'current','resources':[],'audit':[],'notes':[]}
  with zipfile.ZipFile(io.BytesIO(csv_report(data))) as archive:
   self.assertNotIn(LOGIN,archive.read('teams.csv').decode());self.assertNotIn(LOGIN,archive.read('submissions.csv').decode());self.assertIn(LOGIN,archive.read('test-submissions.csv').decode())

if __name__=='__main__':unittest.main()
