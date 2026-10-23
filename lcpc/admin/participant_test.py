"""Use the real participant UI and prepare separate rehearsal workspaces; never auto-switch."""
import datetime,ipaddress,json,secrets,shutil
from pathlib import Path
from urllib.parse import urlsplit
from core import require,Error,password_policy
from contests import DraftBridge,write_json
from contest_exports import csv_bytes
from native_admin import reauth
import test_team
from participant_access import access,checks,configuration,SCENARIOS

def view(app):
 manager=app.manager;row=manager.selected();state=Path(row['state']);info=access(app)
 marker=state/'admin-dashboard/rehearsal.json';rehearsal=json.loads(marker.read_text()) if marker.exists() else None
 snapshot=app.bridge.snapshot();fingerprint=configuration(snapshot,app.resources.resources())
 with app.resources.db() as db:saved=db.execute("SELECT value FROM settings WHERE key='participant.checklist'").fetchone()
 checklist=json.loads(saved[0]) if saved else {'results':{},'configuration':fingerprint}
 return {'contestId':row['id'],'active':info['active'],'origin':info['origin'],'loginUrl':info['origin']+'/#/login' if info['origin'] else None,'access':info,'rehearsal':rehearsal,'configuration':fingerprint,'testAccount':test_team.info(app),'checklist':checklist,'stale':checklist.get('configuration')!=fingerprint}

def prepare(app,data):
 manager=app.manager;require(data.get('confirm')=='CONFIRM','Type CONFIRM to prepare a rehearsal');source=manager.selected();require(type(data.get('durationMinutes')) is int and 1<=data['durationMinutes']<=1440,'Use 1–1440 minutes');require(type(data.get('publishResources')) is bool,'Choose rehearsal resource publication');snapshot=app.bridge.snapshot(fresh=True);require(snapshot.get('problems'),'Add problems before preparing a rehearsal',409)
 published={(r['problem'],r['kind'],r['language'],r['sha256']) for r in app.resources.resources() if r['published']};slug='rehearsal-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d-%H%M')+'-'+secrets.token_hex(3)
 result=manager.create({'title':snapshot['contest']['title'][:160]+' · Rehearsal','shortName':'REHEARSAL','slug':slug,'durationMinutes':data['durationMinutes'],'penaltyMinutes':snapshot['contest'].get('penaltyMinutes',20),'workflow':'automatic','copyProblems':True,'copyResources':True});row=manager.row(result['id']);store=manager.store_for(row);password=secrets.token_urlsafe(24)
 try:
  bridge=DraftBridge(row['state']);bridge.call('team.create',{'name':'Rehearsal Team','password':password});write_json(store.base/'rehearsal.json',{'sourceContestId':source['id'],'team':'team1','created':datetime.datetime.now(datetime.timezone.utc).isoformat()})
  if data['publishResources']:
   with store.db() as db:
    for r in store.resources():
     if (r['problem'],r['kind'],r['language'],r['sha256']) in published:db.execute('UPDATE resources SET published=1 WHERE id=?',(r['id'],))
  store.publish_catalog(bridge.snapshot())
 except Exception:
  # Only the newly created, never-activated workspace is rolled back.
  manager.stores.pop(row['state'],None);manager.data['contests']=[r for r in manager.data['contests'] if r['id']!=slug];manager.save();dest=Path(row['state'])
  if dest.parent==manager.instances and dest.name==slug:shutil.rmtree(dest)
  raise
 return {'contestId':slug,'login':'team1','password':password,'name':'Rehearsal Team'}
def route(handler,path,data=None):
 if not path.startswith('/api/participant-test'):return False
 handler.user('owner');app=handler.app
 if data is None:
  require(path=='/api/participant-test','Not found',404);handler.send(200,view(app));return True
 app.manager.guard(data)
 if path=='/api/participant-test/checks':
  value=checks(app);app.store.audit(handler.actor,'participant.read-only-checks','success',details={'contestId':app.manager.data['selected'],'failed':sum(c['status']=='failed' for c in value['checks'])});handler.send(200,value);return True
 if path=='/api/participant-test/checklist':
  current=view(app);require(data.get('configuration')==current['configuration'],'Problem or resource settings changed. Reload the test page.',409);results=data.get('results');require(isinstance(results,dict) and len(results)<=1000,'Invalid test checklist')
  ids={p['id'] for p in app.bridge.snapshot().get('problems',[])}|{'global'}
  for key,status in results.items():
   parts=key.rsplit('|',1);require(len(parts)==2 and parts[0] in ids and parts[1] in SCENARIOS and status in ('pending','passed','failed','not_applicable'),'Invalid checklist scenario')
  value={'configuration':current['configuration'],'results':results,'updatedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'actor':handler.actor}
  with app.resources.db() as db:db.execute("INSERT OR REPLACE INTO settings VALUES('participant.checklist',?)",(json.dumps(value),))
  app.store.audit(handler.actor,'participant.manual-checklist','success',details={'contestId':app.manager.data['selected'],'scenarios':len(results)});handler.send(200,value);return True
 if path=='/api/participant-test/test-account':
  reauth(handler,data);result=test_team.credentials(app);app.store.audit(handler.actor,'participant.test-access-downloaded','success',details={'contestId':app.manager.data['selected'],'login':test_team.LOGIN});handler.send(200,csv_bytes(['contestId','login','password','name'],[result]),'text/csv; charset=utf-8',{'Content-Disposition':'attachment; filename="test-team-access.csv"'});return True
 require(path=='/api/participant-test/prepare','Not found',404);reauth(handler,data);result=prepare(app,data);app.store.audit(handler.actor,'participant.rehearsal-prepared','success',details={'contestId':app.manager.data['selected'],'rehearsalContestId':result['contestId']});handler.send(200,csv_bytes(['contestId','login','password','name'],[result]),'text/csv; charset=utf-8',{'Content-Disposition':'attachment; filename="rehearsal-access.csv"'});return True
