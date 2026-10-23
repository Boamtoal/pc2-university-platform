import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from infra.submission_receipts import Receipts
class Retry(unittest.TestCase):
 def setUp(self):self.temp=tempfile.TemporaryDirectory();self.store=Receipts(self.temp.name)
 def tearDown(self):self.temp.cleanup()
 def test_receipt_replay_is_bound_to_session_and_exact_payload(self):
  key='a'*32;scope,cached=self.store.claim('team1-token',key,b'private-source');self.assertIsNone(cached);self.store.complete(scope,200,b'{}')
  self.assertEqual(self.store.claim('team1-token',key,b'private-source')[1],(200,b'{}'))
  self.assertEqual(self.store.claim('team1-token',key,b'other')[1][0],409)
  self.assertIsNone(self.store.claim('team2-token',key,b'private-source')[1]);self.assertNotIn(b'private-source',self.store.path.read_bytes());self.assertNotIn(b'team1-token',self.store.path.read_bytes())
 def test_unknown_delivery_is_not_sent_again_after_a_restart(self):
  scope,_=self.store.claim('token','b'*32,b'payload');self.store.complete(scope,503,b'failure');self.store=Receipts(self.temp.name)
  self.assertEqual(self.store.claim('token','b'*32,b'payload')[1][0],409)
