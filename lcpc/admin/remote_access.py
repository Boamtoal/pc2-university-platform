"""Optional HTTPS administrator access, authorized per real peer IP and named user."""
import hashlib,ipaddress,json,ssl,subprocess,threading,time
from pathlib import Path
from core import require,stamp
from native_admin import reauth
from participant_access import local_addresses,NETWORKS

PORT=8092
def private_ip(value):
 try:address=ipaddress.ip_address(value)
 except (TypeError,ValueError):require(False,'Use one private IPv4 address, without a port or subnet')
 require(address.version==4 and any(address in n for n in NETWORKS),'Use one private LAN IPv4 address')
 return str(address)

class RemoteAccess:
 def __init__(self,app):
  self.app=app;self.server=None;self.thread=None;self.last_denied={};self.error=''
  with app.store.db() as db:db.executescript('''
  CREATE TABLE IF NOT EXISTS remote_grants(username TEXT NOT NULL,ip TEXT NOT NULL,created TEXT NOT NULL,expires REAL NOT NULL,PRIMARY KEY(username,ip));
  CREATE TABLE IF NOT EXISTS remote_attempts(ip TEXT PRIMARY KEY,first_seen TEXT NOT NULL,last_seen TEXT NOT NULL,count INTEGER NOT NULL);
  ''')
 def config(self):
  with self.app.store.db() as db:row=db.execute("SELECT value FROM settings WHERE key='remote.access'").fetchone()
  return json.loads(row[0]) if row else {'enabled':False,'bind':''}
 def save(self,config):
  with self.app.store.db() as db:db.execute("INSERT OR REPLACE INTO settings VALUES('remote.access',?)",(json.dumps(config),))
 @property
 def origin(self):return 'https://'+self.config()['bind']+':'+str(PORT)
 def permitted(self,ip,username=None):
  if not self.config()['enabled']:return False
  with self.app.store.db() as db:
   query='SELECT 1 FROM remote_grants g JOIN users u ON u.username=g.username WHERE g.ip=? AND g.expires>? AND u.enabled=1';args=[ip,time.time()]
   if username is not None:query+=' AND g.username=?';args.append(username)
   return bool(db.execute(query+' LIMIT 1',args).fetchone())
 def denied(self,ip):
  now=time.monotonic()
  if now-self.last_denied.get(ip,-1000)<60:return
  if len(self.last_denied)>512:self.last_denied={k:v for k,v in self.last_denied.items() if now-v<60}
  if len(self.last_denied)>512:return
  self.last_denied[ip]=now;created=stamp()
  with self.app.store.db() as db:
   db.execute('INSERT INTO remote_attempts VALUES(?,?,?,1) ON CONFLICT(ip) DO UPDATE SET last_seen=excluded.last_seen,count=count+1',(ip,created,created))
   db.execute('DELETE FROM remote_attempts WHERE ip NOT IN (SELECT ip FROM remote_attempts ORDER BY last_seen DESC LIMIT 256)')
  self.app.store.audit('anonymous','remote.ip-blocked','denied',ip,alert=('warning','Remote dashboard connection blocked for unapproved IP '+ip))
 def certificates(self,bind):
  directory=self.app.store.base/'remote-access';directory.mkdir(mode=0o700,exist_ok=True)
  ca=directory/'ca.crt';ca_key=directory/'ca.key';cert=directory/'server.crt';key=directory/'server.key';issued=directory/'issued.json'
  command='/opt/homebrew/bin/openssl' if Path('/opt/homebrew/bin/openssl').is_file() else '/usr/bin/openssl'
  def run(*args):subprocess.run([command,*args],check=True,capture_output=True,timeout=30)
  if not ca.exists():
   run('req','-new','-x509','-newkey','rsa:3072','-nodes','-days','3650','-subj','/CN=University Dashboard Private CA','-addext','basicConstraints=critical,CA:TRUE','-addext','keyUsage=critical,keyCertSign,cRLSign','-keyout',str(ca_key),'-out',str(ca))
  old=json.loads(issued.read_text()) if issued.exists() else {}
  if not cert.exists() or old.get('bind')!=bind or old.get('created',0)<time.time()-300*86400:
   run('req','-new','-newkey','rsa:2048','-nodes','-subj','/CN=University Organizer Dashboard','-keyout',str(key),'-out',str(directory/'server.csr'))
   (directory/'server.ext').write_text('subjectAltName=IP:'+str(ipaddress.ip_address(bind))+'\nextendedKeyUsage=serverAuth\nbasicConstraints=critical,CA:FALSE\nkeyUsage=digitalSignature,keyEncipherment\n')
   run('x509','-req','-in',str(directory/'server.csr'),'-CA',str(ca),'-CAkey',str(ca_key),'-CAcreateserial','-days','365','-extfile',str(directory/'server.ext'),'-out',str(cert))
   issued.write_text(json.dumps({'bind':bind,'created':time.time()}))
  for file in directory.iterdir():
   if file.is_file():file.chmod(0o600)
  ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);ctx.minimum_version=ssl.TLSVersion.TLSv1_2;ctx.options|=ssl.OP_NO_COMPRESSION;ctx.load_cert_chain(cert,key);return ctx
 def stop(self):
  server,self.server=self.server,None
  if server:server.shutdown();server.server_close();self.app.store.audit('system','remote.stopped','success')
  if self.thread:self.thread.join(timeout=5);self.thread=None
 def start(self):
  config=self.config()
  if not config['enabled']:return
  bind=private_ip(config['bind']);require(bind in {a['ip'] for a in local_addresses()},'The selected server IP is not assigned. Choose its current LAN address.',409)
  from server import Server
  server=Server((bind,PORT),self.app,remote=True,tls_context=self.certificates(bind));self.server=server
  self.thread=threading.Thread(target=lambda:server.serve_forever(poll_interval=.2),name='approved-admin-https',daemon=True);self.thread.start();self.error='';self.app.store.audit('system','remote.started','success',details={'bind':bind,'port':PORT})
 def configure(self,enabled,bind):
  require(type(enabled) is bool,'Choose whether remote access is enabled')
  if enabled:
   bind=private_ip(bind);require(bind in {a['ip'] for a in local_addresses()},'Choose a currently assigned server LAN address',409)
  old=self.config();new={'enabled':enabled,'bind':bind if enabled else old['bind']}
  self.stop();self.save(new)
  try:self.start()
  except Exception:
   self.save(old)
   try:self.start()
   except Exception:self.save({**old,'enabled':False});self.error='Remote listener unavailable. Local dashboard access remains available.'
   raise
  if not enabled:
   with self.app.store.db() as db:db.execute("DELETE FROM sessions WHERE channel='remote'")
 def view(self):
  config=self.config()
  with self.app.store.db() as db:
   grants=[dict(r) for r in db.execute('SELECT g.*,u.role,u.enabled FROM remote_grants g JOIN users u ON u.username=g.username ORDER BY g.expires DESC')]
   users=[dict(r) for r in db.execute('SELECT username,role,must_change FROM users WHERE enabled=1 ORDER BY username')]
   attempts=[dict(r) for r in db.execute('SELECT * FROM remote_attempts ORDER BY last_seen DESC LIMIT 50')]
  try:addresses=local_addresses()
  except Exception:addresses=[]
  ca=self.app.store.base/'remote-access/ca.crt'
  fingerprint=hashlib.sha256(ssl.PEM_cert_to_DER_cert(ca.read_text())).hexdigest().upper() if ca.exists() else None
  return {**config,'running':bool(self.server),'error':self.error,'url':self.origin+'/' if config['enabled'] else None,'port':PORT,'addresses':addresses,'grants':grants,'users':users,'attempts':attempts,'certificateAvailable':ca.exists(),'caFingerprint':':'.join(fingerprint[i:i+2] for i in range(0,len(fingerprint),2)) if fingerprint else None,'checkedAt':stamp()}

def route(handler,path,data=None):
 if not path.startswith('/api/remote-access'):return False
 handler.user('owner');require(not getattr(handler.server,'remote',False) and handler.client_address[0]=='127.0.0.1','Manage remote approvals only from the server computer.',403)
 remote=handler.app.remote;store=handler.app.store
 if data is None:
  if path=='/api/remote-access':handler.send(200,remote.view());return True
  require(path=='/api/remote-access/ca','Not found',404);ca=store.base/'remote-access/ca.crt';require(ca.is_file(),'Enable HTTPS remote access to generate its certificate first.',409)
  store.audit(handler.actor,'remote.ca-downloaded','success');handler.send(200,ca.read_bytes(),'application/x-pem-file',{'Content-Disposition':'attachment; filename="dashboard-private-ca.crt"'});return True
 handler.app.manager.guard(data);reauth(handler,data);require(data.get('confirm')=='CONFIRM','Confirmation required')
 if path=='/api/remote-access/configure':
  remote.configure(data.get('enabled'),data.get('bind',''));store.audit(handler.actor,'remote.configured','success',details={'enabled':remote.config()['enabled'],'bind':remote.config()['bind']},alert=('warning','Remote administrator HTTPS access was '+('enabled' if remote.config()['enabled'] else 'disabled')))
 elif path=='/api/remote-access/approve':
  ip=private_ip(data.get('ip'));username=data.get('username');require(isinstance(username,str) and 1<=len(username)<=64,'Choose a dashboard account');hours=data.get('hours',8);require(type(hours) is int and 1<=hours<=168,'IP approval lasts 1–168 hours')
  with store.db() as db:
   require(db.execute('SELECT 1 FROM users WHERE username=? AND enabled=1',(username,)).fetchone(),'Choose an enabled dashboard account')
   count=db.execute('SELECT count(*) FROM remote_grants WHERE expires>?',(time.time(),)).fetchone()[0];require(count<128,'Revoke an old IP approval before adding another',409)
   db.execute('INSERT OR REPLACE INTO remote_grants VALUES(?,?,?,?)',(username,ip,stamp(),time.time()+hours*3600))
  store.audit(handler.actor,'remote.ip-approved','success',details={'username':username,'ip':ip,'hours':hours},alert=('warning','Remote dashboard IP approved for '+str(username)+': '+ip))
 elif path=='/api/remote-access/revoke':
  ip=private_ip(data.get('ip'));username=data.get('username');require(isinstance(username,str) and 1<=len(username)<=64,'Choose a dashboard account')
  with store.db() as db:db.execute('DELETE FROM remote_grants WHERE username=? AND ip=?',(username,ip));db.execute("DELETE FROM sessions WHERE username=? AND peer=? AND channel='remote'",(username,ip))
  store.audit(handler.actor,'remote.ip-revoked','success',details={'username':username,'ip':ip})
 else:require(False,'Not found',404)
 handler.send(200,remote.view());return True
