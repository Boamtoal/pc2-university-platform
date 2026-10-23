"""Two read-only views; public data is read only from the freeze-aware exporter."""
import copy,json,re
from datetime import datetime, timezone
from pathlib import Path
from core import require, stamp
from submission_review import query
from participant_access import access

def released(state):
 path=Path(state)/'wti/WebContent/WTI-UI/standings/data.json'
 try:
  require(path.stat().st_size<=8*1024*1024,'The public standings snapshot is too large.',503)
  value=json.loads(path.read_text())
  published=datetime.fromisoformat(value['publishedAt'].replace('Z','+00:00'))
  age=(datetime.now(timezone.utc)-published).total_seconds()
  require(-5<=age<=30,'Public standings updates have stopped. Waiting for the public exporter.',503)
  require(value.get('release',{}).get('schema')==1 and value['release'].get('preliminaryResultsCounted') is False,'Waiting for a verified public standings snapshot.',503)
  require(isinstance(value['contestStandings']['standingsHeader'],dict),'Public standings are unavailable.',503)
  return value
 except (OSError,ValueError,KeyError,TypeError):
  require(False,'Public standings are unavailable. Waiting for the public exporter.',503)

def route(handler,path):
 if path not in ('/api/scoreboards/public','/api/scoreboards/live'):return False
 handler.user();query(handler,required=True);app=handler.app;cid=app.manager.data['selected']
 require(cid==app.manager.data['active'],'Live scoreboard views require the active contest. Retained standings are available in Exports & Backups.',409)
 if path.endswith('/public'):
  # Never substitute bridge.snapshot().standings, including when the export is stale.
  payload=released(app.manager.selected()['state']);mode='public'
 else:
  snapshot=app.bridge.snapshot()
  require(not snapshot.get('judging',{}).get('preliminaryResultsCounted'),'Preliminary scoring is enabled in PC². Disable it in Judging before viewing final standings.',409)
  payload=copy.deepcopy(snapshot['standings']);payload['publishedAt']=snapshot['updatedAt'];mode='live'
  clock=snapshot.get('contest',{})
  payload['clock']={'schema':1,'lengthSeconds':clock.get('lengthSeconds',0),'remainingSeconds':clock.get('remainingSeconds',0),'running':clock.get('running',False)}
  problems=payload.get('contestStandings',{}).get('standingsHeader',{}).get('problem',[])
  columns=problems if isinstance(problems,list) else [problems]
  for index,problem in enumerate(p for p in snapshot.get('problems',[]) if p.get('active',True)):
   for column in columns:
    if column.get('id')!=index+1 or column.get('title')!=problem.get('name'):continue
    if re.fullmatch(r'[A-Za-z]{1,3}',problem.get('letter','')):column['letter']=problem['letter']
    if re.fullmatch(r'#[0-9a-fA-F]{6}',problem.get('colorRGB','')):column.update(colorRGB=problem['colorRGB'],colorName=problem.get('colorName',''))
  require(isinstance(payload.get('contestStandings',{}).get('standingsHeader'),dict),'Native standings are unavailable.',503)
 info=access(app)
 handler.send(200,{'contestId':cid,'mode':mode,'payload':payload,'checkedAt':stamp(),'displayUrl':info['origin']+'/standings/' if info.get('origin') else None})
 return True
