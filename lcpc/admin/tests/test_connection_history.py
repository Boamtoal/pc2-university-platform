import sys,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]));sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from infra.participant_activity import ActivityStore
from infra import connection_history as history
TOKEN='11111111-1111-4111-8111-111111111111'
class History(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.state=Path(self.temp.name);(self.state/'network').mkdir();(self.state/'network/profile.json').write_text(json.dumps({'cidr':'192.168.10.0/24'}));self.store=ActivityStore(self.state);self.store.bind(TOKEN,'team7');self.t=1000
 def tearDown(self):self.temp.cleanup()
 def signal(self,client='a'*32,event='heartbeat',ip='192.168.10.4',token=TOKEN,reported='team7'):
  with patch('infra.participant_activity.time.time',return_value=self.t):self.store.telemetry({'client':client,'reportedTeam':reported,'events':[{'event':event,'details':{'page':'runs'}}]},token,ip)
 def view(self):
  with patch('infra.connection_history.time.time',return_value=self.t):return history.view(self.store,[{'login':'team7','name':'Fixture','online':True}])['teams'][0]
 def test_overlapping_tabs_are_merged_and_signal_gaps_excluded(self):
  self.signal();self.t+=10;self.signal();self.signal('b'*32);self.t+=10;self.signal();self.signal('b'*32);self.assertEqual(self.view()['observedSeconds'],20)
  self.t+=181;self.store.sweep(now=self.t);self.assertEqual(self.view()['state'],'missing');self.assertEqual(self.view()['observedSeconds'],20)
  self.signal();self.t+=10;self.signal();self.assertEqual(self.view()['observedSeconds'],30);self.assertFalse(self.store.query()['issues']) # another recent tab confirms this team/IP is reachable
 def test_networks_are_recorded_as_cidr_not_assumed_ssid(self):
  self.signal();self.t+=10;self.signal();(self.state/'network/profile.json').write_text(json.dumps({'cidr':'192.168.20.0/24'}));self.t+=10;self.signal(ip='192.168.20.4');self.t+=10;self.signal(ip='192.168.20.4');self.assertEqual({n['network'] for n in self.view()['networks']},{'192.168.10.0/24','192.168.20.0/24'});self.assertEqual(self.view()['observedSeconds'],20)
 def test_unverified_reports_do_not_inflate_verified_time(self):
  self.signal(token='22222222-2222-4222-8222-222222222222');self.t+=10;self.signal(token='22222222-2222-4222-8222-222222222222');row=self.view();self.assertEqual(row['state'],'unverified');self.assertEqual(row['observedSeconds'],0);self.assertEqual(row['reportedSeconds'],10)
 def test_refresh_is_debounced_but_page_left_is_reported_and_logout_suppressed(self):
  self.signal();self.t+=10;self.signal(event='page.close');self.t+=3;self.store.sweep(now=self.t);self.assertFalse(self.store.query()['issues']);self.signal(event='page.open');self.t+=10;self.signal(event='page.close');self.t+=91;self.store.sweep(now=self.t);self.assertEqual(self.store.query()['issues'][0]['event'],'connection.page_closed');self.signal();self.assertFalse(self.store.query()['issues']);self.store.unbind(TOKEN);self.t+=100;self.store.sweep(now=self.t);self.assertFalse(self.store.query()['issues']);self.assertEqual(self.view()['state'],'closed')
 def test_a_recovery_during_sweep_cannot_leave_a_stale_disconnect_incident(self):
  self.signal();self.t+=181;record=self.store.record
  def racing(event,**kwargs):
   if event=='connection.signal_missing':self.signal()
   return record(event,**kwargs)
  with patch.object(self.store,'record',side_effect=racing):self.store.sweep(now=self.t)
  self.assertFalse(self.store.query()['issues']);self.assertEqual(self.view()['state'],'recent')
 def test_background_tab_and_navigation_do_not_create_connection_alerts(self):
  self.signal();self.t+=60;self.store.sweep(now=self.t);self.assertFalse(self.store.query()['issues']);self.signal()
  self.signal(event='page.close');self.t+=30;self.store.sweep(now=self.t);self.assertFalse(self.store.query()['issues']);self.signal(client='b'*32,event='page.open')
  self.t+=60;self.store.sweep(now=self.t);self.signal(client='b'*32)
  self.assertFalse(self.store.query()['issues']);self.assertFalse([e for e in self.store.query()['events'] if e['event']=='connection.signal_restored'])
 def test_real_outage_has_one_loss_and_one_recovery_for_overlapping_tabs(self):
  self.signal();self.signal('b'*32);self.t+=181;self.store.sweep(now=self.t);self.store.sweep(now=self.t+5)
  self.signal();self.signal('b'*32)
  rows=self.store.query()['events'];self.assertEqual(sum(e['event']=='connection.signal_restored' for e in rows),1);self.assertEqual(sum(e['event']=='connection.signal_missing' for e in rows),1)
if __name__=='__main__':unittest.main()
