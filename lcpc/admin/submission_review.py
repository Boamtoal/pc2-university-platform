"""Scoped, read-only organizer review data. Never executes or rejudges source."""
from urllib.parse import parse_qs, urlsplit
from core import require, stamp

def query(handler, required=False):
 values=parse_qs(urlsplit(handler.path).query,keep_blank_values=True)
 if required or 'contestId' in values:
  ids=values.get('contestId',[])
  require(len(ids)==1 and ids[0]==handler.app.manager.data['selected'],'The selected contest changed. Open this review from the current workspace.',409)
  require(not handler.app.manager.busy(),'A contest operation is in progress. Refresh the review when it finishes.',409)
 return values

def route(handler,path):
 if path not in ('/api/submission-review','/api/problem-review'):return False
 handler.user();app=handler.app;values=query(handler,required=True);snapshot=app.bridge.snapshot()
 contest={'id':app.manager.data['selected'],'title':snapshot['contest']['title']}
 if path=='/api/problem-review':
  ids=values.get('problemId',[]);require(len(ids)==1 and len(ids[0])<=240,'Choose one problem')
  problem=next((p for p in snapshot.get('problems',[]) if p['id']==ids[0]),None);require(problem,'Problem not found',404)
  handler.send(200,{'contest':contest,'problem':problem,'resources':[r for r in app.resources.resources() if r['problem']==problem['id']],'checkedAt':stamp(),'timeZone':app.resources.schedule_preferences()['timeZone']});return True
 try:
  require(len(values.get('number',[]))==1 and len(values.get('site',[]))==1,'Choose one submission')
  number=int(values['number'][0]);site=int(values['site'][0])
 except ValueError:require(False,'Invalid submission')
 require(1<=number<=2147483647 and 1<=site<=999,'Invalid submission')
 run=next((r for r in snapshot.get('runs',[]) if r['number']==number and r['site']==site),None);require(run,'Submission not found',404)
 evidence=app.bridge.call('diagnostics',{'number':number,'site':site})
 problem=next((p for p in snapshot.get('problems',[]) if p['id']==run.get('problemId')),None)
 app.store.audit(handler.actor,'submission.review','success',details={'number':number,'site':site,'contestId':contest['id']})
 handler.send(200,{'contest':contest,'submission':run,'problem':problem,'evidence':evidence,'checkedAt':stamp(),'timeZone':app.resources.schedule_preferences()['timeZone']});return True
