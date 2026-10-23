import json,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from contest_runtime import stop_exporters
from core import ROOT
from infra import vm

class Recovery(unittest.TestCase):
 def test_server_exiting_between_pid_probes_is_stopped_but_live_pid_mismatch_is_rejected(self):
  from contest_runtime import controller
  with tempfile.TemporaryDirectory() as folder:
   state=Path(folder);(state/'server.pid').write_text('12345');ctl=controller(state)
   with patch.object(ctl,'alive',side_effect=[True,False]),patch.object(ctl.subprocess,'run',return_value=SimpleNamespace(stdout='')):self.assertIsNone(ctl.pid_for('server'))
   with patch.object(ctl,'alive',return_value=True),patch.object(ctl.subprocess,'run',return_value=SimpleNamespace(stdout='some-other-program')):
    with self.assertRaisesRegex(RuntimeError,'identity'):ctl.pid_for('server')
 def test_exporter_cleanup_is_restricted_to_exact_contest_and_program(self):
  with tempfile.TemporaryDirectory() as folder:
   state=Path(folder)/'contest';state.mkdir();(state/'public-standings.pid').write_text('101')
   script=ROOT/'lcpc/public_standings.py'
   listing=f'101 S /usr/bin/python3 {script} --state {state}\n102 S /usr/bin/java -Dlcpc.secrets={state}/credentials.properties PublicStandings\n103 S /usr/bin/python3 {script} --state /some/other/contest\n104 S /usr/bin/java -Dlcpc.secrets={state}/credentials.properties OtherProgram\n105 Z /usr/bin/python3 {script} --state {state}\n'
   with patch('contest_runtime.subprocess.check_output',return_value=listing),patch('contest_runtime.os.kill') as kill:
    stop_exporters(SimpleNamespace(alive=lambda _:False),state,state)
   self.assertEqual([call.args for call in kill.call_args_list],[(101,15),(102,15)])
   self.assertFalse((state/'public-standings.pid').exists())
 def test_existing_stopped_judge_resumes_without_reprovisioning(self):
  with tempfile.TemporaryDirectory() as folder:
   config=Path(folder)/vm.NAME/'lima.yaml';config.parent.mkdir();config.write_text('fixture')
   with patch.dict(vm.ENV,{'LIMA_HOME':folder}),patch.object(vm,'lima',return_value=SimpleNamespace(stdout=json.dumps({'name':vm.NAME,'status':'Stopped'}))) as run:
    vm.ensure_running()
   self.assertEqual(run.call_args_list[1].args[0],['start','--tty=false',vm.NAME])
 def test_running_vm_is_reused_and_missing_vm_does_not_download(self):
  with tempfile.TemporaryDirectory() as folder:
   with patch.dict(vm.ENV,{'LIMA_HOME':folder}),patch.object(vm,'lima') as run:
    with self.assertRaisesRegex(RuntimeError,'not been installed'):vm.ensure_running()
    run.assert_not_called()
   config=Path(folder)/vm.NAME/'lima.yaml';config.parent.mkdir();config.write_text('fixture')
   with patch.dict(vm.ENV,{'LIMA_HOME':folder}),patch.object(vm,'lima',return_value=SimpleNamespace(stdout=json.dumps({'name':vm.NAME,'status':'Running'}))) as run:
    vm.ensure_running();self.assertEqual(run.call_count,1)

if __name__=='__main__':unittest.main()
