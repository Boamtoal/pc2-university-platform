#!/usr/bin/env python3
"""Real isolated judging checks against the separate technical contest only."""
from pathlib import Path
import os,sys,subprocess,time,json
root=Path(__file__).resolve().parents[2]
state=root/'.local/instances/linux-trial'
assert json.loads((state/'mode.json').read_text())['mode']=='isolated-trial'
env={**os.environ,'LCPC_STATE_DIR':str(state)}
rows=[]
cases=[('wa','wrong answer'),('ce','compilation error'),('tle','time limit'),('mle','memory limit'),('re','run-time error'),('isolation','yes'),('pids','yes'),('filelimit','run-time error'),('cpp20','yes')]
for name,expected in cases:
 argv=[str(root/'lcpc/pc2ctl.py'),'api','submit','team1','sum',str(root/'lcpc/infra/tests'/f'{name}.cpp'),expected]
 if name=='cpp20':argv+=['GNU C++20 (Isolated Linux ARM64)']
 start=time.monotonic();q=subprocess.run(argv,env=env,capture_output=True,text=True,timeout=120)
 (root/'work/phase2'/f'pc2-linux-{name}.txt').write_text(q.stdout+q.stderr)
 result=next((l for l in q.stdout.splitlines() if l.startswith('RESULT ')),None)
 rows.append({'case':name,'returncode':q.returncode,'result':result,'seconds':round(time.monotonic()-start,3)})
 (root/'work/phase2/pc2-integration.json').write_text(json.dumps(rows,indent=2)+'\n')
 print(name+': '+str(result),flush=True)
 if q.returncode:raise SystemExit('Unexpected judgement; stopped before further tests')
