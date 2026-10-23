import json,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]));sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from core import Store
from notifications import listing,initialize
from infra.participant_activity import ActivityStore
class Inbox(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.state=Path(self.temp.name);self.store=Store(self.state);self.row={'id':'fixture','state':str(self.state)};self.app=SimpleNamespace(store=self.store,manager=SimpleNamespace(data={'contests':[self.row]}));self.activity=ActivityStore(self.state)
 def tearDown(self):self.temp.cleanup()
 def test_security_losses_and_returns_are_retained_and_deduplicated(self):
  self.store.audit('fixture','test','denied',alert=('warning','Security fixture'))
  self.activity.record('connection.signal_missing',login='team7',source='observer',severity='warning')
  self.activity.record('connection.signal_restored',login='team7',source='observer',outcome='restored')
  data=listing(self.app,{'username':'owner'},{});self.assertEqual(data['unread'],3);self.assertEqual({v['category'] for v in data['notifications']},{'security','connection'});self.assertEqual(data['notifications'][0]['severity'],'success')
  again=listing(self.app,{'username':'owner'},{});self.assertEqual(again['latest'],data['latest']);self.assertEqual(again['unread'],3)
  with self.activity.db() as db:db.execute('DELETE FROM events')
  self.assertEqual(len(listing(self.app,{'username':'owner'},{})['notifications']),3,'The inbox keeps its history after the original event retention period')
 def test_read_receipts_persist_per_owner_without_resolving_incidents(self):
  self.store.audit('fixture','test','denied',alert=('error','Security fixture'));data=listing(self.app,{'username':'owner'},{});nid=data['notifications'][0]['id']
  with self.store.db() as db:db.execute("INSERT INTO notification_reads VALUES('owner',?,'read')",(nid,))
  self.assertEqual(listing(self.app,{'username':'owner'},{})['unread'],0);self.assertEqual(listing(self.app,{'username':'second-owner'},{})['unread'],1)
  with self.store.db() as db:self.assertEqual(db.execute('SELECT acknowledged FROM alerts').fetchone()[0],0)
  self.app.store=Store(self.state);self.assertEqual(listing(self.app,{'username':'owner'},{})['unread'],0)
 def test_incremental_feed_and_filters_keep_connection_restore_messages(self):
  first=listing(self.app,{'username':'owner'},{})['latest'];self.activity.record('team.connection.updated',login='team2',source='pc2',details={'online':True})
  rows=listing(self.app,{'username':'owner'},{'after':[str(first)],'category':['connection'],'search':['team2']})['notifications'];self.assertEqual(rows,[],'Native login changes are retained as diagnostics, not duplicate browser connection popups')
 def test_repeated_request_warnings_are_grouped_and_expected_public_probes_are_silent(self):
  for _ in range(4):self.activity.record('request.failed',ip='192.168.10.4',source='browser',severity='warning',details={'page':'runs','endpoint':'runs','status':503})
  self.activity.record('request.failed',ip='192.168.10.4',source='browser',severity='warning',details={'page':'instructions','endpoint':'other','status':401})
  self.activity.record('request.failed',login='team2',source='browser',severity='warning',details={'page':'runs','endpoint':'runs','status':503,'correlated':True})
  rows=listing(self.app,{'username':'owner'},{})['notifications'];self.assertEqual(len(rows),1);self.assertEqual(rows[0]['occurrences'],4)
  self.assertEqual(listing(self.app,{'username':'owner'},{})['notifications'][0]['occurrences'],4)
 def test_legacy_tab_level_alerts_are_archived_without_deleting_history_or_activity(self):
  with self.store.db() as db:
   db.executescript("CREATE TABLE notifications(id INTEGER PRIMARY KEY,created TEXT,source_key TEXT UNIQUE,category TEXT,contest_id TEXT,severity TEXT,title TEXT,message TEXT,details TEXT);")
   db.execute("INSERT INTO notifications VALUES(1,'2026-10-21T00:00:00+00:00','old','connection','fixture','warning','Old','Old tab signal','{}')")
  self.assertEqual(listing(self.app,{'username':'owner'},{})['unread'],0)
  rows=listing(self.app,{'username':'owner'},{'archived':['1']})['notifications'];self.assertEqual(len(rows),1);self.assertEqual(rows[0]['archived'],1)
if __name__=='__main__':unittest.main()
