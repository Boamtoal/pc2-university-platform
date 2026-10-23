import importlib.util,json,tempfile,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('package_source',Path(__file__).resolve().parents[1]/'package-source.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class PublicationTests(unittest.TestCase):
 def test_operational_and_student_data_is_not_selected(self):
  for file in ['.local/credentials.properties','output/teams.pdf','lcpc/contest/config/A/data/secret/01.in','lcpc/solutions/actual.cpp','lcpc/admin/__pycache__/x.pyc','lcpc/branding/uploads/logo.png','lcpc/src/EventProblemImport.java','work/logs/account.txt','lcpc/admin/real.csv']:
   self.assertFalse(m.allowed(Path(file)),file)
 def test_required_templates_and_synthetic_tests_are_selected(self):
  for file in ['lcpc/admin/timezones.json','lcpc/admin/server.py','lcpc/admin/tests/test_core.py','lcpc/branding/tests/fixtures/pc2-scoreboard.json','lcpc/public-problems/index.html','lcpc/templates/practice/config/sum/data/secret/01.ans','lcpc/infra/linux/compile17','NOTICE.md']:
   self.assertTrue(m.allowed(Path(file)),file)
 def test_secret_and_home_indicators_are_rejected_without_printing_them(self):
  for raw in [b'-----BEGIN '+b'PRIVATE KEY-----',b'ghp_'+b'a'*32,b'/Users/'+b'fixtureperson/anything',b'10.199.'+b'178.7']:
   self.assertTrue(m.inspect(Path('example.py'),raw))
  self.assertFalse(m.inspect(Path('test.py'),b'password=secrets.token_urlsafe(32)'))
 def test_existing_output_is_never_overwritten(self):
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaises(ValueError):m.package(Path(d),Path(d))
if __name__=='__main__':unittest.main()
