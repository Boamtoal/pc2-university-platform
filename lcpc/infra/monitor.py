#!/usr/bin/env python3
"""Bounded monitor: sample resources and service state, never mutate contest state."""
import sys,time,json,subprocess,os
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from infra.health import resources
root=Path(__file__).resolve().parents[2]
count=int(sys.argv[1]) if len(sys.argv)>1 else 12
interval=float(sys.argv[2]) if len(sys.argv)>2 else 5
if not 1<=count<=720 or not 1<=interval<=60:raise SystemExit('Bounds: 1..720 samples, 1..60 second interval')
for i in range(count):
 r=resources();r['timestamp']=time.time()
 q=subprocess.run(['ps','-axo','pid=,%cpu=,rss=,comm='],capture_output=True,text=True)
 r['processes']=[l.strip() for l in q.stdout.splitlines() if any(s in l for s in ['java','lima','caddy'])]
 r['safe']=r['disk_free_gib']>=8 and (r['memory_free_percentage'] or 0)>=10
 print(json.dumps(r),flush=True)
 if not r['safe']:raise SystemExit('Resource threshold reached; monitor stopped, no services killed')
 if i+1<count:time.sleep(interval)
