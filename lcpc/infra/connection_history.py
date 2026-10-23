"""Observed browser signal intervals, not router leases or proof of Wi-Fi membership."""
import ipaddress,json,time
from collections import defaultdict
GAP_SECONDS=180
CLOSE_GRACE_SECONDS=90
HEARTBEAT_SECONDS=10
def migrate(store):
 with store.db() as db:
  db.executescript('''CREATE TABLE IF NOT EXISTS connection_periods(id INTEGER PRIMARY KEY AUTOINCREMENT,client TEXT NOT NULL,team TEXT NOT NULL,reported_team TEXT NOT NULL,ip TEXT NOT NULL,network TEXT NOT NULL,started REAL NOT NULL,last_seen REAL NOT NULL,ended REAL,reason TEXT NOT NULL DEFAULT '');CREATE INDEX IF NOT EXISTS connection_client ON connection_periods(client,id);CREATE INDEX IF NOT EXISTS connection_team ON connection_periods(team,id);''')
def network(store,ip):
 try:
  profile=json.loads((store.state/'network/profile.json').read_text());net=ipaddress.ip_network(profile['cidr'],strict=False)
  return str(net) if ipaddress.ip_address(ip) in net else ''
 except (OSError,ValueError,KeyError):return ''
def signal(store,key,team,reported,ip,closed,now):
 net=network(store,ip)
 with store.db() as db:
  row=db.execute('SELECT * FROM connection_periods WHERE client=? AND ended IS NULL ORDER BY id DESC LIMIT 1',(key,)).fetchone()
  if row and (row['ip']!=ip or row['network']!=net or now-row['last_seen']>GAP_SECONDS):
   db.execute("UPDATE connection_periods SET ended=last_seen,reason=? WHERE id=?",('address_changed' if row['ip']!=ip or row['network']!=net else 'signal_gap',row['id']));row=None
  if closed:
   if row:db.execute("UPDATE connection_periods SET last_seen=?,ended=?,reason='page_left' WHERE id=?",(now,now,row['id']))
  elif row:db.execute('UPDATE connection_periods SET last_seen=? WHERE id=?',(now,row['id']))
  else:db.execute('INSERT INTO connection_periods(client,team,reported_team,ip,network,started,last_seen) VALUES(?,?,?,?,?,?,?)',(key,team,reported,ip,net,now,now))
  # Bound diagnostic history independently of official contest records.
  db.execute('DELETE FROM connection_periods WHERE last_seen<?',(now-store.RETAIN_SECONDS,))
  db.execute('DELETE FROM connection_periods WHERE id IN (SELECT id FROM connection_periods ORDER BY id DESC LIMIT -1 OFFSET 50000)')
def finish(store,clients,reason,now=None):
 with store.db() as db:
  for key in clients:db.execute('UPDATE connection_periods SET ended=last_seen,reason=? WHERE client=? AND ended IS NULL',(reason,key))
def union_seconds(periods):
 total=0;start=end=None
 for a,b in sorted((r['started'],r['last_seen']) for r in periods):
  if start is None:start,end=a,b
  elif a<=end:end=max(end,b)
  else:total+=max(0,end-start);start,end=a,b
 return round(total+max(0,end-start),1) if start is not None else 0

def view(store,teams):
 now=time.time()
 with store.db() as db:
  clients=[dict(r) for r in db.execute('SELECT client,team,reported_team,ip,last_seen,page,platform,browser,closed,gap FROM clients ORDER BY last_seen DESC LIMIT 2000')]
  periods=[dict(r) for r in db.execute('SELECT * FROM connection_periods ORDER BY id DESC LIMIT 50000')]
 by_client=defaultdict(list);by_period=defaultdict(list);by_reported=defaultdict(list)
 for c in clients:by_client[c['team'] or c['reported_team']].append(c)
 for p in periods:(by_period if p['team'] else by_reported)[p['team'] or p['reported_team']].append(p)
 rows=[]
 for team in teams:
  login=team['login'];signals=by_client[login];verified=[c for c in signals if c['team']==login];recent=[c for c in signals if not c['closed'] and now-c['last_seen']<=GAP_SECONDS];confirmed=[c for c in recent if c['team']==login];history=by_period[login];reported=by_reported[login];latest=max([c['last_seen'] for c in signals],default=None)
  networks=sorted({r['network'] for r in history})
  totals=[{'network':n or 'Unmapped network','observedSeconds':union_seconds([p for p in history if p['network']==n]),'firstSeen':min(p['started'] for p in history if p['network']==n),'lastSeen':max(p['last_seen'] for p in history if p['network']==n)} for n in networks]
  state='recent' if confirmed else 'unverified' if recent else 'closed' if signals and all(c['closed'] for c in signals) else 'missing' if signals else 'not_observed'
  rows.append({'login':login,'name':team['name'],'nativeOnline':bool(team.get('online')),'state':state,'lastSeen':latest,'missingSeconds':round(now-latest) if latest and not recent else 0,'clients':signals,'networks':totals,'periods':history[:200],'reportedPeriods':reported[:100],'observedSeconds':union_seconds(history),'reportedSeconds':union_seconds(reported)})
 return {'teams':rows,'checkedAt':now,'gapSeconds':GAP_SECONDS,'heartbeatSeconds':HEARTBEAT_SECONDS,'historyLimit':50000,'scope':'Observed browser-to-server intervals on the server LAN CIDR. This does not inspect router leases, SSIDs or other applications. Overlapping tabs are merged, and gaps are excluded.'}
