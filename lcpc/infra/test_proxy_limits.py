#!/usr/bin/env python3
from pathlib import Path
import sys,os,ssl,json,urllib.request,urllib.error,time
ROOT=Path(__file__).resolve().parents[2];os.environ['LCPC_STATE_DIR']=str(ROOT/'.local/instances/linux-trial');sys.path.insert(0,str(ROOT/'lcpc'))
import pc2ctl as ctl
from infra import network
ctx=ssl.create_default_context(cafile=str(ctl.LOCAL/'network/ca.crt'));url='https://127.0.0.1:8443'
rows=[]
def req(path='/',data=None):
 try:
  with urllib.request.urlopen(urllib.request.Request(url+path,data=None if data is None else json.dumps(data).encode(),headers={'Content-Type':'application/json'}),context=ctx,timeout=8) as r:return r.status,dict(r.headers)
 except urllib.error.HTTPError as e:return e.code,dict(e.headers)
code,h=req();assert code==200
for name in ['X-Content-Type-Options','Referrer-Policy','X-Frame-Options']:assert name.lower() in [k.lower() for k in h]
rows.append({'test':'response security headers','verified':True})
assert req('/api/teams/login',{'teamName':'team1','password':'x'*5000})[0]==413
rows.append({'test':'oversize login body rejected','status':413})
codes=[req('/api/teams/login',{'teamName':'administrator1','password':'invalid'})[0] for _ in range(31)]
assert 429 in codes;rows.append({'test':'login limit 30 attempts per IP per minute','status_counts':{str(n):codes.count(n) for n in set(codes)}})
f=ctl.LOCAL/'network/Caddyfile';original=f.read_text()
try:
 network.stop(ctl);time.sleep(.3)
 changed=original.replace('remote_ip 127.0.0.1/32','remote_ip 127.0.0.2/32');assert changed!=original
 f.write_text(changed);network.start(ctl)
 for path in ['/','/assets/appconfig.json','/api/teams/login','/websocket/WTISocket/invalid']:
  assert req(path)[0]==403
 rows.append({'test':'CIDR deny precedes all participant routes','verified':True})
finally:
 network.stop(ctl);time.sleep(.3);f.write_text(original);network.start(ctl)
 (ROOT/'work/phase2/proxy-limits-test.json').write_text(json.dumps(rows,indent=2)+'\n')
print('VERIFIED: headers, body cap, login throttling and CIDR route denial')
