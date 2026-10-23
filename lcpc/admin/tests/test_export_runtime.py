"""A fresh source checkout need not already contain a developer's runtime folder."""
import importlib.util,os,shutil,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import contest_exports as exports
class FreshPDFRuntime(unittest.TestCase):
 @unittest.skipUnless(importlib.util.find_spec('reportlab'),'PDF dependency is not installed in this Python')
 def test_pdf_creates_a_private_temp_parent_on_a_clean_install(self):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);target=root/'lcpc/admin';target.mkdir(parents=True);shutil.copyfile(exports.ROOT/'lcpc/admin/report_pdf.py',target/'report_pdf.py')
   data={'contestId':'synthetic','status':'archived','exportedAt':'2026-01-01T00:00:00Z','snapshot':{'contest':{'title':'Synthetic empty contest'},'teams':[],'runs':[],'problems':[],'clarifications':[]},'resources':[],'audit':[],'notes':[]}
   with patch.object(exports,'ROOT',root):raw=exports.pdf_report(data)
   self.assertTrue(raw.startswith(b'%PDF'));self.assertEqual((root/'.local').stat().st_mode&0o077,0);self.assertEqual(list((root/'.local').iterdir()),[])
if __name__=='__main__':unittest.main()
