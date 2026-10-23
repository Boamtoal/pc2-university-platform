"""Private dashboard storage, peer-bound authentication, audit trail and PC2 pipe."""
from pathlib import Path
import sys,base64,collections,contextlib,datetime,fcntl,hashlib,hmac,json,logging,logging.handlers,os,queue,re,secrets,sqlite3,struct,subprocess,threading,time,uuid,zipfile,io
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'lcpc'))
from runtime_paths import java_executable

class Error(Exception):
 def __init__(self,status,message):self.status=status;super().__init__(message)
def require(ok,message,status=400):
 if not ok:raise Error(status,message)
def stamp():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def digest(s):return hashlib.sha256(s.encode()).hexdigest()
def password_hash(password,salt=None):
 salt=salt or secrets.token_hex(16)
 value=hashlib.scrypt(password.encode(),salt=bytes.fromhex(salt),n=32768,r=8,p=1,maxmem=64*1024*1024).hex()
 return salt+'$'+value
def password_ok(password,encoded):
 try:return hmac.compare_digest(password_hash(password,encoded.split('$')[0]),encoded)
 except (ValueError,TypeError):return False
def password_policy(value):require(isinstance(value,str) and 16<=len(value)<=128,'Use a password of 16–128 characters')
def totp(secret,at=None):
 key=base64.b32decode(secret+'='*((8-len(secret)%8)%8));counter=int((time.time() if at is None else at)//30)
 raw=hmac.new(key,struct.pack('>Q',counter),hashlib.sha1).digest();offset=raw[-1]&15
 return str((int.from_bytes(raw[offset:offset+4],'big')&0x7fffffff)%1000000).zfill(6)

class Store:
 def __init__(self,state):
  self.state=Path(state).resolve();self.base=self.state/'admin-dashboard';self.base.mkdir(mode=0o700,exist_ok=True);self.uploads=self.base/'uploads';self.uploads.mkdir(mode=0o700,exist_ok=True)
  self.dbpath=self.base/'dashboard.sqlite3';self.lock=threading.RLock()
  keyfile=self.base/'audit.key'
  if not keyfile.exists():keyfile.write_bytes(secrets.token_bytes(32));keyfile.chmod(0o600)
  self.auditkey=keyfile.read_bytes()
  with self.db() as db:db.executescript('''
  CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT NOT NULL);
  CREATE TABLE IF NOT EXISTS users(username TEXT PRIMARY KEY,password TEXT NOT NULL,role TEXT NOT NULL,must_change INTEGER DEFAULT 1,totp TEXT DEFAULT '',pending_totp TEXT DEFAULT '',last_totp INTEGER DEFAULT 0,enabled INTEGER DEFAULT 1);
  CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,username TEXT NOT NULL,csrf TEXT NOT NULL,created REAL NOT NULL,seen REAL NOT NULL);
  CREATE TABLE IF NOT EXISTS failures(ip TEXT NOT NULL,created REAL NOT NULL);
  CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY AUTOINCREMENT,created TEXT NOT NULL,actor TEXT NOT NULL,event TEXT NOT NULL,outcome TEXT NOT NULL,ip TEXT NOT NULL,details TEXT NOT NULL,previous TEXT NOT NULL,signature TEXT NOT NULL);
  CREATE TABLE IF NOT EXISTS alerts(id INTEGER PRIMARY KEY AUTOINCREMENT,created TEXT NOT NULL,severity TEXT NOT NULL,message TEXT NOT NULL,acknowledged INTEGER DEFAULT 0);
  CREATE TABLE IF NOT EXISTS resources(id TEXT PRIMARY KEY,problem TEXT NOT NULL,kind TEXT NOT NULL,language TEXT NOT NULL,label TEXT NOT NULL,filename TEXT NOT NULL,mime TEXT NOT NULL,size INTEGER NOT NULL,sha256 TEXT NOT NULL,published INTEGER DEFAULT 0,deleted INTEGER DEFAULT 0,created TEXT NOT NULL,version INTEGER NOT NULL DEFAULT 1);
  ''')
  with self.db() as db:
   if 'pending_totp_created' not in [row[1] for row in db.execute('PRAGMA table_info(users)')]:db.execute('ALTER TABLE users ADD COLUMN pending_totp_created REAL DEFAULT 0')
   columns={row[1] for row in db.execute('PRAGMA table_info(sessions)')}
   if 'peer' not in columns:db.execute("ALTER TABLE sessions ADD COLUMN peer TEXT NOT NULL DEFAULT '127.0.0.1'")
   if 'channel' not in columns:db.execute("ALTER TABLE sessions ADD COLUMN channel TEXT NOT NULL DEFAULT 'local'")
  self.dbpath.chmod(0o600)
  self.logger=logging.getLogger('dashboard.'+str(self.base));self.logger.setLevel(logging.INFO);self.logger.propagate=False
  if not self.logger.handlers:
   handler=logging.handlers.RotatingFileHandler(self.base/'audit.jsonl',maxBytes=5*1024*1024,backupCount=10);handler.setFormatter(logging.Formatter('%(message)s'));self.logger.addHandler(handler)
  self.boot=time.time()
 @contextlib.contextmanager
 def db(self):
  connection=sqlite3.connect(self.dbpath,timeout=15);connection.row_factory=sqlite3.Row
  try:
   connection.execute('PRAGMA journal_mode=WAL')
   with connection:yield connection
  finally:connection.close()
 def schedule_preferences(self):
  with self.db() as db:row=db.execute("SELECT value FROM settings WHERE key='schedule.preferences'").fetchone()
  return json.loads(row[0]) if row else {'country':'LY','timeZone':'Africa/Tripoli'}
 def save_schedule_preferences(self,preferences):
  with self.db() as db:db.execute("INSERT INTO settings(key,value) VALUES('schedule.preferences',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(json.dumps(preferences),))
 def initialize(self):
  with self.db() as db:
   if db.execute('SELECT 1 FROM users LIMIT 1').fetchone():return None
   password=secrets.token_urlsafe(24);db.execute('INSERT INTO users(username,password,role) VALUES(?,?,?)',('admin',password_hash(password),'owner'))
  credential=self.base/'INITIAL-LOGIN.txt';credential.write_text('University Dashboard\nURL: http://127.0.0.1:8091/\nUsername: admin\nTemporary password: '+password+'\nChange this password at first sign-in. This file is deleted after the change.\n');credential.chmod(0o600)
  self.audit('system','initialized','success',details={'scope':'loopback only'});return credential
 def audit(self,actor,event,outcome,ip='local',details=None,alert=None):
  # Only explicit metadata is accepted. Passwords, tokens and code are never audit fields.
  payload={'created':stamp(),'actor':actor[:64],'event':event[:80],'outcome':outcome[:40],'ip':ip[:64],'details':details or {}}
  with self.lock,self.db() as db:
   row=db.execute('SELECT signature FROM audit ORDER BY id DESC LIMIT 1').fetchone();previous=row[0] if row else '0'*64
   encoded=json.dumps(payload,sort_keys=True,separators=(',',':'),ensure_ascii=True)
   signature=hmac.new(self.auditkey,(previous+encoded).encode(),hashlib.sha256).hexdigest()
   db.execute('INSERT INTO audit(created,actor,event,outcome,ip,details,previous,signature) VALUES(?,?,?,?,?,?,?,?)',(payload['created'],payload['actor'],payload['event'],payload['outcome'],payload['ip'],json.dumps(payload['details'],sort_keys=True),previous,signature))
   if alert:db.execute('INSERT INTO alerts(created,severity,message) VALUES(?,?,?)',(payload['created'],alert[0],alert[1][:1000]))
  self.logger.info(json.dumps({**payload,'previous':previous,'signature':signature},ensure_ascii=True))
 def verify_audit(self):
  previous='0'*64;count=0
  with self.db() as db:
   for row in db.execute('SELECT * FROM audit ORDER BY id'):
    payload={k:row[k] for k in ('created','actor','event','outcome','ip')};payload['details']=json.loads(row['details'])
    sig=hmac.new(self.auditkey,(previous+json.dumps(payload,sort_keys=True,separators=(',',':'),ensure_ascii=True)).encode(),hashlib.sha256).hexdigest()
    if row['previous']!=previous or not hmac.compare_digest(row['signature'],sig):return {'valid':False,'row':row['id']}
    previous=sig;count+=1
  return {'valid':True,'entries':count}
 def login(self,username,password,code,ip,channel='local'):
  now=time.time()
  require(isinstance(username,str) and len(username)<=64 and isinstance(password,str) and len(password)<=128,'Invalid credentials',401)
  with self.db() as db:
   db.execute('DELETE FROM failures WHERE created<?',(now-900,));failures=db.execute('SELECT count(*) FROM failures WHERE ip=?',(ip,)).fetchone()[0]
   require(failures<10,'Too many attempts. Retry after 15 minutes.',429)
   user=db.execute('SELECT * FROM users WHERE username=? AND enabled=1',(username,)).fetchone()
   # Dummy hash makes unknown-user attempts perform the same expensive operation.
   encoded=user['password'] if user else '0'*32+'$'+'0'*128
   valid=password_ok(password,encoded)
   counter=0
   if user and user['totp']:
    valid_codes=[int(now//30)+offset for offset in (-1,0,1)]
    counter=next((step for step in valid_codes if hmac.compare_digest(totp(user['totp'],step*30),str(code)) and step>user['last_totp']),0)
    valid=valid and bool(counter)
   if not valid or not user:
    db.execute('INSERT INTO failures VALUES(?,?)',(ip,now));db.commit()
    self.audit(username,'login','denied',ip,alert=('warning','Failed administrator login'+(' — repeated attempts' if failures>=4 else '')))
    raise Error(401,'Invalid credentials or verification code')
   db.execute('DELETE FROM failures WHERE ip=?',(ip,));db.execute('DELETE FROM sessions WHERE seen<? OR created<?',(now-1800,now-28800))
   if counter:db.execute('UPDATE users SET last_totp=? WHERE username=?',(counter,username))
   token=secrets.token_urlsafe(40);csrf=secrets.token_urlsafe(32)
   db.execute('INSERT INTO sessions(token,username,csrf,created,seen,peer,channel) VALUES(?,?,?,?,?,?,?)',(digest(token),username,csrf,now,now,ip,channel))
  self.audit(username,'login','success',ip);return token,dict(user),csrf
 def session(self,token,ip=None,channel=None):
  if not token:return None
  now=time.time()
  with self.db() as db:
   row=db.execute('SELECT s.*,u.role,u.must_change,u.enabled,u.totp FROM sessions s JOIN users u USING(username) WHERE token=?',(digest(token),)).fetchone()
   if not row or not row['enabled'] or row['seen']<now-1800 or row['created']<now-28800:
    db.execute('DELETE FROM sessions WHERE token=?',(digest(token),));return None
   if (ip is not None and row['peer']!=ip) or (channel is not None and row['channel']!=channel):return None
   db.execute('UPDATE sessions SET seen=? WHERE token=?',(now,digest(token)))
  return dict(row)
 def change_password(self,user,current,new,code=''):
  password_policy(new)
  with self.db() as db:
   row=db.execute('SELECT * FROM users WHERE username=?',(user,)).fetchone();require(password_ok(current,row['password']),'Current password is incorrect',403)
   require(not row['totp'] or any(hmac.compare_digest(totp(row['totp'],time.time()+offset*30),str(code)) for offset in (-1,0,1)),'A valid authenticator code is required',403)
   require(not password_ok(new,row['password']),'Choose a different password')
   db.execute('UPDATE users SET password=?,must_change=0 WHERE username=?',(password_hash(new),user));db.execute('DELETE FROM sessions WHERE username=?',(user,))
  if user=='admin':(self.base/'INITIAL-LOGIN.txt').unlink(missing_ok=True)
 def resources(self,deleted=False):
  with self.db() as db:return [dict(row) for row in db.execute('SELECT * FROM resources WHERE deleted=? ORDER BY created DESC',(int(deleted),))]
 def upload(self,data,*,trusted=False):
  problem=data.get('problem');kind=data.get('kind');language=data.get('language','none');label=str(data.get('label','')).strip();filename=str(data.get('filename',''))
  require(isinstance(problem,str) and 1<=len(problem)<=240,'Choose a problem')
  require(kind in ('statement','helper','booklet'),'Invalid resource kind');require(language in ('en','ar','both','none'),'Invalid resource language')
  require(1<=len(label)<=200,'Use a resource label of 1–200 characters');require(1<=len(filename)<=150 and filename==Path(filename).name and not re.search(r'[\x00-\x1f\x7f/\\]',filename),'Invalid filename')
  try:body=base64.b64decode(data['base64'],validate=True)
  except (KeyError,ValueError):raise Error(400,'Invalid upload encoding')
  require(0<len(body)<=20*1024*1024,'Upload one file up to 20 MiB')
  with self.db() as db:stored_bytes=db.execute('SELECT COALESCE(sum(size),0) FROM resources').fetchone()[0]
  require(stored_bytes+len(body)<=1024*1024*1024,'The retained resource storage exceeds its 1 GiB quota')
  extension=Path(filename).suffix.lower();types={'.pdf':'application/pdf','.txt':'text/plain','.csv':'text/csv','.json':'application/json','.zip':'application/zip','.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg'}
  require(extension in types,'Allowed files: PDF, TXT, CSV, JSON, ZIP, PNG and JPG')
  if kind in ('statement','booklet'):
   require(extension=='.pdf','Statements and booklets must be PDF files');require(language in ('en','ar','both'),'Choose a statement language')
  if extension=='.pdf':
   require(body.startswith(b'%PDF-') and b'%%EOF' in body[-4096:],'Invalid PDF file')
   names=re.sub(rb'#([0-9a-fA-F]{2})',lambda m:bytes([int(m[1],16)]),body)
   require(trusted or not re.search(rb'/(JavaScript|JS|Launch|EmbeddedFile|RichMedia|OpenAction|XFA)\b',names),'PDF contains active or embedded content; export a plain PDF')
  if extension=='.png':require(body.startswith(b'\x89PNG\r\n\x1a\n'),'Invalid PNG')
  if extension in ('.jpg','.jpeg'):require(body.startswith(b'\xff\xd8\xff'),'Invalid JPEG')
  if extension=='.zip':
   try:
    with zipfile.ZipFile(io.BytesIO(body)) as archive:
     require(len(archive.infolist())<=200,'ZIP has too many files');total=0
     for item in archive.infolist():
      total+=item.file_size
      require(not item.filename.startswith(('/','\\')) and '..' not in Path(item.filename.replace('\\','/')).parts and not (item.flag_bits&1),'Unsafe or encrypted ZIP entry')
      require(item.is_dir() or Path(item.filename).suffix.lower() in ('.txt','.in','.ans','.out','.csv','.json','.pdf','.png','.jpg','.jpeg'),'ZIP contains an unsupported file type')
      require(total<=50*1024*1024,'ZIP expands beyond 50 MiB')
   except zipfile.BadZipFile:raise Error(400,'Invalid ZIP')
  rid=uuid.uuid4().hex;target=self.uploads/rid;target.write_bytes(body);target.chmod(0o600)
  with self.db() as db:
   version=db.execute('SELECT COALESCE(max(version),0)+1 FROM resources WHERE problem=? AND kind=? AND language=?',(problem,kind,language)).fetchone()[0]
   db.execute('INSERT INTO resources(id,problem,kind,language,label,filename,mime,size,sha256,created,version) VALUES(?,?,?,?,?,?,?,?,?,?,?)',(rid,problem,kind,language,label,filename,types[extension],len(body),hashlib.sha256(body).hexdigest(),stamp(),version))
  return rid
 def publish_catalog(self,snapshot):
  allfiles=self.resources();problems=[]
  for problem in snapshot.get('problems',[]):
   if not problem.get('active',True):continue
   files=[{key:row[key] for key in ('id','kind','language','label','filename','mime','size','sha256','version')} for row in allfiles if row['problem']==problem['id'] and row['published']]
   problems.append({**problem,'resources':files})
  booklets=[{key:row[key] for key in ('id','kind','language','label','filename','mime','size','sha256','version')} for row in allfiles if row['problem']=='__contest__' and row['published']]
  catalog={'updatedAt':stamp(),'problems':problems,'booklets':booklets};target=self.state/'participant-resources/catalog.json';target.parent.mkdir(exist_ok=True)
  temp=target.with_name('catalog.'+uuid.uuid4().hex+'.tmp');temp.write_text(json.dumps(catalog,ensure_ascii=False));temp.chmod(0o600);temp.replace(target)
  return catalog

class Bridge:
 def __init__(self,state):self.state=Path(state);self.lock=threading.RLock();self.process=None;self.responses=queue.Queue();self.cached=None;self.cached_at=0
 def command_line(self,mode):
  return [java_executable(),'-Djdk.crypto.KeyAgreement.legacyKDF=true','-Djava.awt.headless=true','-Dlcpc.denyExecution=true','-Dlcpc.secrets='+str(self.state/'credentials.properties'),'-javaagent:'+str(ROOT/'lcpc/build/local-only-agent.jar'),'-cp',str(ROOT/'lcpc/build')+':'+str(ROOT/'lib/*')+':'+str(self.state/'wti/WebTeamInterface-1.1.jar'),'DashboardBridge',mode,str(self.state/'admin-dashboard/bridge.properties')]
 def start(self):
  if self.process and self.process.poll() is None:return
  self.account_lock=(self.state/'admin-dashboard/bridge-client.lock').open('a')
  try:fcntl.flock(self.account_lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:raise Error(503,'Another dashboard bridge is already connected')
  self.responses=queue.Queue();work=self.state/'admin-dashboard/bridge';work.mkdir(mode=0o700,exist_ok=True)
  ini=work/'pc2v9.ini';ini.write_text('[client]\nserver=127.0.0.1:50002\n')
  self.log=(self.state/'admin-dashboard/bridge.log').open('ab')
  self.process=subprocess.Popen(self.command_line('serve'),cwd=work,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.log,text=True,bufsize=1)
  proc=self.process
  def read():
   for line in proc.stdout:
    if line.startswith('LCPC_JSON '):
     try:self.responses.put(json.loads(line[10:]))
     except ValueError:pass
   self.responses.put({'ready':False,'error':'PC2 bridge disconnected'})
  threading.Thread(target=read,daemon=True).start()
  try:message=self.responses.get(timeout=25)
  except queue.Empty:proc.terminate();raise Error(503,'PC2 connection timed out')
  require(message.get('ready'),'PC2 service connection unavailable',503)
 def call(self,op,args=None):
  with self.lock:
   self.start();request=uuid.uuid4().hex
   self.process.stdin.write(json.dumps({'id':request,'op':op,'args':args or {}})+'\n');self.process.stdin.flush()
   end=time.monotonic()+30
   while time.monotonic()<end:
    try:result=self.responses.get(timeout=max(.1,end-time.monotonic()))
    except queue.Empty:break
    if result.get('id')!=request:continue
    if not result.get('ok'):
     message=result.get('error','PC2 operation failed')
     if 'NotLoggedIn' in message:self.process.terminate()
     raise Error(409,message)
    if op!='snapshot':self.cached_at=0
    return result['data']
   self.process.terminate();raise Error(503,'PC2 did not confirm the operation; check state before retrying')
 def snapshot(self,fresh=False):
  with self.lock:
   if not fresh and self.cached and time.time()-self.cached_at<3:return self.cached
   self.cached=self.call('snapshot');self.cached_at=time.time();return self.cached
 def close(self):
  if self.process and self.process.poll() is None:
   self.process.terminate()
   try:self.process.wait(timeout=8)
   except subprocess.TimeoutExpired:pass
  if hasattr(self,'account_lock'):self.account_lock.close()

def prepare_judge_data(store,encoded):
 """Extract only paired plain .in/.ans tests into a new private directory."""
 try:body=base64.b64decode(encoded,validate=True)
 except (ValueError,TypeError):raise Error(400,'Invalid test archive encoding')
 require(0<len(body)<=20*1024*1024,'Test archive must be at most 20 MiB')
 pairs={};total=0
 try:
  with zipfile.ZipFile(io.BytesIO(body)) as archive:
   require(2<=len(archive.infolist())<=1000,'Use an archive with 1–250 test pairs')
   for item in archive.infolist():
    if item.is_dir():continue
    path=Path(item.filename.replace('\\','/'))
    require(not path.is_absolute() and '..' not in path.parts and not(item.flag_bits&1) and ((item.external_attr>>16)&0o170000)!=0o120000,'Unsafe ZIP entry')
    require(path.suffix in ('.in','.ans'),'Judge archive accepts .in and .ans files only')
    total+=item.file_size;require(total<=50*1024*1024,'Test data exceeds 50 MiB')
    key=str(path.with_suffix(''));pair=pairs.setdefault(key,{})
    require(path.suffix not in pair,'Duplicate test filename');pair[path.suffix]=archive.read(item)
 except (zipfile.BadZipFile,RuntimeError):raise Error(400,'Invalid test archive')
 require(1<=len(pairs)<=250 and all(set(pair)=={'.in','.ans'} for pair in pairs.values()),'Every input needs a matching .ans file with the same name')
 directory=store.base/'judge-data'/uuid.uuid4().hex;directory.mkdir(mode=0o700,parents=True)
 for index,key in enumerate(sorted(pairs)):
  for suffix,content in pairs[key].items():
   file=directory/(str(index+1).zfill(4)+suffix);file.write_bytes(content);file.chmod(0o600)
 return directory
