#!/usr/bin/env python3
"""Proves Linux Judge does not require WAN; does not disable the Mac Wi-Fi."""
from pathlib import Path
import sys,subprocess,json,time
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'lcpc/infra'));import vm
q=vm.guest(['ip','-j','route','show','default'],capture_output=True,text=True);routes=json.loads(q.stdout);assert len(routes)==1
r=routes[0];record={'guest_default_route_removed':False,'full_lan_wan_disconnection_tested':False}
try:
 vm.guest(['sudo','ip','route','del','default']);record['guest_default_route_removed']=True
 q=vm.guest(['ip','-j','route','show','default'],capture_output=True,text=True);assert not json.loads(q.stdout)
 start=time.monotonic()
 q=subprocess.run([sys.executable,str(ROOT/'lcpc/infra/test_https.py')],capture_output=True,text=True,timeout=120)
 (ROOT/'work/phase2/https-five-team-test.log').write_text(q.stdout+q.stderr)
 record['five_team_https_test_exit']=q.returncode;record['seconds']=round(time.monotonic()-start,3);assert q.returncode==0
finally:
 vm.guest(['sudo','ip','route','replace','default','via',r['gateway'],'dev',r['dev']])
 record['guest_route_restored']=True
 (ROOT/'work/phase2/offline-judge-test.json').write_text(json.dumps(record,indent=2)+'\n')
print('VERIFIED: Linux Judge and five-team HTTPS trial with guest WAN route disabled')
