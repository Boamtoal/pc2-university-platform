import copy,json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core import Store
from problem_difficulty import save,load,annotate,inherit

class Difficulty(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();path=Path(self.temp.name)/'source';path.mkdir();self.store=Store(path)
 def tearDown(self):
  for handler in list(self.store.logger.handlers):handler.close();self.store.logger.removeHandler(handler)
  self.temp.cleanup()
 def test_native_id_change_retains_rating_without_mutating_public_snapshot(self):
  save(self.store,{'stable-short-name':{'value':1350,'estimated':True}})
  source={'problems':[{'id':'new-native-id','shortName':'stable-short-name','letter':'A'}]};original=copy.deepcopy(source)
  decorated=annotate(source,self.store)
  self.assertEqual(decorated['problems'][0]['difficulty'],1350)
  self.assertTrue(decorated['problems'][0]['difficultyEstimated']);self.assertEqual(source,original)
 def test_missing_rating_is_not_fabricated(self):
  row=annotate({'problems':[{'id':'x','shortName':'unrated'}]},self.store)['problems'][0]
  self.assertIsNone(row['difficulty']);self.assertFalse(row['difficultyEstimated'])
 def test_copy_only_includes_selected_problem_ratings(self):
  save(self.store,{'a':{'value':800,'estimated':False},'b':{'value':1800,'estimated':False}})
  path=Path(self.temp.name)/'target';path.mkdir();target=Store(path)
  try:
   inherit(self.store,target,[{'shortName':'b'}]);self.assertEqual(load(target),{'b':{'value':1800,'estimated':False}})
   inherit(self.store,target,[]);self.assertEqual(load(target),{})
  finally:
   for h in list(target.logger.handlers):h.close();target.logger.removeHandler(h)
 def test_invalid_rating_cannot_overwrite_stored_values(self):
  save(self.store,{'a':{'value':900,'estimated':False}})
  for value in [True,-5,0,10001,'1500',None]:
   with self.assertRaises(ValueError):save(self.store,{'a':{'value':value,'estimated':False}})
  self.assertEqual(load(self.store)['a']['value'],900)

if __name__=='__main__':unittest.main()
