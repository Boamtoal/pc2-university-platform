#!/usr/bin/env python3
"""Bounded real Linux sandbox tests; never executes participant programs on Mac."""
from pathlib import Path
import json,time,tarfile,tempfile,subprocess
import vm
ROOT=vm.ROOT

def main():
 results=[]
 with tempfile.TemporaryDirectory(dir=ROOT/'.local') as d:
  archive=Path(d)/'sandbox-tests.tar'
  with tarfile.open(archive,'w') as t:
   for p in (ROOT/'lcpc/infra/tests').glob('*.cpp'):t.add(p,arcname=p.name)
  vm.lima(['copy',str(archive),vm.NAME+':/tmp/sandbox-tests.tar'],capture_output=True)
 vm.guest(['sudo','sh','-c','mkdir -p /var/lib/pc2judge/sandbox-tests; tar xf /tmp/sandbox-tests.tar -C /var/lib/pc2judge/sandbox-tests; chown -R pc2judge:pc2judge /var/lib/pc2judge/sandbox-tests'])
 def invoke(name,mode='compile17'):
  argv=['/opt/lcpc/bin/'+mode,name+'.cpp',name] if mode.startswith('compile') else ['/opt/lcpc/scripts/pc2sandbox.sh','128','5','./'+name]
  q=vm.guest(['sudo','-u','pc2judge','sh','-c','cd /var/lib/pc2judge/sandbox-tests && exec "$@"','sh',*argv],input='2 3\n',capture_output=True,text=True,check=False,timeout=50)
  audit=vm.guest(['sudo','tail','-1','/var/lib/lcpc-jobs/audit.jsonl'],capture_output=True,text=True)
  a=json.loads(audit.stdout);a['test']=name;a['stdout']=q.stdout[:100];a['stderr']=q.stderr[:300];a['returncode']=q.returncode
  results.append(a)
  return a
 a=invoke('ac');assert a['exit']==0,a
 a=invoke('ac','run');assert a['exit']==0 and a['stdout'].strip()=='5',a
 props=a['properties']
 assert props['MemoryMax']=='134217728' and props['TasksMax']=='16' and props['PrivateNetwork']=='yes' and props['RootDirectory']=='/var/lib/lcpc-root',props
 # Resource tests only follow actual enforcement properties and successful smoke test.
 for name,expected in [('isolation',0),('pids',0),('tle',244),('mle',243),('re',139),('filelimit',139),('cpp20',0)]:
  a=invoke(name,'compile20' if name=='cpp20' else 'compile17');assert a['exit']==0,a
  a=invoke(name,'run');assert a['exit']==expected,a
  if expected==0:assert a['stdout'].strip()=='5',a
  print(name+': VERIFIED',flush=True)
 path=ROOT/'work/phase2/sandbox-tests.json';path.write_text(json.dumps(results,indent=2)+'\n')
 print('Evidence: '+str(path))
if __name__=='__main__':main()
