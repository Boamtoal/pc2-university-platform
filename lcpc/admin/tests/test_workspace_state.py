import json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from workspace_state import managed_state

class WorkspaceSelectionTest(unittest.TestCase):
 def test_draft_selected_without_active_runtime(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);state=root/'.local/instances/new-contest';state.mkdir(parents=True)
   registry=root/'.local/contest-manager/registry.json';registry.parent.mkdir()
   registry.write_text(json.dumps({'selected':'new-contest','active':None,'contests':[{'id':'new-contest','state':str(state)}]}))
   self.assertEqual(managed_state(root=root),state.resolve())
   with self.assertRaisesRegex(RuntimeError,'No contest is active'):managed_state(root=root,active=True)
   self.assertFalse((root/'.local/instances/lcpc-omu-preparation').exists())
 def test_selected_draft_and_active_contest_are_distinct(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);rows=[]
   for cid in ('draft','live'):
    state=root/'.local/instances'/cid;state.mkdir(parents=True);rows.append({'id':cid,'state':str(state)})
   registry=root/'.local/contest-manager/registry.json';registry.parent.mkdir()
   registry.write_text(json.dumps({'selected':'draft','active':'live','contests':rows}))
   self.assertEqual(managed_state(root=root).name,'draft')
   self.assertEqual(managed_state(root=root,active=True).name,'live')
 def test_outside_workspace_and_missing_state_are_rejected(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);registry=root/'.local/contest-manager/registry.json';registry.parent.mkdir(parents=True)
   for invalid in (root/'outside',root/'.local/instances/missing'):
    registry.write_text(json.dumps({'selected':'missing','active':'missing','contests':[{'id':'missing','state':str(invalid)}]}))
    with self.assertRaisesRegex(RuntimeError,'missing or invalid'):managed_state(root=root)

if __name__=='__main__':unittest.main()
