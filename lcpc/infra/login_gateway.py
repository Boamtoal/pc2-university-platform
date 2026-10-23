#!/usr/bin/env python3
"""Participant gateway and diagnostic collection. Never logs credentials or request bodies."""
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from http.cookies import SimpleCookie,CookieError
from pathlib import Path
from urllib.parse import urlsplit
import argparse,collections,json,os,re,secrets,signal,sys,threading,time,urllib.request,urllib.error
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from participant_policy import submission
from infra.submission_receipts import Receipts
from infra.participant_activity import ActivityStore,TOKEN,team,endpoint
from network import frontend_config
from participant_resources import catalog as resource_catalog,file_response
from infra.result_notifications import payload as result_payload
COOKIE='lcpc_team_session'
class Handler(BaseHTTPRequestHandler):
 protocol_version='HTTP/1.1'
 def log_message(self,*args):pass
 @property
 def config(self):return self.server.config
 @property
 def activity(self):return self.server.activity
 def limited(self,key,limit):
  now=time.monotonic()
  with self.server.rate_lock:
   for k in list(self.server.attempts):
    q=self.server.attempts[k]
    while q and q[0]<now-60:q.popleft()
    if not q:del self.server.attempts[k]
   if key not in self.server.attempts and len(self.server.attempts)>=1024:return True
   q=self.server.attempts[key]
   if len(q)>=limit:return True
   q.append(now);return False
 def begin(self):
  self.started=time.monotonic();self.request_id=secrets.token_hex(8);self.actor='';self.reported='';self.metadata={};self.path_only=urlsplit(self.path).path;self.peer=self.headers.get('X-LCPC-Peer',self.client_address[0]);self.connection.settimeout(10)
  try:self.actor=self.activity.identity(self.resource_token())
  except Exception:self.server.storage_warning()
 def audit(self,event,status,*,details=None,outcome=None):
  try:
   bad=status>=500;warn=status in (400,401,403,409,413,429)
   expected=status in (401,403) and not self.actor and self.path_only in ('/api/teams/resources-session','/api/teams/result-notifications');severity='info' if expected else 'error' if bad else 'warning' if warn else 'info';incident=bad or (event=='login' and status in (401,403))
   self.activity.record(event,login=self.actor,reported=self.reported,ip=self.peer,source='gateway',severity=severity,outcome=outcome or ('success' if status<400 else 'denied' if status<500 else 'failed'),request_id=self.request_id,details={'status':status,'method':self.command,'endpoint':endpoint(self.path_only),'durationMs':(time.monotonic()-self.started)*1000,'expected':expected,**self.metadata,**(details or {})},incident=incident)
  except Exception:self.server.storage_warning()
 def respond(self,status,raw,kind='application/json',headers=None,event=None,outcome=None):
  if event:self.audit(event,status,outcome=outcome)
  self.send_response(status)
  for key,value in {'Content-Type':kind,'Cache-Control':'no-store, private','Content-Length':str(len(raw)),'X-LCPC-Request-ID':self.request_id,'X-Content-Type-Options':'nosniff',**(headers or {})}.items():self.send_header(key,value)
  if status>=400:self.close_connection=True;self.send_header('Connection','close')
  if status==429:self.send_header('Retry-After','60')
  self.end_headers()
  try:
   if self.command!='HEAD':self.wfile.write(raw)
  except (BrokenPipeError,ConnectionResetError):self.audit('connection.delivery_failed',503)
 def cookie_header(self,token='',delete=False):
  value=COOKIE+'='+token+'; Path=/; HttpOnly; SameSite=Strict'+('; Max-Age=0' if delete else '')
  try:
   if json.loads((Path(self.config.state_tag)/'network/profile.json').read_text()).get('transport')=='https':value+='; Secure'
  except (OSError,ValueError):pass
  return value
 def resource_token(self):
  token=self.headers.get('team_id','')
  if not token:
   try:
    cookies=SimpleCookie();cookies.load(self.headers.get('Cookie',''));token=cookies[COOKIE].value if COOKIE in cookies else ''
   except CookieError:return ''
  return token if isinstance(token,str) and TOKEN.fullmatch(token) else ''
 def forward(self,body=None,method=None,headers=None,path=None,limit=4*1024*1024):
  target=path or self.path
  if not target.startswith('/') or target.startswith('//') or '\r' in target or '\n' in target:raise ValueError('Invalid backend path')
  req=urllib.request.Request('http://127.0.0.1:'+str(self.config.backend)+target,data=body,method=method or self.command,headers={'Content-Type':'application/json',**(headers or {})})
  try:
   with urllib.request.urlopen(req,timeout=10) as response:return response.status,response.read(limit+1),response.headers.get('Content-Type','application/json')
  except urllib.error.HTTPError as error:
   try:return error.code,error.read(min(limit,65536)),error.headers.get('Content-Type','application/json')
   finally:error.close()
 def validate_session(self,token):
  if not token:return 401
  try:return self.forward(method='GET',headers={'team_id':token},path='/api/teams/options',limit=65536)[0]
  except (OSError,urllib.error.URLError):return 503
 def read_json(self,maximum):
  if self.headers.get('Transfer-Encoding') or self.headers.get('Content-Type','').split(';')[0].strip()!='application/json':raise ValueError('Send bounded JSON')
  n=int(self.headers.get('Content-Length','0'))
  if not 0<n<=maximum:raise ValueError('Request size is outside policy')
  data=json.loads(self.rfile.read(n))
  if not isinstance(data,dict):raise ValueError('Expected an object')
  return data
 def resources(self):
  path=self.path_only;is_session=path=='/api/teams/resources-session';is_catalog=path=='/api/teams/resources';public=path in ('/instructions','/instructions/','/instructions/index.html');token=self.resource_token();status=200 if public else self.validate_session(token)
  outcome=None;headers={};kind='application/json';raw=b'{"error":"sign in required"}'
  if status!=200:
   outcome='denied'
   if status in (401,403):
    headers['Set-Cookie']=self.cookie_header(delete=True)
    if not is_session and not is_catalog:status=302;headers['Location']='/#/login';raw=b''
   else:status=503;raw=b'{"error":"session service unavailable; retry shortly"}'
  elif is_session:raw=b'{"authenticated":true}';headers['Set-Cookie']=self.cookie_header(token)
  elif is_catalog:
   data=resource_catalog(self.config.state_tag);status=200 if data is not None else 503;raw=json.dumps(data or {'error':'Resource catalog unavailable'}).encode()
  elif path.startswith('/problems/') and path not in ('/problems/','/problems/index.html'):
   result=file_response(self.config.state_tag,path,'download=1' in urlsplit(self.path).query)
   if result is not None:status,raw,kind,headers=result
   else:status=404;raw=b'{"error":"not found"}'
   match=re.fullmatch(r'/problems/files/([a-f0-9]{32})',path)
   if match:self.metadata['resourceId']=match[1]
   alias=re.fullmatch(r'/problems/([A-Z]{1,3})\.pdf',path)
   if alias:self.metadata['problem']=alias[1]
  elif not public and path not in ('/problems','/problems/','/problems/index.html'):
   status=404;raw=b'{"error":"not found"}'
  else:
   route='instructions' if public else 'problems';file=Path(self.config.state_tag)/'participant-resources'/route/'index.html'
   if file.is_file():kind='text/html; charset=utf-8';raw=file.read_bytes()
   else:status=404;raw=b'{"error":"not found"}'
  self.respond(status,raw,kind,headers,'resource.request',outcome)
 def do_HEAD(self):self.do_GET()
 def do_GET(self):
  self.begin()
  if self.path_only=='/api/teams/result-notifications':self.result_notifications();return
  if self.path_only in ('/problems','/instructions','/api/teams/resources-session','/api/teams/resources') or self.path_only.startswith(('/problems/','/instructions/')):
   if not self.server.slots.acquire(blocking=False):self.respond(503,b'{"error":"service busy"}',event='resource.request');return
   try:self.resources()
   except (OSError,ValueError):self.respond(503,b'{"error":"resource service unavailable"}',event='resource.request')
   finally:self.server.slots.release()
   return
  if self.path_only=='/assets/appconfig.json':
   try:profile=json.loads((Path(self.config.state_tag)/'network/profile.json').read_text());raw=json.dumps(frontend_config(profile,self.headers.get('Host',''))).encode();status=200
   except ValueError:status=403;raw=b'{"error":"unknown participant host"}'
   except (OSError,KeyError):status=503;raw=b'{"error":"network configuration unavailable"}'
   self.respond(status,raw,event='request.completed');return
  self.proxy()
 def result_notifications(self):
  token=self.resource_token()
  if not token:self.respond(401,b'{"error":"sign in required"}');return
  if urlsplit(self.path).query:self.respond(400,b'{"error":"result filters are not supported"}');return
  if not self.server.slots.acquire(blocking=False):self.respond(503,b'{"error":"service busy"}');return
  try:
   status,raw,_=self.forward(method='GET',headers={'team_id':token},path='/api/teams/run')
   if status!=200:self.respond(status,b'{"error":"participant result service unavailable"}');return
   if len(raw)>4*1024*1024:raise ValueError('Oversize result response')
   value=result_payload(self.config.state_tag,token,json.loads(raw));self.respond(200,json.dumps(value).encode())
  except (ValueError,TypeError,KeyError,UnicodeError):self.respond(502,b'{"error":"participant results unavailable"}')
  except (OSError,urllib.error.URLError):self.respond(503,b'{"error":"contest service unavailable"}')
  finally:self.server.slots.release()
 def do_DELETE(self):
  self.begin();self.proxy()
 def do_PUT(self):
  self.begin();self.proxy()
 def do_PATCH(self):
  self.begin();self.proxy()
 def do_OPTIONS(self):
  self.begin();self.proxy()
 def do_POST(self):
  self.begin()
  if self.path_only=='/api/teams/activity':self.telemetry();return
  self.proxy()
 def telemetry(self):
  try:
   profile=json.loads((Path(self.config.state_tag)/'network/profile.json').read_text());origins={o for o in [profile['origin'],profile.get('hostname_origin'),*profile.get('additional_origins',[])] if o}
   origin=self.headers.get('Origin','');host=self.headers.get('Host','')
   if origin not in origins or urlsplit(origin).netloc.lower()!=host.lower():self.respond(403,b'{"error":"same-origin diagnostics only"}');return
   if self.limited('activity:'+self.peer,90):self.respond(429,b'{"error":"diagnostic rate limit"}');return
   data=self.read_json(32768);token=self.resource_token()
   if token:
    status=self.validate_session(token)
    if status!=200:self.respond(status,b'{"error":"diagnostic session unavailable"}');return
   elif any(e.get('event') not in {'page.open','page.navigate','browser.error','browser.rejection','request.failed','action.clicked','form.submitted'} for e in data.get('events',[]) if isinstance(e,dict)):
    self.respond(401,b'{"error":"sign in for session diagnostics"}');return
   count=self.activity.telemetry(data,token,self.peer);self.respond(202,json.dumps({'ok':True,'accepted':count}).encode())
  except (ValueError,TypeError,KeyError,UnicodeError):self.respond(400,b'{"error":"invalid diagnostic metadata"}')
  except Exception:self.server.storage_warning();self.respond(503,b'{"error":"diagnostic storage unavailable"}')
 def proxy(self):
  path=self.path_only;event='login' if path=='/api/teams/login' else 'logout' if path=='/api/teams/logout' else 'submission.request' if path=='/api/teams/run' and self.command=='POST' else 'clarification.request' if path=='/api/teams/clarification' and self.command=='POST' else 'request.completed'
  if not path.startswith(('/api/teams/','/api/contest/','/api/contests/')) or path=='/api/teams/activity':self.respond(404,b'{"error":"not found"}');return
  if not self.server.slots.acquire(blocking=False):self.respond(503,b'{"error":"service busy"}',event=event);return
  token=self.resource_token();headers={'team_id':token} if token else {};out_headers={};status=400;raw=b'{"error":"invalid request"}';kind='application/json'
  try:
   if path in ('/api/teams/login','/api/teams/run') and self.command=='POST':
    if self.limited(('submit:' if path.endswith('/run') else 'login:')+self.peer,40 if path.endswith('/run') else 30):status=429;raw=b'{"error":"retry in 60 seconds"}'
    else:
     data=self.read_json(768*1024 if path.endswith('/run') else 4096)
     if path.endswith('/run'):
      if not token:status=401;raw=b'{"error":"sign in required"}'
      else:
       data=submission(data);self.metadata={'problem':data['probName'],'language':data['language'],'bytes':len(data['mainFile']['byteData'])*3//4};encoded=json.dumps(data,sort_keys=True,separators=(',',':')).encode();request_key=self.headers.get('Idempotency-Key','');receipt=None
       session_status=self.validate_session(token) if request_key else 200
       if session_status!=200:
        status=session_status if session_status in (401,403) else 503
        raw=b'{"error":"Sign in before submitting."}' if status in (401,403) else b'{"error":"Connection temporarily unavailable. Your session has been preserved; check My submissions before retrying."}'
       elif request_key:
        receipt,cached=self.server.receipts.claim(token,request_key,encoded)
        if cached:status,raw=cached
        else:
         status,raw,kind=self.forward(encoded,headers=headers);self.server.receipts.complete(receipt,status,raw)
       else:status,raw,kind=self.forward(encoded,headers=headers)
     else:
      self.reported=team(data.get('teamName'))
      if not self.reported or not isinstance(data.get('password'),str) or len(data['password'])>128:status=403;raw=b'{"error":"participant accounts only"}'
      elif not self.server.auth_lock.acquire(timeout=4):status=503;raw=b'{"error":"login busy"}'
      else:
       try:status,raw,kind=self.forward(json.dumps({'teamName':self.reported,'password':data['password']}).encode())
       finally:self.server.auth_lock.release()
       if status==200:
        result=json.loads(raw);newtoken=result.get('teamId','')
        if isinstance(newtoken,str) and TOKEN.fullmatch(newtoken):
         self.actor=self.reported
         try:self.activity.bind(newtoken,self.actor)
         except Exception:self.server.storage_warning()
         out_headers['Set-Cookie']=self.cookie_header(newtoken)
   else:
    body=None
    if self.command not in ('GET','HEAD','DELETE','OPTIONS'):
     n=int(self.headers.get('Content-Length','0'))
     if self.headers.get('Transfer-Encoding') or not 0<n<=2*1024*1024:raise ValueError('Invalid request length')
     body=self.rfile.read(n)
    status,raw,kind=self.forward(body,headers=headers)
   if len(raw)>4*1024*1024:status=502;raw=b'{"error":"backend response too large"}'
   if path=='/api/teams/logout' and self.command=='DELETE':
    out_headers['Set-Cookie']=self.cookie_header(delete=True)
    if status==200:
     try:self.activity.unbind(token)
     except Exception:self.server.storage_warning()
  except (ValueError,TypeError,KeyError,UnicodeError):status=400;raw=b'{"error":"invalid request; check file and submission settings"}'
  except (OSError,urllib.error.URLError):status=503;raw=b'{"error":"contest service unavailable; retry shortly"}'
  finally:self.server.slots.release()
  self.respond(status,raw,kind,out_headers,event)
class Server(ThreadingHTTPServer):
 daemon_threads=False;request_queue_size=16
 def __init__(self,address,config,activity=None):
  self.config=config;self.receipts=Receipts(config.state_tag);self.activity=activity or ActivityStore(config.state_tag);self.slots=threading.BoundedSemaphore(8);self.auth_lock=threading.Lock();self.rate_lock=threading.Lock();self.attempts=collections.defaultdict(collections.deque);self.last_warning=0;self.threads=threading.BoundedSemaphore(32);super().__init__(address,Handler)
 def process_request(self,request,address):
  if not self.threads.acquire(blocking=False):
   try:request.sendall(b'HTTP/1.1 503 Service Unavailable\r\nConnection: close\r\nContent-Length: 0\r\n\r\n')
   finally:self.shutdown_request(request)
   return
  try:super().process_request(request,address)
  except Exception:self.threads.release();raise
 def process_request_thread(self,request,address):
  try:super().process_request_thread(request,address)
  finally:self.threads.release()
 def storage_warning(self):
  if time.monotonic()-self.last_warning>60:self.last_warning=time.monotonic();print('Participant activity storage unavailable; contest requests remain enabled.',flush=True)
 def get_request(self):
  sock,addr=super().get_request();sock.settimeout(10);return sock,addr
 def handle_error(self,*_):print('Participant gateway request failed; no request body was logged.',flush=True)
def main():
 os.umask(0o077);parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8090);parser.add_argument('--backend',type=int,default=8080);parser.add_argument('--state-tag',required=True);args=parser.parse_args();server=Server(('127.0.0.1',args.port),args)
 def stop(*_):threading.Thread(target=server.shutdown,daemon=True).start()
 signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
 try:server.serve_forever(poll_interval=.2)
 finally:server.server_close()
if __name__=='__main__':main()
