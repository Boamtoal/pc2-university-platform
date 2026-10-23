"""Contest-local participant diagnostics. No request bodies, passwords or tokens in events."""
from pathlib import Path
from contextlib import contextmanager
import datetime,hashlib,hmac,ipaddress,json,os,re,secrets,sqlite3,time
from infra import connection_history
TEAM=re.compile(r'team[1-9][0-9]{0,4}')
TOKEN=re.compile(r'[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}')
CLIENT=re.compile(r'[a-f0-9]{16,32}')
SOURCES={'gateway','browser','pc2','observer','organizer'}
SEVERITIES={'info','warning','error'}
BROWSER_EVENTS={'page.open','page.navigate','page.visibility','page.close','session.restored','network.offline','network.online','browser.error','browser.rejection','request.completed','request.failed','socket.open','socket.close','socket.error','file.selected','action.clicked','form.submitted','heartbeat'}
ACTIONS={'login','logout','submit','submit_problem','clarification','save','clear_filters','download','unknown'}
PAGES={'login','runs','clarifications','options','scoreboard','resources','instructions','unknown'}
ENDPOINTS={'login','logout','runs','clarifications','options','resources','resource_session','result_notifications','problems','languages','judgements','clock','config','activity','other'}
def stamp(at=None):return datetime.datetime.fromtimestamp(time.time() if at is None else at,datetime.timezone.utc).isoformat()
def text(value,limit=200):return ''.join(c for c in str(value or '') if ord(c)>=32 and ord(c)!=127)[:limit]
def team(value):return value if isinstance(value,str) and TEAM.fullmatch(value) else ''
def peer(value):
 try:return str(ipaddress.ip_address(value))
 except ValueError:return ''
def endpoint(path):
 from urllib.parse import urlsplit
 p=urlsplit(path).path.rstrip('/')
 known={'/api/teams/login':'login','/api/teams/logout':'logout','/api/teams/run':'runs','/api/teams/clarification':'clarifications','/api/teams/options':'options','/api/teams/resources':'resources','/api/teams/resources-session':'resource_session','/api/teams/result-notifications':'result_notifications','/api/teams/activity':'activity','/assets/appconfig.json':'config'}
 if p in known:return known[p]
 if p.startswith('/problems'):return 'resources'
 if p.startswith('/instructions'):return 'resources'
 for name in ('problems','languages','judgements','clarifications'):
  if p in ('/api/contests/'+name,'/api/contest/'+name):return name
 if 'clock' in p.lower() or p.endswith('/isContestRunning'):return 'clock'
 return 'other'
def safe_details(data):
 """Closed schema. Arbitrary error strings, URLs, headers and body fields never pass."""
 out={}
 for key in ('status','durationMs','line','column','closeCode','fileCount','bytes','number','site','elapsedMinutes','count'):
  v=data.get(key)
  if type(v) in (int,float) and -1<=v<=100000000:
   if key=='status' and not 0<=v<=599:continue
   if key=='closeCode' and not 0<=v<=4999:continue
   out[key]=round(v,2)
 for key,choices in {'endpoint':ENDPOINTS,'page':PAGES,'action':ACTIONS,'errorType':{'Error','TypeError','ReferenceError','SyntaxError','RangeError','URIError','EvalError','ResourceError','Unknown'},'method':{'GET','HEAD','POST','DELETE','PUT','PATCH'},'visibility':{'visible','hidden'},'platform':{'Windows','macOS','Linux','Android','iOS','Other'},'browser':{'Chrome','Edge','Firefox','Safari','Other'},'extension':{'.cpp','.cc','.c','.py','.java','other'}}.items():
  if isinstance(data.get(key),str) and data[key] in choices:out[key]=data[key]
 for key in ('expected','historical','final','accepted','deleted','answered','all','online','normalClose','correlated'):
  if type(data.get(key)) is bool:out[key]=data[key]
 if isinstance(data.get('resourceId'),str) and re.fullmatch('[a-f0-9]{32}',data['resourceId']):out['resourceId']=data['resourceId']
 if isinstance(data.get('script'),str) and re.fullmatch(r'[A-Za-z0-9_.-]{1,100}\.js',data['script']):out['script']=data['script']
 # These fields originate only in PC2, never in browser telemetry.
 for key in ('problem','language','verdict','automaticVerdict','workflowState'):
  if key in data:out[key]=text(data[key],200)
 if isinstance(data.get('clientAt'),str):
  try:data={**data,'clientAt':datetime.datetime.fromisoformat(data['clientAt']).timestamp()}
  except ValueError:pass
 if isinstance(data.get('clientAt'),(int,float)) and abs(time.time()-data['clientAt'])<=86400:out['clientAt']=stamp(data['clientAt'])
 return out
class ActivityStore:
 RETAIN_SECONDS=30*86400
 MAX_EVENTS=200000
 def __init__(self,state):
  self.state=Path(state).resolve();self.base=self.state/'participant-activity';self.base.mkdir(mode=0o700,parents=True,exist_ok=True);self.base.chmod(0o700);self.path=self.base/'activity.sqlite3'
  key=self.base/'signing.key'
  try:
   fd=os.open(key,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
   with os.fdopen(fd,'wb') as f:f.write(secrets.token_bytes(32))
  except FileExistsError:pass
  self.key=key.read_bytes()
  if len(self.key)!=32:raise ValueError('Invalid activity signing key')
  with self.db() as db:db.executescript('''
   CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT NOT NULL);
   CREATE TABLE IF NOT EXISTS identities(token_hash TEXT PRIMARY KEY,team TEXT NOT NULL,created REAL NOT NULL);
   CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY AUTOINCREMENT,at REAL NOT NULL,created TEXT NOT NULL,team TEXT NOT NULL,reported_team TEXT NOT NULL,ip TEXT NOT NULL,source TEXT NOT NULL,event TEXT NOT NULL,severity TEXT NOT NULL,outcome TEXT NOT NULL,request_id TEXT NOT NULL,client TEXT NOT NULL,details TEXT NOT NULL,previous TEXT NOT NULL,signature TEXT NOT NULL);
   CREATE INDEX IF NOT EXISTS event_team ON events(team,id);
   CREATE INDEX IF NOT EXISTS event_created ON events(at);
   CREATE INDEX IF NOT EXISTS event_request ON events(request_id);
   CREATE TABLE IF NOT EXISTS issues(id INTEGER PRIMARY KEY AUTOINCREMENT,issue_key TEXT UNIQUE NOT NULL,team TEXT NOT NULL,reported_team TEXT NOT NULL,ip TEXT NOT NULL,source TEXT NOT NULL,event TEXT NOT NULL,severity TEXT NOT NULL,first_at REAL NOT NULL,last_at REAL NOT NULL,count INTEGER NOT NULL,state TEXT NOT NULL,event_id INTEGER NOT NULL,actor TEXT NOT NULL DEFAULT '');
   CREATE TABLE IF NOT EXISTS clients(client TEXT PRIMARY KEY,team TEXT NOT NULL,reported_team TEXT NOT NULL,ip TEXT NOT NULL,last_seen REAL NOT NULL,page TEXT NOT NULL,platform TEXT NOT NULL,browser TEXT NOT NULL,closed INTEGER NOT NULL DEFAULT 0,gap INTEGER NOT NULL DEFAULT 0);
   CREATE TABLE IF NOT EXISTS observed(entity TEXT PRIMARY KEY,fingerprint TEXT NOT NULL);
  ''')
  with self.db() as db:
   if 'session_hash' not in [r[1] for r in db.execute('PRAGMA table_info(clients)')]:db.execute("ALTER TABLE clients ADD COLUMN session_hash TEXT NOT NULL DEFAULT ''")
  self.path.chmod(0o600);connection_history.migrate(self)
 @contextmanager
 def db(self):
  db=sqlite3.connect(self.path,timeout=2);db.row_factory=sqlite3.Row
  try:
   db.execute('PRAGMA journal_mode=WAL')
   with db:yield db
  finally:db.close()
 def token_hash(self,token):return hmac.new(self.key,token.encode(),hashlib.sha256).hexdigest() if isinstance(token,str) and TOKEN.fullmatch(token) else ''
 def bind(self,token,login):
  hashed=self.token_hash(token);login=team(login)
  if not hashed or not login:return
  with self.db() as db:db.execute('INSERT OR REPLACE INTO identities VALUES(?,?,?)',(hashed,login,time.time()))
 def identity(self,token):
  with self.db() as db:row=db.execute('SELECT team FROM identities WHERE token_hash=?',(self.token_hash(token),)).fetchone()
  return row[0] if row else ''
 def unbind(self,token):
  with self.db() as db:
   keys=[r[0] for r in db.execute('SELECT client FROM clients WHERE session_hash=?',(self.token_hash(token),))];db.execute('DELETE FROM identities WHERE token_hash=?',(self.token_hash(token),));db.execute('UPDATE clients SET closed=2 WHERE session_hash=?',(self.token_hash(token),))
  connection_history.finish(self,keys,'signed_out')
 def client_key(self,token,client):return hmac.new(self.key,(self.token_hash(token)+':'+client).encode(),hashlib.sha256).hexdigest()[:24]
 def record(self,event,*,login='',reported='',ip='',source='gateway',severity='info',outcome='observed',request_id='',client='',details=None,incident=False,issue_key=None):
  if not re.fullmatch('[a-z][a-z0-9_.]{0,79}',event) or source not in SOURCES or severity not in SEVERITIES:raise ValueError('Invalid activity event')
  payload={'created':stamp(),'team':team(login),'reported_team':team(reported),'ip':peer(ip),'source':source,'event':event,'severity':severity,'outcome':outcome if outcome in {'success','denied','failed','observed','restored','acknowledged','resolved'} else 'observed','request_id':request_id if re.fullmatch('[a-f0-9]{16,32}',request_id) else '', 'client':client if re.fullmatch('[a-f0-9]{16,32}',client) else '', 'details':safe_details(details or {})}
  now=time.time()
  with self.db() as db:
   db.execute('BEGIN IMMEDIATE')
   if incident and client and event in {'connection.signal_missing','connection.page_closed'}:
    signal=db.execute('SELECT closed,gap FROM clients WHERE client=?',(client,)).fetchone()
    if signal and (not signal['gap'] or signal['closed']!=(1 if event=='connection.page_closed' else 0)):return None
   row=db.execute('SELECT signature FROM events ORDER BY id DESC LIMIT 1').fetchone();anchor=db.execute("SELECT value FROM settings WHERE key='anchor'").fetchone();previous=row[0] if row else anchor[0] if anchor else '0'*64
   encoded=json.dumps(payload,sort_keys=True,separators=(',',':'));signature=hmac.new(self.key,(previous+encoded).encode(),hashlib.sha256).hexdigest()
   cursor=db.execute('INSERT INTO events(at,created,team,reported_team,ip,source,event,severity,outcome,request_id,client,details,previous,signature) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(now,*[payload[k] for k in ('created','team','reported_team','ip','source','event','severity','outcome','request_id','client')],json.dumps(payload['details']),previous,signature));eid=cursor.lastrowid
   if incident:
    scope=payload['team'] or payload['ip'] or payload['client'] or 'system';key=issue_key or scope+':'+event+':'+str(payload['details'].get('endpoint',''))+':'+str(payload['details'].get('status',''))
    if db.execute('SELECT 1 FROM issues WHERE issue_key=?',(key,)).fetchone() or db.execute('SELECT count(*) FROM issues').fetchone()[0]<10000:
     db.execute("INSERT INTO issues(issue_key,team,reported_team,ip,source,event,severity,first_at,last_at,count,state,event_id) VALUES(?,?,?,?,?,?,?,?,?,1,'open',?) ON CONFLICT(issue_key) DO UPDATE SET last_at=excluded.last_at,count=issues.count+1,event_id=excluded.event_id,severity=excluded.severity,state=CASE WHEN issues.state='resolved' THEN 'open' ELSE issues.state END",(key,payload['team'],payload['reported_team'],payload['ip'],source,event,severity,now,now,eid))
   if eid%500==0:self._prune(db,now)
  return eid
 def _prune(self,db,now):
  cutoff=db.execute('SELECT id FROM events ORDER BY id DESC LIMIT 1 OFFSET ?',(self.MAX_EVENTS,)).fetchone();bound=cutoff[0] if cutoff else 0
  old=db.execute('SELECT max(id) FROM events WHERE at<?',(now-self.RETAIN_SECONDS,)).fetchone()[0] or 0;bound=max(bound,old)
  if bound:
   row=db.execute('SELECT signature FROM events WHERE id=?',(bound,)).fetchone()
   if row:db.execute("INSERT OR REPLACE INTO settings VALUES('anchor',?)",(row[0],));db.execute('DELETE FROM events WHERE id<=?',(bound,))
  db.execute('DELETE FROM identities WHERE created<?',(now-self.RETAIN_SECONDS,));db.execute('DELETE FROM clients WHERE last_seen<?',(now-self.RETAIN_SECONDS,));db.execute("DELETE FROM issues WHERE state='resolved' AND last_at<?",(now-self.RETAIN_SECONDS,))
 def telemetry(self,data,token,ip):
  events=data.get('events');client=data.get('client');reported=team(data.get('reportedTeam'))
  if not isinstance(events,list) or not 1<=len(events)<=20 or not isinstance(client,str) or not CLIENT.fullmatch(client):raise ValueError('Invalid diagnostic event batch')
  login=self.identity(token);key=self.client_key(token,client);now=time.time();page='unknown';platform='Other';browser='Other'
  # Validate the complete batch before writing any browser events.
  for event in events:
   if not isinstance(event,dict) or event.get('event') not in BROWSER_EVENTS or not isinstance(event.get('details',{}),dict):raise ValueError('Unsupported browser diagnostic event')
  for item in events:
   event=item['event'];raw=item.get('details',{});details=safe_details({k:v for k,v in raw.items() if k not in ('problem','language','verdict','automaticVerdict','workflowState')})
   page=details.get('page',page);platform=details.get('platform',platform);browser=details.get('browser',browser)
   closed=event=='page.close'
   old=None;restore_incident=False
   if token:
    with self.db() as db:
     old=db.execute('SELECT * FROM clients WHERE client=?',(key,)).fetchone()
     if old is None and db.execute('SELECT count(*) FROM clients').fetchone()[0]>=2000:db.execute('DELETE FROM clients WHERE client IN (SELECT client FROM clients ORDER BY last_seen LIMIT 50)')
     db.execute("INSERT INTO clients(client,team,reported_team,ip,last_seen,page,platform,browser,closed,gap,session_hash) VALUES(?,?,?,?,?,?,?,?,?,0,?) ON CONFLICT(client) DO UPDATE SET team=excluded.team,reported_team=excluded.reported_team,ip=excluded.ip,last_seen=excluded.last_seen,page=CASE WHEN excluded.page='unknown' THEN clients.page ELSE excluded.page END,platform=CASE WHEN excluded.platform='Other' THEN clients.platform ELSE excluded.platform END,browser=CASE WHEN excluded.browser='Other' THEN clients.browser ELSE excluded.browser END,closed=excluded.closed,gap=0",(key,login,reported,peer(ip),now,page,platform,browser,int(closed),self.token_hash(token)))
     if not closed:
      identity=login or reported
      if identity:
       restore_incident=db.execute("SELECT 1 FROM issues WHERE state!='resolved' AND event IN ('connection.signal_missing','connection.page_closed') AND issue_key IN (SELECT 'signal:'||client FROM clients WHERE ip=? AND (team=? OR (team='' AND reported_team=?))) LIMIT 1",(peer(ip),identity,identity)).fetchone() is not None
       db.execute("UPDATE issues SET state='resolved',last_at=? WHERE event IN ('connection.signal_missing','connection.page_closed') AND issue_key IN (SELECT 'signal:'||client FROM clients WHERE ip=? AND (team=? OR (team='' AND reported_team=?)))",(now,peer(ip),identity,identity))
    connection_history.signal(self,key,login,reported,peer(ip),closed,now)
   if not closed and restore_incident:self.record('connection.signal_restored',login=login,reported=reported,ip=ip,source='observer',outcome='restored',client=key)
   if event=='heartbeat':continue
   rid=raw.get('requestId','');rid=rid if isinstance(rid,str) and re.fullmatch('[a-f0-9]{16,32}',rid) else ''
   correlated=False
   if rid:
    with self.db() as db:correlated=db.execute("SELECT 1 FROM events WHERE request_id=? AND source='gateway' AND (team=? OR client=?) LIMIT 1",(rid,login,key)).fetchone() is not None
   details['correlated']=correlated
   severity='error' if event in {'browser.error','browser.rejection'} or (event=='request.failed' and details.get('status',0)>=500) else 'warning' if event in {'request.failed','socket.error','network.offline'} or (event=='socket.close' and not details.get('normalClose')) else 'info'
   expected=not login and event=='request.failed' and details.get('status') in (401,403) and details.get('page') in ('login','instructions') and details.get('endpoint') in ('resource_session','result_notifications','other')
   if correlated or expected:severity='info'
   details['expected']=expected
   incident=not correlated and not expected and severity in {'warning','error'} and event not in {'network.offline'}
   self.record(event,login=login,reported=reported,ip=ip,source='browser',severity=severity,outcome='failed' if severity!='info' else 'observed',request_id=rid,client=key,details=details,incident=incident)
  return len(events)
 def sweep(self,now=None):
  now=time.time() if now is None else now
  with self.db() as db:
   rows=[dict(r) for r in db.execute('SELECT * FROM clients WHERE closed=0 AND gap=0 AND last_seen<?',(now-connection_history.GAP_SECONDS,))];db.execute('UPDATE clients SET gap=1 WHERE closed=0 AND gap=0 AND last_seen<?',(now-connection_history.GAP_SECONDS,))
  connection_history.finish(self,[r['client'] for r in rows],'signal_gap')
  seen=set()
  for row in rows:
   group=(row['team'] or row['reported_team'] or row['client'],row['ip'])
   if group in seen or self.other_recent_signal(row,now):continue
   seen.add(group)
   self.record('connection.signal_missing',login=row['team'],reported=row['reported_team'],ip=row['ip'],source='observer',severity='warning',client=row['client'],details={'page':row['page']},incident=True,issue_key='signal:'+row['client'])
  with self.db() as db:
   closed=[dict(r) for r in db.execute("SELECT * FROM clients WHERE closed=1 AND gap=0 AND last_seen<? AND page!='login'",(now-connection_history.CLOSE_GRACE_SECONDS,))];db.execute("UPDATE clients SET gap=1 WHERE closed=1 AND gap=0 AND last_seen<? AND page!='login'",(now-connection_history.CLOSE_GRACE_SECONDS,))
  for row in closed:
   group=(row['team'] or row['reported_team'] or row['client'],row['ip'])
   if group in seen or self.other_recent_signal(row,now):continue
   seen.add(group)
   self.record('connection.page_closed',login=row['team'],reported=row['reported_team'],ip=row['ip'],source='observer',severity='warning',client=row['client'],incident=True,issue_key='signal:'+row['client'])
 def other_recent_signal(self,row,now):
  identity=row['team'] or row['reported_team']
  if not identity:return False
  with self.db() as db:return db.execute("SELECT 1 FROM clients WHERE client!=? AND ip=? AND closed=0 AND last_seen>=? AND (team=? OR (team='' AND reported_team=?)) LIMIT 1",(row['client'],row['ip'],now-connection_history.GAP_SECONDS,identity,identity)).fetchone() is not None
 def observe(self,snapshot):
  with self.db() as db:initialized=db.execute("SELECT value FROM settings WHERE key='pc2.initialized'").fetchone() is not None
  records=[]
  for run in snapshot.get('runs',[]):
   details={k:run[k] for k in ('number','site','problem','language','verdict','final','accepted','deleted','automaticVerdict','workflowState','elapsedMinutes') if k in run};records.append(('run:'+str(run.get('site',1))+':'+str(run['number']),run.get('team',''),'submission',details))
  for c in snapshot.get('clarifications',[]):records.append(('clarification:'+str(c.get('site',1))+':'+str(c['number']),c.get('team',''),'clarification',{k:c[k] for k in ('number','site','answered','deleted','all') if k in c}))
  for t in snapshot.get('teams',[]):records.append(('team:'+t['login'],t['login'],'team.connection',{'online':bool(t.get('online'))}))
  for entity,login,kind,details in records:
   fingerprint=hashlib.sha256(json.dumps(details,sort_keys=True).encode()).hexdigest()
   with self.db() as db:old=db.execute('SELECT fingerprint FROM observed WHERE entity=?',(entity,)).fetchone()
   if old and old[0]==fingerprint:continue
   event=(kind+'.history') if not initialized else (kind+'.recorded' if old is None else kind+'.updated')
   disconnected=initialized and old is not None and kind=='team.connection' and not details['online']
   self.record(event,login=login,source='pc2',severity='info',incident=False,details={**details,'historical':not initialized})
   if kind=='team.connection' and details['online']:
    with self.db() as db:db.execute("UPDATE issues SET state='resolved' WHERE issue_key=?",('native:'+login,))
   with self.db() as db:db.execute('INSERT OR REPLACE INTO observed VALUES(?,?)',(entity,fingerprint))
  with self.db() as db:
   db.execute("INSERT OR REPLACE INTO settings VALUES('pc2.initialized','1')");db.execute("INSERT OR REPLACE INTO settings VALUES('pc2.last_seen',?)",(str(time.time()),))
 def summary(self):
  with self.db() as db:
   count=db.execute('SELECT count(*) FROM events').fetchone()[0];last=db.execute('SELECT created FROM events ORDER BY id DESC LIMIT 1').fetchone();issue=db.execute("SELECT count(*) FROM issues WHERE state!='resolved'").fetchone()[0];monitor=db.execute("SELECT value FROM settings WHERE key='pc2.last_seen'").fetchone();anchor=db.execute("SELECT value FROM settings WHERE key='anchor'").fetchone()
  return {'events':count,'unresolved':issue,'lastEvent':last[0] if last else None,'nativeLastSeen':stamp(float(monitor[0])) if monitor else None,'retentionDays':30,'maxEvents':self.MAX_EVENTS,'trimmed':bool(anchor)}
 def query(self,filters=None,limit=200):
  f=filters or {};where=[];args=[]
  if f.get('team'):
   if not team(f['team']):raise ValueError('Invalid team filter')
   where.append('(team=? OR (team=\'\' AND reported_team=?))');args.extend([f['team']]*2)
  if f.get('severity'):
   if f['severity'] not in SEVERITIES:raise ValueError('Invalid severity')
   where.append('severity=?');args.append(f['severity'])
  if f.get('source'):
   if f['source'] not in SOURCES:raise ValueError('Invalid source')
   where.append('source=?');args.append(f['source'])
  if f.get('category'):
   if f['category'] not in {'login','logout','submission','clarification','request','resource','browser','page','session','socket','network','connection','team','file','action','form','monitor','issue'}:raise ValueError('Invalid category')
   where.append('(event=? OR event LIKE ?)');args.extend([f['category'],f['category']+'.%'])
  if f.get('search'):
   search=f['search']
   if not isinstance(search,str) or len(search)>120:raise ValueError('Use up to 120 search characters')
   where.append("instr(lower(team||' '||reported_team||' '||ip||' '||event||' '||request_id||' '||details),lower(?))>0");args.append(search)
  for key,sql in [('since','at>=?'),('before','id<?')]:
   if f.get(key):
    try:value=float(f[key])
    except (ValueError,TypeError):raise ValueError('Invalid cursor or time')
    if not 0<value<=time.time()+1000000000:raise ValueError('Invalid cursor or time')
    where.append(sql);args.append(value)
  condition=' WHERE '+' AND '.join(where) if where else ''
  with self.db() as db:
   rows=[dict(r) for r in db.execute('SELECT * FROM events'+condition+' ORDER BY id DESC LIMIT ?',(*args,min(limit,10000)+1))]
   issues=[dict(r) for r in db.execute("SELECT * FROM issues WHERE state!='resolved'"+(' AND (team=? OR (team=\'\' AND reported_team=?))' if f.get('team') else '')+' ORDER BY last_at DESC LIMIT 100',([f['team']]*2 if f.get('team') else []))]
   clients=[dict(r) for r in db.execute('SELECT * FROM clients'+(' WHERE team=? OR (team=\'\' AND reported_team=?)' if f.get('team') else '')+' ORDER BY last_seen DESC LIMIT 100',([f['team']]*2 if f.get('team') else []))]
  more=len(rows)>limit;rows=rows[:limit]
  for row in rows:row['details']=json.loads(row['details']);row.pop('previous');row.pop('signature');row.pop('at')
  for row in clients:row.pop('session_hash',None)
  return {'events':rows,'issues':issues,'clients':clients,'more':more,'before':rows[-1]['id'] if rows else None,'summary':self.summary()}
 def resolve(self,iid,action,actor):
  if type(iid) is not int or action not in {'acknowledge','resolve'}:raise ValueError('Invalid incident action')
  state='resolved' if action=='resolve' else 'acknowledged'
  with self.db() as db:
   row=db.execute('SELECT * FROM issues WHERE id=?',(iid,)).fetchone()
   if not row:raise ValueError('Incident not found')
   db.execute('UPDATE issues SET state=?,actor=? WHERE id=?',(state,text(actor,64),iid))
  self.record('issue.'+state,login=row['team'],source='organizer',outcome=state,details={'number':iid})
 def verify(self):
  with self.db() as db:
   db.execute('BEGIN');anchor=db.execute("SELECT value FROM settings WHERE key='anchor'").fetchone();previous=anchor[0] if anchor else '0'*64;count=0
   for row in db.execute('SELECT * FROM events ORDER BY id'):
    payload={k:row[k] for k in ('created','team','reported_team','ip','source','event','severity','outcome','request_id','client')};payload['details']=json.loads(row['details']);sig=hmac.new(self.key,(previous+json.dumps(payload,sort_keys=True,separators=(',',':'))).encode(),hashlib.sha256).hexdigest()
    if row['previous']!=previous or not hmac.compare_digest(row['signature'],sig):return {'valid':False,'row':row['id']}
    previous=sig;count+=1
  return {'valid':True,'entries':count,'retainedChain':bool(anchor)}
