"""PDF content/font assertions only. No visual inspection or team code execution."""
import base64,json,subprocess,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path(__file__).resolve().parent))
import test_learning_reports as fixtures
from learning_reports import build_team,save_material
from contest_exports import BUNDLED_PYTHON,ROOT

class LearningPDF(unittest.TestCase):
 def test_reference_is_real_cpp_and_every_test_contains_input_actual_and_expected(self):
  fixture=fixtures.Learning();fixture.setUp()
  try:
   code=b'#include <iostream>\nint main(){std::cout<<3;}\n'
   save_material(fixture.store,fixture.snapshot,{'problemId':'p1','kind':'solution','filename':'reference.cpp','base64':base64.b64encode(code).decode()})
   report=build_team(fixture.store,fixture.snapshot,fixture.snapshot['teams'][0],{},fixture.native,fixture.raw,fixture.target,'2026-10-21T12:00:00+00:00')
   attempt=report['problems'][0]['attempts'][0]
   attempt['replayTests']=[{'number':1,'executed':True,'exit':244,'executionStatus':'Time Limit Exceeded','comparison':'Different output','input':{'text':'1 2\n'},'output':{'text':'9\n'},'expected':{'text':'3\n'}}]
   (fixture.target/'report.json').write_text(json.dumps(report))
   pdf=fixture.target/'report.pdf';result=subprocess.run([str(BUNDLED_PYTHON),str(ROOT/'lcpc/admin/learning_pdf.py'),str(fixture.target/'report.json'),str(pdf)],capture_output=True,text=True,timeout=30)
   self.assertEqual(result.returncode,0,result.stderr)
   check='''from pypdf import PdfReader
import sys
r=PdfReader(sys.argv[1]);s='\\n'.join(p.extract_text() or '' for p in r.pages)
for value in ('#include <iostream>','Organizer reference solution - C++','Time Limit Exceeded','Input','Team output - actual replay stdout','Correct output - expected answer'):assert value in s,value
assert 'Recorded test outcomes' not in s
assert '@@' not in s
fonts=[str(f.get_object().get('/BaseFont','')) for p in r.pages for f in p.get('/Resources',{}).get('/Font',{}).values()]
assert any('Courier' in name for name in fonts),fonts
'''
   result=subprocess.run([str(BUNDLED_PYTHON),'-c',check,str(pdf)],capture_output=True,text=True,timeout=20);self.assertEqual(result.returncode,0,result.stderr)
  finally:fixture.tearDown()

if __name__=='__main__':unittest.main()
