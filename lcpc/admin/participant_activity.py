"""Private participant diagnostics UI routes and read-only PC2 event observer."""
import json,sys,threading,time
from urllib.parse import parse_qs,urlsplit
from core import ROOT,Error,require
sys.path.insert(0,str(ROOT/'lcpc'))
from infra.participant_activity import ActivityStore
from contest_exports import csv_bytes

def activity_store(app,state=None):
 path=str(state or app.resources.state)
 if not hasattr(app,'participant_stores'):app.participant_stores={}
 if path not in app.participant_stores:app.participant_stores[path]=ActivityStore(path)
 return app.participant_stores[path]
def route(handler,path,data=None):
 if not path.startswith('/api/participant-activity'):return False
 handler.user('owner');app=handler.app;require(not app.manager.busy(),'A contest operation is in progress; diagnostics remain retained.',409);store=activity_store(app);op=path.rsplit('/',1)[-1]
 try:
  if data is None:
   require(path=='/api/participant-activity','Not found',404);raw=parse_qs(urlsplit(handler.path).query);allowed={'team','severity','source','category','search','since','before'};require(not(set(raw)-allowed),'Invalid diagnostic filters');filters={k:v[0] for k,v in raw.items()};result=store.query(filters);result['contestId']=app.manager.data['selected'];result['active']=app.manager.data['active']==app.manager.data['selected'];handler.send(200,result);return True
  app.manager.guard(data)
  if op=='open':app.store.audit(handler.actor,'participant.activity-open','success',details={'contestId':app.manager.data['selected']});handler.send(200,{'ok':True});return True
  if op=='integrity':
   value=store.verify();app.store.audit(handler.actor,'participant.activity-integrity','success' if value['valid'] else 'failed',details={'contestId':app.manager.data['selected'],**value});handler.send(200,value);return True
  if op=='issue':
   store.resolve(data.get('id'),data.get('action'),handler.actor);app.store.audit(handler.actor,'participant.issue.'+str(data.get('action')),'success',details={'contestId':app.manager.data['selected'],'id':data['id']});handler.send(200,{'ok':True});return True
  if op=='export':
   filters=data.get('filters',{});require(isinstance(filters,dict) and not(set(filters)-{'team','severity','source','category','search','since'}),'Invalid diagnostic export filters');value=store.query(filters,limit=10000);rows=[{**row,'identity':'verified' if row['team'] else 'reported' if row['reported_team'] else 'unattributed'} for row in value['events']];body=csv_bytes(['id','created','team','reported_team','identity','ip','source','event','severity','outcome','request_id','client','details'],rows);app.store.audit(handler.actor,'participant.activity-export','success',details={'contestId':app.manager.data['selected'],'rows':len(rows),'limited':value['more']});handler.send(200,body,'text/csv; charset=utf-8',{'Content-Disposition':'attachment; filename="participant-activity.csv"','X-LCPC-Export-Limited':str(value['more']).lower()});return True
 except ValueError as error:raise Error(400,str(error))
 raise Error(404,'Not found')
class ActivityMonitor:
 def __init__(self,app):self.app=app;self.stop_event=threading.Event();self.failed=False
 def poll_once(self):
  app=self.app
  with app.manager.lock:
   cid=app.manager.data['active']
   if not cid or app.manager.busy():return
   row=app.manager.row(cid);store=activity_store(app,row['state'])
   try:
    store.sweep();snapshot=app.manager.bridge_for(row).snapshot();store.observe(snapshot)
    if self.failed:
     store.record('monitor.restored',source='observer',outcome='restored')
     with store.db() as db:db.execute("UPDATE issues SET state='resolved' WHERE event='monitor.unavailable' AND source='observer'")
     self.failed=False
   except Exception:
    if not self.failed:
     try:store.record('monitor.unavailable',source='observer',severity='error',outcome='failed',incident=True)
     except Exception:pass
    self.failed=True
 def start(self):
  def run():
   while not self.stop_event.is_set():
    try:self.poll_once()
    except Exception:pass
    self.stop_event.wait(5)
  self.thread=threading.Thread(target=run,name='participant-diagnostics',daemon=True);self.thread.start()
 def close(self):
  self.stop_event.set()
  if hasattr(self,'thread'):self.thread.join(timeout=3)
