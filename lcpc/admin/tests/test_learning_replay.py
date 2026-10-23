import sys,tempfile,json,hashlib,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from learning_replay import prepare,attach,execution_status

class Replay(unittest.TestCase):
 def test_runtime_limits_and_compile_failures_are_explicit_without_becoming_official_verdicts(self):
  self.assertEqual(execution_status({'executed':True,'exit':244}),'Time Limit Exceeded')
  self.assertEqual(execution_status({'executed':True,'exit':139}),'Runtime Error')
  self.assertEqual(execution_status({'executed':True,'exit':243}),'Memory Limit Exceeded')
  self.assertEqual(execution_status({'executed':False,'exit':None}),'Compilation Error - not executed')
 def test_cache_key_covers_code_compiler_limits_and_input_content(self):
  with tempfile.TemporaryDirectory() as folder:
   native={'problems':[{'id':'p','tests':[{'number':1,'input':{'available':True,'path':'1.in','sha256':'a'}}]}],'runs':[{'site':1,'number':1,'problemId':'p','sources':[{'path':'source.cpp','sha256':'source-a'}]}]}
   snapshot={'problems':[{'id':'p','timeLimit':1,'memoryLimit':128}],'runs':[{'site':1,'number':1,'language':'GNU C++17 (Isolated Linux ARM64)'}]}
   tasks,mapping=prepare(native,Path(folder),snapshot,Path(folder));first=mapping[(1,1)]
   self.assertEqual(tasks[0]['compiler'],'compile17');snapshot['problems'][0]['timeLimit']=2
   self.assertNotEqual(prepare(native,Path(folder),snapshot,Path(folder))[1][(1,1)],first)
 def test_each_case_has_actual_output_expected_input_and_explicit_replay_origin(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);cache=root/'cache';case=cache/'key';case.mkdir(parents=True);team=root/'team';team.mkdir()
   (team/'1.in').write_bytes(b'1 2\n');(team/'1.ans').write_bytes(b'3\n');(case/'1.out').write_bytes(b'9\n');(case/'1.err').write_bytes(b'');(case/'compiler.err').write_bytes(b'')
   (case/'manifest.json').write_text(json.dumps({'compilation':{'exit':0},'provenance':'Current-data isolated Linux replay','tests':[{'number':1,'executed':True,'exit':0}]}))
   report={'problems':[{'tests':[{'number':1,'input':{'available':True,'path':'1.in'},'expected':{'available':True,'path':'1.ans'}}],'attempts':[{'site':1,'number':1,'verdict':'Wrong Answer'}]}]}
   attach(report,team,{(1,1):'key'},cache);attempt=report['problems'][0]['attempts'][0];row=attempt['replayTests'][0]
   self.assertEqual(row['input']['text'],'1 2\n');self.assertEqual(row['output']['text'],'9\n');self.assertEqual(row['expected']['text'],'3\n');self.assertEqual(row['comparison'],'Different output');self.assertEqual(attempt['verdict'],'Wrong Answer');self.assertIn('isolated',attempt['replay']['provenance'])

if __name__=='__main__':unittest.main()
