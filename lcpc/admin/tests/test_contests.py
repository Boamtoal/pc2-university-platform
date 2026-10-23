import base64,copy,hashlib,io,json,sys,tempfile,unittest,zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]));sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from core import Store,Error,prepare_judge_data,ROOT
from contests import ContestManager,DraftBridge,write_json,read_json
from contest_exports import csv_report,report_data,full_backup
from contest_runtime import prepare_instance
from restore_backup import restore
from infra.runtime_guard import ensure_single

class Fake:
 process=None
 def __init__(self,state):
  self.state=state;self.calls=[];self.data={'contest':{'title':'Original Contest','shortName':'ORIG','running':False,'elapsedSeconds':60,'remainingSeconds':3540,'lengthSeconds':3600,'freezeRemaining':'00:00:00','thawed':False,'scheduledStart':None},'teams':[{'number':7,'login':'team7','name':'Existing team','enabled':True,'visible':True}],'problems':[{'id':'p1','letter':'A','shortName':'alpha','name':'Alpha','timeLimit':2,'memoryLimit':128,'active':True,'tests':1,'judgingMode':'automatic'}],'runs':[{'number':4,'site':1,'team':'team7','teamName':'Existing team','problem':'Alpha','verdict':'Accepted','final':True,'accepted':True,'deleted':False}],'clarifications':[],'standings':{},'languages':[],'judging':{'mode':'automatic'}}
 def snapshot(self,fresh=False):return copy.deepcopy(self.data)
 def call(self,op,args=None):
  self.calls.append((op,args));folder=self.state/'admin-dashboard/template-exports';folder.mkdir(exist_ok=True);file=folder/'generated.bin';file.write_bytes(b'fixture-template-generated-by-native-service');return {'path':str(file),'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'languages':[{'name':'GNU C++17 (Isolated Linux ARM64)','active':True,'compilerCmd':'/opt/lcpc/bin/compile17 {:mainfile} {:basename}','exemask':'{:basename}','execCmd':'./{:basename}'}]}
 def close(self):pass
class Contests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.state=Path(self.temp.name)/'current';self.state.mkdir();self.state=self.state.resolve();self.store=Store(self.state);self.bridge=Fake(self.state);self.app=SimpleNamespace(store=self.store,resources=self.store,bridge=self.bridge);self.manager=ContestManager(self.app)
  self.args={'title':'Next Contest','shortName':'NEXT','slug':'next-contest','durationMinutes':180,'penaltyMinutes':20,'workflow':'review','copyProblems':True,'copyResources':False}
 def tearDown(self):self.manager.close();self.temp.cleanup()
 def create(self):return self.manager.create(self.args)['id']
 def test_create_is_independent_and_does_not_copy_teams_or_runs(self):
  before=copy.deepcopy(self.bridge.data);cid=self.create();self.assertEqual(self.manager.data['active'],self.state.name);self.assertEqual(self.manager.data['selected'],self.state.name)
  self.manager.select(cid);snap=self.app.bridge.snapshot();self.assertEqual(snap['runs'],[]);self.assertEqual(len(snap['teams']),1);self.assertTrue(snap['teams'][0]['testAccount']);self.assertFalse(snap['teams'][0]['visible']);self.assertEqual(len(snap['problems']),1);self.assertEqual(self.bridge.data,before);self.assertNotIn('credentials.properties',[p.name for p in Path(self.manager.row(cid)['state']).iterdir()])
 def test_empty_draft_can_add_first_problem_and_private_tests(self):
  self.args['copyProblems']=False;cid=self.create();self.manager.select(cid);store=self.app.resources;out=io.BytesIO()
  with zipfile.ZipFile(out,'w') as archive:archive.writestr('01.in','1 2');archive.writestr('01.ans','3')
  directory=prepare_judge_data(store,base64.b64encode(out.getvalue()).decode());result=self.app.bridge.call('problem.create',{'directory':str(directory),'name':'Sum','letter':'A','timeLimit':2,'memoryLimit':128,'template':'__default__'});snapshot=self.app.bridge.snapshot();self.assertEqual(snapshot['problems'][0]['tests'],1);self.assertFalse(snapshot['problems'][0]['active']);self.assertNotIn('dataDirectory',snapshot['problems'][0])
  pid=result['id'];self.app.bridge.call('problem.update',{'id':pid,'name':'Sum','timeLimit':2,'memoryLimit':128,'active':False,'colorName':'Red','colorRGB':'#ff0000'});colored=self.app.bridge.snapshot()['problems'][0];self.assertEqual((colored['colorName'],colored['colorRGB']),('Red','#ff0000'))
  self.app.bridge.call('team.create',{'name':'New team','password':'Test-only-long-password'});self.assertNotIn('password',self.app.bridge.snapshot()['teams'][0]);self.assertEqual(self.bridge.data['teams'][0]['login'],'team7')
 def test_second_active_is_blocked_even_if_original_clock_paused(self):
  cid=self.create()
  with self.assertRaisesRegex(Error,'Another contest is active'):self.manager.start_job('activate',cid,'owner')
  self.assertIsNone(self.manager.job);self.assertEqual(self.bridge.calls[0][0],'template.export')
 def test_archive_active_rejected_and_archived_mutations_blocked(self):
  with self.assertRaisesRegex(Error,'Deactivate'):self.manager.archive(self.state.name,True)
  cid=self.create();self.manager.archive(cid,True);self.manager.select(cid)
  with self.assertRaisesRegex(Error,'archived'):self.manager.allow_native_mutation()
  self.manager.archive(cid,False);self.assertEqual(self.manager.row(cid)['status'],'draft')
 def test_stale_tab_and_busy_jobs_reject_mutations(self):
  cid=self.create();self.manager.select(cid)
  with self.assertRaisesRegex(Error,'selected contest changed'):self.manager.guard({'contestId':self.state.name})
  self.manager.job={'status':'running'}
  with self.assertRaisesRegex(Error,'in progress'):self.manager.guard({'contestId':cid})
  self.manager.job=None
 def test_unique_names_and_path_restrictions(self):
  self.create()
  with self.assertRaisesRegex(Error,'already exists'):self.create()
  self.args['slug']='../../bad'
  with self.assertRaises(Error):self.create()
 def test_resources_are_copied_as_unpublished_drafts_only(self):
  rid=self.store.upload({'problem':'p1','kind':'helper','language':'ar','label':'Supporting data','filename':'help.txt','base64':base64.b64encode('hello'.encode()).decode()})
  with self.store.db() as db:db.execute('UPDATE resources SET published=1 WHERE id=?',(rid,))
  self.args['copyResources']=True;cid=self.create();self.manager.select(cid);rows=self.app.resources.resources();self.assertEqual(len(rows),1);self.assertFalse(rows[0]['published']);self.assertNotEqual(rows[0]['id'],rid);self.assertTrue(self.store.resources()[0]['published'])
 def test_catalog_and_selection_persist(self):
  cid=self.create();self.manager.select(cid);new=ContestManager(SimpleNamespace(store=self.store,resources=self.store,bridge=self.bridge));self.assertEqual(new.data['selected'],cid);self.assertEqual(new.data['active'],self.state.name);new.close()
 def test_export_csv_preserves_metadata_and_defuses_formula_cells(self):
  self.bridge.data['teams'][0]['name']='=WEBSERVICE("bad")';data=report_data(self.manager,self.manager.selected());raw=csv_report(data)
  with zipfile.ZipFile(io.BytesIO(raw)) as archive:
   self.assertIn('submissions.csv',archive.namelist());self.assertIn("'=WEBSERVICE",archive.read('teams.csv').decode('utf-8-sig'));self.assertEqual(len(json.loads(archive.read('snapshot.json'))['snapshot']['runs']),1)
 def test_active_backup_and_running_deactivation_are_rejected(self):
  with self.assertRaisesRegex(Error,'Deactivate'):self.manager.start_job('backup',self.state.name,'owner')
  self.bridge.data['contest']['running']=True
  with self.assertRaisesRegex(Error,'Pause'):self.manager.start_job('deactivate',self.state.name,'owner')
  self.bridge.data['contest']['running']=False;self.bridge.data['runs'][0]['final']=False
  with self.assertRaisesRegex(Error,'pending'):self.manager.start_job('deactivate',self.state.name,'owner')
 def test_empty_draft_is_not_activatable(self):
  cid=self.create();self.manager.data['active']=None
  with self.assertRaisesRegex(Error,'Add teams'):self.manager.start_job('activate',cid,'owner')
 def test_cli_runtime_guard_rejects_other_server_and_reservation(self):
  with patch('infra.runtime_guard.server_states',return_value=[self.state]):
   with self.assertRaisesRegex(RuntimeError,'Another contest'):ensure_single(self.temp.name,Path(self.temp.name)/'other')
  registry=Path(self.temp.name)/'.local/contest-manager/registry.json';write_json(registry,{'active':'current','contests':[{'id':'current','state':str(self.state)}]})
  with patch('infra.runtime_guard.server_states',return_value=[]):
   with self.assertRaisesRegex(RuntimeError,'reserved'):ensure_single(self.temp.name,Path(self.temp.name)/'other')
 def test_deactivation_preserves_snapshot_and_activation_leaves_clock_paused(self):
  from contest_runtime import deactivate,activate
  from contextlib import nullcontext
  (self.state/'secured').write_text('fixture')
  ctl=SimpleNamespace(ROLES=[],pid_for=lambda _:None,terminate=lambda _:None,start=lambda *a:None)
  with patch('contest_runtime.runtime_lock',side_effect=nullcontext),patch('contest_runtime.controller',return_value=ctl),patch('contest_runtime.Bridge',return_value=self.bridge),patch('infra.network.stop'),patch('infra.vm.ACTIVE',Path(self.temp.name)/'absent-marker'),patch('contest_runtime.subprocess.check_output',return_value=''):
   result=deactivate(self.manager,self.manager.selected())
  self.assertTrue(result['preserved']);self.assertIsNone(self.manager.data['active']);self.assertEqual(read_json(self.state/'admin-dashboard/last-snapshot.json')['runs'],self.bridge.data['runs'])
  self.assertTrue((self.state/'admin-dashboard/clone-template.json').exists())
  web=self.state/'wti/WebContent/WTI-UI';web.mkdir(parents=True,exist_ok=True);(web/'index.html').write_text('<html><head></head><body></body></html>')
  proc=SimpleNamespace(pid=99999999,poll=lambda:None)
  with patch('contest_runtime.runtime_lock',side_effect=nullcontext),patch('contest_runtime.controller',return_value=ctl),patch('contest_runtime.other_server',return_value=False),patch('contest_runtime.Bridge',return_value=self.bridge),patch('infra.vm.judge_start'),patch('contest_runtime.subprocess.Popen',return_value=proc),patch('contest_runtime.time.sleep'):
   result=activate(self.manager,self.manager.selected())
  self.assertFalse(result['clockStarted']);self.assertEqual(self.manager.data['active'],self.state.name);self.assertFalse(any(op=='clock.start' for op,args in self.bridge.calls));self.assertEqual(self.bridge.data['runs'][0]['number'],4)
 def test_shutdown_reconnects_and_keeps_transport_open_until_server_stops(self):
  from contest_runtime import deactivate
  from contextlib import nullcontext
  fresh=Fake(self.state);fresh.closed=False
  fresh.close=lambda:setattr(fresh,'closed',True)
  polls=[]
  def pid_for(role):
   self.assertFalse(fresh.closed,'Shutdown transport closed before server exit')
   self.assertEqual(fresh.calls[-1][0],'runtime.shutdown')
   polls.append(role);return 123 if len(polls)==1 else None
  ctl=SimpleNamespace(ROLES=[],pid_for=pid_for,terminate=lambda _:None)
  with patch('contest_runtime.runtime_lock',side_effect=nullcontext),patch('contest_runtime.controller',return_value=ctl),patch('contest_runtime.Bridge',return_value=fresh) as reconnect,patch('infra.network.stop'),patch('infra.vm.ACTIVE',Path(self.temp.name)/'absent-marker'),patch('contest_runtime.subprocess.check_output',return_value=''),patch('contest_runtime.time.sleep'):
   deactivate(self.manager,self.manager.selected())
  reconnect.assert_called_once_with(self.state)
  self.assertGreaterEqual(len(polls),2);self.assertTrue(fresh.closed)
  self.assertIsNone(self.manager.data['active'])
 def test_activation_failure_retains_reservation_when_server_survives(self):
  from contest_runtime import activate
  from contextlib import nullcontext
  (self.state/'secured').write_text('fixture');self.manager.data['active']=None
  ctl=SimpleNamespace(pid_for=lambda _:123,start=lambda *a:(_ for _ in ()).throw(RuntimeError('fixture startup failed')))
  with patch('contest_runtime.runtime_lock',side_effect=nullcontext),patch('contest_runtime.controller',return_value=ctl),patch('contest_runtime.other_server',return_value=False),patch('infra.network.stop'):
   with self.assertRaisesRegex(RuntimeError,'fixture startup failed'):activate(self.manager,self.manager.selected())
  self.assertEqual(self.manager.data['active'],self.state.name);self.assertEqual(self.manager.selected()['status'],'error')
 def test_encrypted_backup_restore_roundtrip_with_independent_key(self):
  self.manager.data['active']=None;source=self.state/'saved-source.cpp';source.write_text('int main() {}');keydir=Path(self.temp.name)/'keys';keydir.mkdir()
  from infra.participant_activity import ActivityStore
  activity=ActivityStore(self.state);activity.bind('11111111-1111-4111-8111-111111111111','team7');activity.record('login',login='team7')
  from infra import secure_backup
  real=secure_backup.keypair
  with patch.object(secure_backup,'keypair',side_effect=lambda base:real(keydir)),patch('contest_runtime.controller',return_value=SimpleNamespace(ROLES=[],pid_for=lambda _:None)):
   result=full_backup(self.manager,self.manager.selected())
  folder=self.manager.base/'backups'/result['backupId'];target=Path(self.temp.name)/'restored';restored=restore(folder/'backup.zip',keydir/'backup-keys',target);self.assertEqual((target/'saved-source.cpp').read_text(),'int main() {}');self.assertEqual(restored['restoredFrom'],'current')
  recovered=ActivityStore(target);self.assertTrue(recovered.verify()['valid']);self.assertEqual(recovered.query()['events'][0]['team'],'team7');self.assertEqual(recovered.identity('11111111-1111-4111-8111-111111111111'),'')
  with self.assertRaisesRegex(Error,'already exists'):restore(folder/'backup.zip',keydir/'backup-keys',target)
  with zipfile.ZipFile(folder/'backup.zip') as archive:
   manifest=json.loads(archive.read('manifest.json'));cipher=bytearray(archive.read('contest.tar.gz.cms'));cipher[-1]^=1
  bad=Path(self.temp.name)/'tampered.zip'
  with zipfile.ZipFile(bad,'w') as archive:archive.writestr('manifest.json',json.dumps(manifest));archive.writestr('contest.tar.gz.cms',cipher)
  with self.assertRaisesRegex(Error,'integrity'):restore(bad,keydir/'backup-keys',Path(self.temp.name)/'tampered-restored')

if __name__=='__main__':unittest.main(verbosity=2)
