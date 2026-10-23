"""Durable owner notification inbox. Reading is separate from resolving a security/participant incident."""
import json,time
from pathlib import Path
from urllib.parse import parse_qs,urlsplit
from core import require,stamp
from participant_activity import activity_store
CONNECTIONS=('connection.signal_missing','connection.page_closed','connection.signal_restored','team.connection.updated','monitor.restored')
def initialize(store):
 with store.db() as db:db.executescript('''
 CREATE TABLE IF NOT EXISTS notifications(id INTEGER PRIMARY KEY AUTOINCREMENT,created TEXT NOT NULL,source_key TEXT UNIQUE NOT NULL,category TEXT NOT NULL,contest_id TEXT NOT NULL,severity TEXT NOT NULL,title TEXT NOT NULL,message TEXT NOT NULL,details TEXT NOT NULL);
 CREATE TABLE IF NOT EXISTS notification_reads(username TEXT NOT NULL,notification_id INTEGER NOT NULL,read_at TEXT NOT NULL,PRIMARY KEY(username,notification_id));
 CREATE TABLE IF NOT EXISTS notification_cursors(source TEXT PRIMARY KEY,last_id INTEGER NOT NULL);
 CREATE INDEX IF NOT EXISTS notifications_category ON notifications(category,id);
 ''')
 # Existing inbox copies are derived history; keep original signed activity untouched.
 with store.db() as db:
  columns={r[1] for r in db.execute('PRAGMA table_info(notifications)')};legacy='archived' not in columns
  for name,definition in [('archived','INTEGER NOT NULL DEFAULT 0'),('occurrences','INTEGER NOT NULL DEFAULT 1'),('last_occurred',"TEXT NOT NULL DEFAULT ''"),('group_key',"TEXT NOT NULL DEFAULT ''")]:
   if name not in columns:db.execute('ALTER TABLE notifications ADD COLUMN '+name+' '+definition)
  db.execute('CREATE INDEX IF NOT EXISTS notification_group ON notifications(group_key,last_occurred)')
  if legacy:
   for row in db.execute("SELECT id,category,details FROM notifications WHERE category!='security'").fetchall():
    payload=json.loads(row['details']);details=payload.get('details',{});event=payload.get('event','')
    expected=details.get('status') in (401,403) and details.get('page') in ('instructions','login') and not payload.get('team')
    if row['category']=='connection' or expected or details.get('correlated'):
     db.execute('UPDATE notifications SET archived=1 WHERE id=?',(row['id'],))
  db.execute("UPDATE notifications SET last_occurred=created WHERE last_occurred=''")

def actionable(row,details):
 event=row['event']
 if event=='team.connection.updated' or details.get('historical') or details.get('correlated') or details.get('expected'):return False
 if event=='request.failed' and not row['team'] and details.get('status') in (401,403) and details.get('page') in ('instructions','login') and details.get('endpoint') in ('other','result_notifications','resource_session'):return False
 return row['severity'] in ('warning','error') or event in CONNECTIONS

def sync(app):
 initialize(app.store)
 with app.store.db() as target:
  target.execute('BEGIN IMMEDIATE')
  cursor=lambda key: (target.execute('SELECT last_id FROM notification_cursors WHERE source=?',(key,)).fetchone() or [0])[0]
  def advance(key,n):target.execute('INSERT OR REPLACE INTO notification_cursors VALUES(?,?)',(key,n))
  rows=target.execute('SELECT * FROM alerts WHERE id>? ORDER BY id LIMIT 500',(cursor('security'),)).fetchall()
  for row in rows:
   target.execute('INSERT OR IGNORE INTO notifications(created,source_key,category,contest_id,severity,title,message,details) VALUES(?,?,?,?,?,?,?,?)',(row['created'],'security:'+str(row['id']),'security','',row['severity'],'Security '+row['severity'],row['message'],json.dumps({'securityAlertId':row['id']})))
  if rows:advance('security',rows[-1]['id'])
  for contest in app.manager.data['contests']:
   path=Path(contest['state'])/'participant-activity/activity.sqlite3'
   if not path.exists():continue
   key='activity:'+contest['id'];store=activity_store(app,contest['state'])
   with store.db() as source:
    rows=source.execute("SELECT id,created,team,reported_team,ip,event,severity,details FROM events WHERE id>? AND (severity IN ('warning','error') OR event IN (?,?,?,?,?)) ORDER BY id LIMIT 500",(cursor(key),*CONNECTIONS)).fetchall()
   for row in rows:
    details=json.loads(row['details']);event=row['event']
    if not actionable(row,details):continue
    category='connection' if event in CONNECTIONS else 'participant';who=row['team'] or (row['reported_team']+' (unverified)' if row['reported_team'] else 'Participant')
    title={'connection.signal_missing':'Browser signal missing','connection.page_closed':'Participant page left or closed','connection.signal_restored':'Connection signal restored','team.connection.updated':'PC² connection restored' if details.get('online') else 'PC² connection lost','monitor.restored':'Participant monitor restored'}.get(event,event.replace('.',' ').capitalize())
    severity='success' if event in ('connection.signal_restored','monitor.restored') or event=='team.connection.updated' and details.get('online') else row['severity']
    message=who+': '+title+(' · '+row['ip'] if row['ip'] else '')
    payload={'event':event,'team':row['team'],'reportedTeam':row['reported_team'],'ip':row['ip'],'sourceEventId':row['id'],'details':details}
    source_key=key+':'+str(row['id'])
    if target.execute('SELECT 1 FROM notifications WHERE source_key=?',(source_key,)).fetchone():continue
    group=contest['id']+':'+category+':'+(row['team'] or row['ip'])+':'+event+':'+str(details.get('endpoint',''))+':'+str(details.get('status',''))
    prior=target.execute('SELECT id,last_occurred FROM notifications WHERE group_key=? AND archived=0 ORDER BY id DESC LIMIT 1',(group,)).fetchone() if category=='participant' else None
    if prior:
     import datetime
     delta=(datetime.datetime.fromisoformat(row['created'])-datetime.datetime.fromisoformat(prior['last_occurred'])).total_seconds()
     if 0<=delta<=300:
      target.execute('UPDATE notifications SET occurrences=occurrences+1,last_occurred=? WHERE id=?',(row['created'],prior['id']));continue
    target.execute('INSERT OR IGNORE INTO notifications(created,source_key,category,contest_id,severity,title,message,details,last_occurred,group_key) VALUES(?,?,?,?,?,?,?,?,?,?)',(row['created'],source_key,category,contest['id'],severity,title,message,json.dumps(payload),row['created'],group))
   if rows:advance(key,rows[-1]['id'])

def integer(raw,label):
 try:value=int(raw)
 except (ValueError,TypeError):require(False,'Invalid '+label)
 require(0<=value<=2**63-1,'Invalid '+label);return value

def listing(app,user,q):
 sync(app);username=user['username'];params=[username];where=['1=1'] if q.get('archived')==['1'] else ['n.archived=0']
 for key,column,allowed in [('category','n.category',{'security','connection','participant'}),('severity','n.severity',{'info','success','warning','error'})]:
  if q.get(key):require(q[key][0] in allowed,'Invalid notification filter');where.append(column+'=?');params.append(q[key][0])
 if q.get('unread')==['1']:where.append('r.notification_id IS NULL')
 search=q.get('search',[''])[0];require(len(search)<=160,'Search is too long')
 if search:where.append('(n.title LIKE ? OR n.message LIKE ? OR n.contest_id LIKE ?)');params.extend(['%'+search+'%']*3)
 after=integer(q['after'][0],'cursor') if 'after' in q else None;before=integer(q['before'][0],'cursor') if 'before' in q else None
 require(after is None or before is None,'Choose one pagination direction')
 if after is not None:where.append('n.id>?');params.append(after)
 if before is not None:where.append('n.id<?');params.append(before)
 with app.store.db() as db:
  latest=db.execute('SELECT coalesce(max(id),0) FROM notifications').fetchone()[0]
  unread=db.execute('SELECT count(*) FROM notifications n LEFT JOIN notification_reads r ON r.notification_id=n.id AND r.username=? WHERE r.notification_id IS NULL AND n.archived=0',(username,)).fetchone()[0]
  rows=[dict(r) for r in db.execute('SELECT n.*,r.read_at FROM notifications n LEFT JOIN notification_reads r ON r.notification_id=n.id AND r.username=? WHERE '+' AND '.join(where)+' ORDER BY n.id '+('ASC' if after is not None else 'DESC')+' LIMIT 61',params)]
 more=len(rows)>60;rows=rows[:60]
 for row in rows:row['details']=json.loads(row['details']);row.pop('source_key',None)
 return {'notifications':rows,'unread':unread,'latest':latest,'cursor':rows[-1]['id'] if more and rows else latest,'before':rows[-1]['id'] if rows else None,'more':more,'checkedAt':stamp()}

def route(handler,path,data=None):
 if path not in ('/api/notifications','/api/notifications/read'):return False
 user=handler.user('owner');app=handler.app
 if data is None:
  require(path=='/api/notifications','Method not allowed',405);q=parse_qs(urlsplit(handler.path).query);require(not(set(q)-{'after','before','category','severity','unread','search','archived'}),'Invalid notification filters');require(all(len(v)==1 for v in q.values()),'Choose each notification filter once');handler.send(200,listing(app,user,q));return True
 require(path=='/api/notifications/read','Method not allowed',405);require(not(set(data)-{'id','through','contestId'}),'Unexpected notification field');initialize(app.store)
 require(('id' in data)!=('through' in data),'Choose one notification or the displayed range')
 key='id' if 'id' in data else 'through';require(type(data[key]) is int and 0<data[key]<=2**63-1,'Invalid notification ID')
 with app.store.db() as db:
  rows=db.execute('SELECT id FROM notifications WHERE id'+('=?' if key=='id' else '<=?'),(data[key],)).fetchall()
  require(rows or key=='through','Notification not found',404)
  db.executemany('INSERT OR IGNORE INTO notification_reads VALUES(?,?,?)',[(user['username'],r['id'],stamp()) for r in rows])
 handler.send(200,{'ok':True});return True
