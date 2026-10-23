"""Owner-only observed connection status and incremental dashboard alert feed."""
import json,time
from urllib.parse import parse_qs,urlsplit
from core import require
from participant_activity import activity_store
from infra.connection_history import view

def route(handler,path,data=None):
 if not path.startswith('/api/team-connections'):return False
 handler.user('owner');require(data is None,'Method not allowed',405);app=handler.app;require(not app.manager.busy(),'A contest operation is in progress',409);q=parse_qs(urlsplit(handler.path).query)
 require(q.get('contestId',[''])[0]==app.manager.data['selected'],'Workspace changed. Reopen connection monitoring.',409);store=activity_store(app)
 if path=='/api/team-connections':
  result=view(store,app.bridge.snapshot().get('teams',[]));result.update(contestId=app.manager.data['selected'],active=app.manager.data['active']==app.manager.data['selected']);handler.send(200,result);return True
 require(path=='/api/team-connections/alerts','Not found',404)
 try:after=int(q.get('after',['0'])[0])
 except (ValueError,TypeError):require(False,'Invalid notification cursor')
 require(0<=after<=2**63-1,'Invalid notification cursor')
 with store.db() as db:
  db.execute('BEGIN')
  rows=[dict(r) for r in db.execute("SELECT id,created,team,reported_team,ip,event,severity,details FROM events WHERE id>? AND (team!='' OR reported_team!='') AND event IN ('connection.signal_missing','connection.page_closed','connection.signal_restored','team.connection.updated') ORDER BY id LIMIT 100",(after,))]
  latest=db.execute('SELECT max(id) FROM events').fetchone()[0] or 0
 for r in rows:r['details']=json.loads(r['details'])
 handler.send(200,{'contestId':app.manager.data['selected'],'alerts':rows,'latest':latest,'cursor':rows[-1]['id'] if len(rows)==100 else latest});return True
