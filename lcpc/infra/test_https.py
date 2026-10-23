#!/usr/bin/env python3
"""Bounded five-team trial through TLS-verified participant proxy, no token output."""
from pathlib import Path
import json,ssl,urllib.request,urllib.error,base64,time,socket,os,concurrent.futures
from health import resources
ROOT=Path(__file__).resolve().parents[2];STATE=ROOT/'.local/instances/linux-trial'
assert json.loads((STATE/'mode.json').read_text())['mode']=='isolated-trial'
PROFILE=json.loads((STATE/'network/profile.json').read_text());BASE=PROFILE['origin'];CTX=ssl.create_default_context(cafile=str(STATE/'network/ca.crt'))
CREDS=dict(l.split('=',1) for l in (STATE/'credentials.properties').read_text().splitlines())
EVIDENCE={'profile':BASE,'checks':[],'teams':[],'resources':[]};SESSIONS=[]
def record(name,detail=True):EVIDENCE['checks'].append({'name':name,'passed':True,'detail':detail});print(name+': VERIFIED',flush=True)
def req(path,data=None,token=None,method=None,headers=None):
 h={'Content-Type':'application/json',**(headers or {})}
 if token:h['team_id']=token
 raw=None if data is None else json.dumps(data).encode()
 try:
  with urllib.request.urlopen(urllib.request.Request(BASE+path,data=raw,headers=h,method=method),context=CTX,timeout=15) as r:return r.status,r.read(),dict(r.headers)
 except urllib.error.HTTPError as e:return e.code,e.read(),dict(e.headers)
def api(path,**kw):
 status,raw,h=req('/api'+path,**kw)
 assert status==200,(path,status)
 return json.loads(raw) if raw else None

def websocket(token):
 s=CTX.wrap_socket(socket.create_connection(('127.0.0.1',8443),timeout=10),server_hostname='127.0.0.1')
 key=base64.b64encode(os.urandom(16)).decode()
 s.sendall(('GET /websocket/WTISocket/'+token+' HTTP/1.1\r\nHost: 127.0.0.1:8443\r\nOrigin: '+BASE+'\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Version: 13\r\nSec-WebSocket-Key: '+key+'\r\n\r\n').encode())
 buf=b''
 while b'\r\n\r\n' not in buf:buf+=s.recv(4096)
 assert buf.startswith(b'HTTP/1.1 101'),buf.split(b'\r\n')[0]
 return s,bytearray(buf.split(b'\r\n\r\n',1)[1])

def judged_event(connection,run_id):
 s,pending=connection;s.settimeout(5)
 def read(n):
  while len(pending)<n:
   chunk=s.recv(65536)
   if not chunk:raise RuntimeError('WebSocket closed before judged event')
   pending.extend(chunk)
  result=bytes(pending[:n]);del pending[:n];return result
 for _ in range(20):
  a,b=read(2);size=b&127
  if size==126:size=int.from_bytes(read(2),'big')
  elif size==127:size=int.from_bytes(read(8),'big')
  assert size<65536 and not b&128
  payload=read(size)
  if a&15==1:
   event=json.loads(payload)
   if event.get('type')=='judged' and event.get('id')==run_id:
    return {'type':'judged','run':run_id,'payload_bytes':len(payload)}
 raise RuntimeError('No matching judged event')

def team_trial(n):
 user='team'+str(n);start=time.monotonic();login=api('/teams/login',data={'teamName':user,'password':CREDS[user]});token=login['teamId'];SESSIONS.append(token)
 login_secs=time.monotonic()-start
 langs=api('/contest/languages',token=token);probs=api('/contest/problems',token=token)
 before={r['id'] for r in api('/teams/run',token=token)}
 ws=websocket(token) if n==1 else None
 start=time.monotonic()
 data={'probName':'Sum Two Integers','language':'GNU C++17 (Isolated Linux ARM64)','mainFile':{'fileName':'ac.cpp','byteData':base64.b64encode((ROOT/'lcpc/infra/tests/ac.cpp').read_bytes()).decode()},'extraFiles':[],'isTest':False,'osName':'Mac OS X'}
 api('/teams/run',data=data,token=token)
 deadline=time.monotonic()+90
 while time.monotonic()<deadline:
  new=[r for r in api('/teams/run',token=token) if r['id'] not in before and r['isFinal']]
  if new:
   r=new[-1];assert r['judgement']=='Yes',r['judgement'];break
  time.sleep(.5)
 else:raise RuntimeError('Judgement timeout')
 scores=api('/contest/scoreboard',token=token)
 if n==1:(ROOT/'work/phase2/https-scoreboard.json').write_text(json.dumps(scores))
 row={'team':user,'login_seconds':round(login_secs,3),'judge_seconds':round(time.monotonic()-start,3),'run':r['id'],'judgement':r['judgement'],'problems':len(probs),'languages':len(langs)}
 if ws:
  row['websocket_event']=judged_event(ws,r['id']);ws[0].close()
 return row
try:
 status,body,h=req('/');assert status==200 and b'<html' in body.lower();record('HTTPS certificate and participant page')
 status,body,h=req('/assets/appconfig.json');cfg=json.loads(body);assert cfg['baseUrl']==BASE+'/api' and cfg['websocketUrl'].startswith('wss://');record('HTTPS/WSS frontend configuration')
 assert req('/api/contest/problems')[0]==401;record('Unauthenticated REST denied')
 assert req('/api/contest/problems',token='invalid-token')[0]==401;record('Invalid token denied')
 assert req('/api/teams/login',data={'teamName':'administrator1','password':'invalid'})[0]==403;record('Administrator login denied on participant proxy')
 assert req('/api/teams/login',data={'teamName':'team2','password':'invalid'})[0]==401;record('Wrong team password denied')
 assert req('/',headers={'Origin':'https://untrusted.invalid'})[0]==403;record('Foreign Origin denied')
 assert req('/swagger.json')[0]==404;record('Swagger endpoint hidden')
 assert req('/websocket/WTISocket/server')[0]==403;record('Reserved internal WebSocket channel denied')
 r=resources();assert r['disk_free_gib']>=8 and (r['memory_free_percentage'] or 0)>=10;EVIDENCE['resources'].append(r)
 with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:EVIDENCE['teams']=list(pool.map(team_trial,range(1,6)))
 record('Five concurrent team logins, submissions, standings and WebSocket')
 EVIDENCE['resources'].append(resources())
finally:
 for token in SESSIONS:
  try:req('/api/teams/logout',token=token,method='DELETE')
  except Exception:pass
 (ROOT/'work/phase2/https-five-team-test.json').write_text(json.dumps(EVIDENCE,indent=2)+'\n')
