#!/usr/bin/env python3
"""Real HTTPS refusal tests using an invalid token; no harmful file is submitted."""
from pathlib import Path
import json,base64,ssl,urllib.request,urllib.error,copy
ROOT=Path(__file__).resolve().parents[2];STATE=ROOT/'.local/instances/linux-trial'
ctx=ssl.create_default_context(cafile=str(STATE/'network/ca.crt'))
data={'probName':'Sum Two Integers','language':'GNU C++17 (Isolated Linux ARM64)','mainFile':{'fileName':'ac.cpp','byteData':base64.b64encode(b'int main(){}').decode()},'extraFiles':[],'isTest':False,'osName':'Mac OS X'}
rows=[]
def send(d,auth=True):
 h={'Content-Type':'application/json'}
 if auth:h['team_id']='11111111-1111-1111-1111-111111111111'
 try:
  with urllib.request.urlopen(urllib.request.Request('https://127.0.0.1:8443/api/teams/run',data=json.dumps(d).encode(),headers=h),context=ctx,timeout=10) as r:return r.status
 except urllib.error.HTTPError as e:return e.code
assert send(data)==401;assert send(data,False)==401
for name,value in [('parent traversal','../probe.cpp'),('absolute path','/tmp/probe.cpp'),('command characters','a;echo.cpp'),('hidden file','.profile.cpp')]:
 d=copy.deepcopy(data);d['mainFile']['fileName']=value;assert send(d)==400;rows.append({'test':name,'status':400})
for name,key,value in [('test run disabled','isTest',True),('unapproved language','language','shell'),('extra upload disabled','extraFiles',[{'fileName':'x','byteData':'eA=='}])]:
 d=copy.deepcopy(data);d[key]=value;assert send(d)==400;rows.append({'test':name,'status':400})
d=copy.deepcopy(data);d['mainFile']['byteData']=base64.b64encode(b'x'*(512*1024+1)).decode();assert send(d)==400;rows.append({'test':'source >512 KiB','status':400})
(ROOT/'work/phase2/upload-policy-test.json').write_text(json.dumps(rows,indent=2)+'\n')
print('VERIFIED: malformed, traversal, extra and oversized source uploads rejected before PC2')
