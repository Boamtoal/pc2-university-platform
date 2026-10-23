import sys,tempfile,json,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]));sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from participant_access import access,checks,configuration
class Access(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.state=Path(self.temp.name);(self.state/'network').mkdir();self.profile=self.state/'network/profile.json';self.profile.write_text(json.dumps({'origin':'http://192.168.10.3:8088','interface':'en0','automatic':True}));self.row={'state':str(self.state),'id':'fixture'};self.app=SimpleNamespace(manager=SimpleNamespace(selected=lambda:self.row,data={'active':'fixture','selected':'fixture'}))
 def tearDown(self):self.temp.cleanup()
 def test_share_only_current_assigned_private_managed_address(self):
  with patch('participant_access.local_addresses',return_value=[{'ip':'192.168.10.3','interface':'en0','cidr':'192.168.10.0/24'}]):
   result=access(self.app);self.assertEqual(result['origin'],'http://192.168.10.3:8088');self.assertEqual(len(result['links']),5);self.assertTrue(result['links'][2]['requiresLogin'])
   self.app.manager.data['active']='other';self.assertFalse(access(self.app)['links'])
  self.app.manager.data['active']='fixture'
  with patch('participant_access.local_addresses',return_value=[{'ip':'192.168.20.3','interface':'en0','cidr':'192.168.20.0/24'}]):self.assertIsNone(access(self.app)['origin'])
  for origin in ['http://127.0.0.1:8091','http://8.8.8.8:8088','http://x:y@192.168.10.3:8088','http://192.168.10.3:8091','http://192.168.10.3:8088/secret']:
   self.profile.write_text(json.dumps({'origin':origin}))
   with patch('participant_access.local_addresses',return_value=[]):self.assertFalse(access(self.app)['links'])
 def test_server_checks_never_submit_or_start_a_clock(self):
  calls=[]
  def call(op,args):
   calls.append((op,args));return {'rows':[{'login':'judge3','enabled':True}]} if args['section']=='autojudges' else {'rows':[{'client':'judge3','connected':True}]}
  self.app.bridge=SimpleNamespace(call=call,snapshot=lambda:{'problems':[{'letter':'A','active':True,'tests':2}]})
  def probe(state,url):return (302,b'',{}) if url.endswith('/problems/') else (200,b'{}',{}) if url.endswith('json') else (200,b'<html>Fixture</html>',{})
  with patch('participant_access.local_addresses',return_value=[{'ip':'192.168.10.3','interface':'en0','cidr':'192.168.10.0/24'}]),patch('participant_access.probe',side_effect=probe):result=checks(self.app)
  self.assertTrue(all(r['status']=='passed' for r in result['checks']));self.assertTrue(all(op=='admin.query' for op,args in calls))
  self.assertNotEqual(configuration({'problems':[{'tests':1}]},[]),configuration({'problems':[{'tests':2}]},[]))
 def test_sidebar_server_inventory_uses_active_workspace_while_viewing_a_draft(self):
  active=self.row;draft={'id':'draft','state':str(self.state/'draft')};self.app.manager.selected=lambda:draft;self.app.manager.row=lambda cid:active if cid=='fixture' else draft
  with patch('participant_access.local_addresses',return_value=[{'ip':'192.168.10.3','interface':'en0','cidr':'192.168.10.0/24'}]):
   self.assertIsNone(access(self.app)['ip']);self.assertEqual(access(self.app,active_workspace=True)['ip'],'192.168.10.3')
   self.app.manager.data['active']=None;self.assertIsNone(access(self.app,active_workspace=True)['ip'])
if __name__=='__main__':unittest.main()
