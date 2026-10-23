"""Private post-contest learning packages. Official results remain unchanged."""
from pathlib import Path
import base64,collections,difflib,hashlib,json,os,re,shutil,sqlite3,subprocess,tempfile,uuid,zipfile
from urllib.parse import parse_qs,urlsplit
from core import ROOT,require,stamp
from contests import write_json,read_json
from problem_difficulty import annotate
from test_team import is_test

FORMAT='LCPC-TEAM-LEARNING-2'
ID=re.compile(r'[a-f0-9]{32}')
TEAM=re.compile(r'team[1-9][0-9]{0,4}')
EXTENSIONS={'.cpp','.cc','.c','.java','.py','.txt','.md'}
MAX_PACKAGE=512*1024*1024
def export_ready(manager,row,snapshot):
 stopped=row['status'] in ('inactive','archived') and manager.data['active']!=row['id']
 finished=row['status']=='active' and snapshot['contest'].get('remainingSeconds')==0
 return (stopped or finished) and not snapshot['contest']['running']

def checked_file(base,relative):
 base=Path(base).resolve();path=base/relative
 require(not Path(relative).is_absolute() and '..' not in Path(relative).parts,'Invalid package path')
 require(path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(base),'Package file unavailable',404)
 return path

def activity(state):
 path=Path(state)/'participant-activity/activity.sqlite3'
 if not path.exists():return {}
 result={}
 # No telemetry constructor, pruning, client session or IP data is exported.
 with sqlite3.connect('file:'+str(path.resolve())+'?mode=ro',uri=True) as db:
  for team,event,count,first,last in db.execute("SELECT team,event,count(*),min(created),max(created) FROM events WHERE team!='' AND event IN ('login','session.restored','page.open','page.navigate','action.clicked','file.selected','form.submitted') GROUP BY team,event"):
   row=result.setdefault(team,{'events':{},'first':first,'last':last});row['events'][event]=count;row['first']=min(row['first'],first);row['last']=max(row['last'],last)
 return result

def participants(snapshot,observed):
 runs=[r for r in snapshot.get('runs',[]) if not r.get('deleted') and not is_test(r)]
 clarifications=[c for c in snapshot.get('clarifications',[]) if not c.get('deleted') and not is_test(c)]
 return [t for t in snapshot.get('teams',[]) if TEAM.fullmatch(t.get('login','')) and not is_test(t) and (any(r['team']==t['login'] for r in runs) or any(c['team']==t['login'] for c in clarifications) or t['login'] in observed)]

def material(store,problem):
 root=store.base/'learning-materials';path=root/'catalog.json';catalog=read_json(path) if path.exists() else {};entry=catalog.get(problem['id'],{})
 # Existing imported organizer materials are recognized only when their own
 # editorial explicitly identifies the current problem title and letter.
 legacy=store.base/'organizer-materials';editorial=legacy/'EDITORIAL_AND_SOLUTIONS.md';text=editorial.read_text() if editorial.is_file() else ''
 imported=('| '+problem['letter']+' '+problem['name']+' |') in text
 result={}
 for kind in ('solution','editorial'):
  saved=entry.get(kind)
  if saved:
   file=checked_file(root,saved['file']);require(hashlib.sha256(file.read_bytes()).hexdigest()==saved['sha256'],'Reference material checksum changed',409);result[kind]={'file':file,'filename':saved['filename'],'provenance':'Organizer-uploaded current reference'}
  elif imported:
   if kind=='solution':
    file=legacy/'solutions'/(problem['letter']+'.cpp')
    if file.is_file() and not file.is_symlink():result[kind]={'file':file,'filename':problem['letter']+'.cpp','provenance':'Imported organizer reference; current material, not re-executed by this export'}
   else:
    match=re.search(r'^## '+re.escape(problem['letter'])+r' - Reference reasoning\s*\n(.*?)(?=^## |\Z)',text,re.M|re.S)
    if match:result[kind]={'text':match[1].strip(),'filename':'editorial.md','provenance':'Imported organizer explanation'}
 return result

def summary(manager,row):
 snapshot=annotate(manager.bridge_for(row).snapshot(),manager.store_for(row));observed=activity(row['state']);teams=participants(snapshot,observed)
 root=Path(row['state'])/'admin-dashboard/learning-reports';exports=[]
 if root.exists():
  for path in root.glob('*/manifest.json'):
   if not ID.fullmatch(path.parent.name):continue
   value=read_json(path)
   if value.get('complete') and value.get('format')==FORMAT:exports.append({k:value[k] for k in ('id','created','contestId','teams','bytes')})
 return {'contestId':row['id'],'eligibleTeams':[{'login':t['login'],'name':t['name'],'attempts':sum(not r.get('deleted') and r['team']==t['login'] for r in snapshot.get('runs',[]))} for t in teams],
  'ignoredTeams':len([t for t in snapshot.get('teams',[]) if not is_test(t)])-len(teams),'ready':export_ready(manager,row,snapshot),
  'problems':[{**p,'referenceAvailable':'solution' in material(manager.store_for(row),p),'editorialAvailable':'editorial' in material(manager.store_for(row),p)} for p in snapshot.get('problems',[])],
  'exports':sorted(exports,key=lambda x:x['created'],reverse=True)[:50],'job':manager.job}

def save_material(store,snapshot,data):
 problem=next((p for p in snapshot['problems'] if p['id']==data.get('problemId')),None);require(problem,'Choose a current problem')
 kind=data.get('kind');require(kind in ('solution','editorial'),'Choose reference code or explanation')
 filename=data.get('filename','');require(isinstance(filename,str) and 1<=len(filename)<=150 and filename==Path(filename).name and not re.search(r'[\x00-\x1f/\\]',filename),'Invalid reference filename')
 require(Path(filename).suffix.lower() in (EXTENSIONS if kind=='solution' else {'.md','.txt'}),'Unsupported reference file')
 try:body=base64.b64decode(data.get('base64',''),validate=True);text=body.decode('utf-8')
 except (ValueError,UnicodeError):require(False,'Upload UTF-8 text or source code')
 require(0<len(body)<=512*1024 and '\0' not in text,'Reference text must be 1 byte to 512 KiB')
 root=store.base/'learning-materials';root.mkdir(mode=0o700,exist_ok=True);catalog=read_json(root/'catalog.json') if (root/'catalog.json').exists() else {}
 name=uuid.uuid4().hex+Path(filename).suffix.lower();file=root/name;file.write_bytes(body);file.chmod(0o600)
 catalog.setdefault(problem['id'],{})[kind]={'file':name,'filename':filename,'sha256':hashlib.sha256(body).hexdigest(),'updated':stamp()};write_json(root/'catalog.json',catalog)

def extract_native(state,target):
 from runtime_paths import java_executable
 command=[java_executable(),'-Djdk.crypto.KeyAgreement.legacyKDF=true','-Djava.awt.headless=true','-Dlcpc.denyExecution=true','-Xmx768m','-cp',str(ROOT/'lcpc/build')+':'+str(ROOT/'lib/*')+':'+str(state/'wti/WebTeamInterface-1.1.jar'),'OfflineLearningEvidence',str(state),str(target)]
 result=subprocess.run(command,cwd=ROOT,capture_output=True,timeout=90)
 require(result.returncode==0 and (target/'evidence.json').exists(),'Saved native evidence could not be read. The contest must remain stopped; inspect its profile before retrying.',409)
 return read_json(target/'evidence.json')

def safe_name(name):
 suffix=Path(name).suffix.lower();return suffix if re.fullmatch(r'\.[a-z0-9]{1,8}',suffix) else '.txt'

def copy_evidence(descriptor,source,target,relative):
 if not descriptor.get('available'):return {'available':False}
 file=checked_file(source,descriptor['path']);body=file.read_bytes()
 require(hashlib.sha256(body).hexdigest()==descriptor['sha256'],'Saved evidence checksum mismatch',409)
 dest=target/relative;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(body)
 return {'available':True,'path':str(relative),'bytes':len(body),'sha256':descriptor['sha256']}

def text_preview(root,item,limit=8000):
 if not item.get('available'):return None
 file=checked_file(root,item['path']);body=file.read_bytes();return {'text':body[:limit].decode('utf-8',errors='replace'),'truncated':len(body)>limit,'bytes':len(body)}

def advice(runs):
 verdicts=collections.Counter(r.get('verdict','Pending') for r in runs if not r.get('deleted'));tips=[]
 for value in verdicts:
  key=value.lower()
  if 'wrong' in key:tips.append('For Wrong Answer attempts, trace boundary cases and compare the algorithm with the reference explanation. A textual code difference alone does not establish the cause.')
  elif 'compil' in key:tips.append('Resolve the saved compiler diagnostics first and compile using the configured contest language version.')
  elif 'runtime' in key or 'run-time' in key:tips.append('Inspect bounds, invalid memory access and saved execution stderr. Do not infer an exact failing line unless the retained evidence identifies it.')
  elif 'time limit' in key:tips.append('Review asymptotic complexity and worst-case inputs against the problem constraints.')
  elif 'memory' in key:tips.append('Review peak allocations and data structure sizes against the memory limit.')
 if any(r.get('accepted') and r.get('final') for r in runs):tips.append('Use accepted work as a baseline. Explain why it is correct, estimate its complexity and test edge cases before simplifying it.')
 if any(not r.get('final') for r in runs):tips.append('Some attempts have no final decision. Treat their outcomes as pending, not as a success or failure.')
 if not runs:tips.append('No retained submissions were found. This report records verified activity or questions only; there is no code outcome to assess.')
 return tips

def decisions(store,contest_id):
 result={}
 with store.db() as db:
  for row in db.execute("SELECT created,actor,event,details FROM audit WHERE outcome='success' AND event IN ('run.approve','judgement','run.rejudge') ORDER BY id"):
   value=json.loads(row['details'])
   if value.get('contestId')!=contest_id:continue
   if type(value.get('site')) is not int or type(value.get('number')) is not int:continue
   result.setdefault((value['site'],value['number']),[]).append({'at':row['created'],'actor':row['actor'],'action':row['event'],'reason':str(value.get('reason',''))})
 return result

def build_team(store,snapshot,team,observed,native,native_root,target,exported):
 login=team['login'];runs=sorted([r for r in snapshot['runs'] if r['team']==login and not r.get('deleted')],key=lambda r:(r.get('elapsedMinutes',0),r['site'],r['number']))
 evidence={(r['site'],r['number']):r for r in native['runs']};problem_data={p['id']:p for p in native['problems']};problems={p['id']:p for p in snapshot['problems']}
 report={'format':FORMAT,'contest':snapshot['contest'],'team':{'login':login,'name':team['name']},'exportedAt':exported,'timezone':store.schedule_preferences()['timeZone'],'attempts':len(runs),'acceptedAttempts':sum(bool(r.get('accepted') and r.get('final')) for r in runs),'solvedProblems':len({r['problemId'] for r in runs if r.get('accepted') and r.get('final')}),'activity':observed.get(login,{}),'clarifications':[c for c in snapshot.get('clarifications',[]) if c['team']==login and not c.get('deleted')],'problems':[],'advice':advice(runs)}
 for pid in dict.fromkeys(r.get('problemId') for r in runs):
  p=problems.get(pid)
  if not p:continue
  base=Path('problems')/(p['letter']+'-'+hashlib.sha256(pid.encode()).hexdigest()[:8]);current=problem_data.get(pid,{});entry={**p,'attempts':[],'reference':{},'resources':[],'tests':[],'validator':current.get('validator','Unknown'),'historicRevisionAvailable':False}
  for r in store.resources():
   if r['problem'] not in (pid,'__contest__') or not r['published']:continue
   file=checked_file(store.uploads,r['id']);body=file.read_bytes();require(hashlib.sha256(body).hexdigest()==r['sha256'],'Problem resource checksum changed',409)
   rel=base/'statements'/(r['id']+safe_name(r['filename']));dest=target/rel;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(body);entry['resources'].append({'path':str(rel),'filename':r['filename'],'kind':r['kind'],'language':r['language'],'mime':r['mime']})
  for kind,m in material(store,p).items():
   body=m['text'].encode() if 'text' in m else m['file'].read_bytes();rel=base/'reference'/('reference'+safe_name(m['filename']) if kind=='solution' else 'editorial.md');dest=target/rel;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(body)
   entry['reference'][kind]={'path':str(rel),'available':True,'bytes':len(body),'filename':m['filename'],'provenance':m['provenance'],'preview':body[:65536].decode('utf-8',errors='replace'),'truncated':len(body)>65536}
  for test in current.get('tests',[]):
   n=test['number'];entry['tests'].append({'number':n,'input':copy_evidence(test['input'],native_root,target,base/'tests'/f'{n:04}.in'),'expected':copy_evidence(test['expected'],native_root,target,base/'tests'/f'{n:04}.ans')})
  for run in [r for r in runs if r.get('problemId')==pid]:
   raw=evidence.get((run['site'],run['number']),{});require(not raw or raw['team']==login and raw['problemId']==pid,'Run evidence does not belong to this team',409)
   attempt={**run,'sources':[],'reports':[],'history':raw.get('history',[]),'cases':raw.get('cases',{}),'comparisonAvailable':False};runbase=base/'attempts'/f"{run['site']}-{run['number']}"
   for i,source in enumerate(raw.get('sources',[]),1):
    item=copy_evidence(source,native_root,target,runbase/'source'/(str(i)+safe_name(source.get('name',''))));item.update(name=source.get('name','Source'),preview=text_preview(target,item,65536));attempt['sources'].append(item)
   for i,saved in enumerate(raw.get('reports',[]),1):
    projected={k:v for k,v in saved.items() if k!='outputs'};projected['outputs']={}
    for key,item in saved.get('outputs',{}).items():
     output=copy_evidence(item,native_root,target,runbase/'judge-reports'/str(i)/(key+'.txt'));output['preview']=text_preview(target,output);projected['outputs'][key]=output
    attempt['reports'].append(projected)
   reference=entry['reference'].get('solution')
   if reference and attempt['sources']:
    original=attempt['sources'][0]['preview']['text'];diff=''.join(difflib.unified_diff(reference['preview'].splitlines(True),original.splitlines(True),fromfile='current-reference',tofile='team-source'))
    rel=runbase/'reference-vs-team.diff';(target/rel).write_text(diff,encoding='utf-8');attempt.update(comparisonAvailable=True,comparisonPath=str(rel),comparisonPreview=diff[:16000],comparisonTruncated=len(diff)>16000 or reference['truncated'] or attempt['sources'][0]['preview']['truncated'])
   failed=[c['number'] for c in raw.get('cases',{}).get('tests',[]) if c.get('status')=='Failed'];selected=(failed or [t['number'] for t in entry['tests']])[:3];attempt['examples']=[]
   for n in selected:
    case=next((t for t in entry['tests'] if t['number']==n),None)
    if case:attempt['examples'].append({'number':n,'input':text_preview(target,case['input'],2000),'expected':text_preview(target,case['expected'],2000),'historicAssociationAvailable':False})
   entry['attempts'].append(attempt)
  report['problems'].append(entry)
 write_json(target/'report.json',report);return report

def package_tree(folder,target):
 with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as archive:
  for file in sorted(folder.rglob('*')):
   if file.is_file():archive.write(file,str(file.relative_to(folder)))
 target.chmod(0o600)

def generate(manager,row):
 from contest_runtime import runtime_lock,controller
 from contest_exports import BUNDLED_PYTHON
 state=Path(row['state']);store=manager.store_for(row);snapshot=annotate(manager.bridge_for(row).snapshot(fresh=True),store)
 require(export_ready(manager,row,snapshot),'Finish the contest or stop its server before creating learning reports',409)
 observed=activity(state);teams=participants(snapshot,observed);require(teams,'No teams with retained participation were found',409)
 root=store.base/'learning-reports';root.mkdir(mode=0o700,exist_ok=True);export_id=uuid.uuid4().hex;out=root/export_id;out.mkdir(mode=0o700)
 try:
  def progress(completed,total,message):
   manager.job.update(message=message,progress={'completed':completed,'total':total,'percent':90+int(completed/total*10)})
   write_json(manager.base/'job.json',manager.job)
  with runtime_lock(),tempfile.TemporaryDirectory(prefix='learning-',dir=root) as tmp:
   manager.job.update(message='Capturing saved contest evidence',progress={'percent':0});write_json(manager.base/'job.json',manager.job)
   require(manager.data['active']==row['id'] or not controller(state).pid_for('server'),'The native server is still running outside the active workspace. Review service state before export.',409)
   temp=Path(tmp);raw=temp/'native';raw.mkdir();native=extract_native(state,raw);payload=temp/'package';payload.mkdir();created=stamp();entries=[]
   current=annotate(manager.bridge_for(row).snapshot(fresh=True),store)
   for key in ('contest','problems','runs','clarifications'):
    require(current.get(key)==snapshot.get(key),'Contest evidence changed during capture. Retry export when judging is stable.',409)
   from learning_replay import run as replay,attach as attach_replay
   replay_mapping,replay_cache,_=replay(manager,row,native,raw,snapshot)
   progress(1,len(teams)+2,'Isolated analysis completed; creating detailed PDFs')
   for index,team in enumerate(teams,1):
    progress(index,len(teams)+2,f"Preparing team {index} of {len(teams)}")
    teamroot=payload/team['login'];teamroot.mkdir();report=build_team(store,snapshot,team,observed,native,raw,teamroot,created)
    attach_replay(report,teamroot,replay_mapping,replay_cache)
    notes=decisions(manager.app.store,row['id'])
    for problem in report['problems']:
     for attempt in problem['attempts']:attempt['organizerDecisions']=notes.get((attempt['site'],attempt['number']),[])
    write_json(teamroot/'report.json',report)
    result=subprocess.run([str(BUNDLED_PYTHON),str(ROOT/'lcpc/admin/learning_pdf.py'),str(teamroot/'report.json'),str(teamroot/'learning-report.pdf')],capture_output=True,timeout=120)
    require(result.returncode==0 and (teamroot/'learning-report.pdf').exists(),'Team PDF generation failed. No incomplete package was published.',503)
    entries.append({'login':team['login'],'name':team['name'],'attempts':report['attempts'],'solvedProblems':report['solvedProblems']})
    (teamroot/'README.txt').write_text('This folder contains only this team\'s retained attempts and questions, plus current organizer references and test data for attempted problems. Full original files accompany the PDF. Current reference tests are not proven historic data for older attempts. Historic saved execution output has no per-test association. The analysis-replay folder contains newly captured per-test output with explicit input/output association. Team code was compiled and executed in the isolated Linux analysis sandbox; official submissions were not rejudged. Textual diffs do not prove algorithmic equivalence or locate a bug. See report.json for full structured evidence.\n')
    require(sum(f.stat().st_size for f in payload.rglob('*') if f.is_file())<=MAX_PACKAGE,'Learning package exceeds 512 MiB. Reduce retained materials before exporting.',413)
    package_tree(teamroot,out/(team['login']+'.zip'))
    progress(index+1,len(teams)+2,f"Completed team {index} of {len(teams)}")
   manifest={'format':FORMAT,'id':export_id,'created':created,'contestId':row['id'],'teams':entries,'complete':True}
   write_json(payload/'manifest.json',manifest);(payload/'README.txt').write_text('Organizer master package. Each team folder is independent; share only the appropriate team folder or its individual ZIP. Teams without retained attempts, questions or verified interactive activity are omitted. Diagnostic test accounts are excluded. No passwords, tokens, device addresses or other teams\' source are included in a team folder.\n')
   package_tree(payload,out/'all-teams.zip');shutil.copytree(payload,out/'teams');manifest['bytes']=(out/'all-teams.zip').stat().st_size;manifest['sha256']=hashlib.sha256((out/'all-teams.zip').read_bytes()).hexdigest();write_json(out/'manifest.json',manifest)
   progress(len(teams)+2,len(teams)+2,'Learning packages ready')
  return {'exportId':export_id,'teams':len(entries),'filename':row['id']+'-team-learning.zip'}
 except Exception:shutil.rmtree(out,ignore_errors=True);raise

def route(handler,path,data=None):
 if path not in ('/api/learning-reports','/api/learning-reports/material','/api/learning-reports/generate','/api/learning-reports/download'):return False
 handler.user('owner');app=handler.app;manager=app.manager;row=manager.selected()
 if data is None:
  require(path=='/api/learning-reports','Method not allowed',405);q=parse_qs(urlsplit(handler.path).query);require(q.get('contestId')==[row['id']],'The selected contest changed',409);handler.send(200,summary(manager,row));return True
 manager.guard(data)
 if path.endswith('/material'):
  require(row['status']!='archived','Unarchive before changing reference materials',409);snapshot=manager.bridge_for(row).snapshot();save_material(manager.store_for(row),snapshot,data);app.store.audit(handler.actor,'learning.reference-uploaded','success',details={'contestId':row['id'],'problemId':data['problemId'],'kind':data['kind']});handler.send(200,{'ok':True});return True
 if path.endswith('/generate'):
  handler.send(202,manager.start_job('learning',row['id'],handler.actor));return True
 require(path.endswith('/download'),'Method not allowed',405);export_id=data.get('exportId','');team=data.get('team','all');require(isinstance(export_id,str) and ID.fullmatch(export_id),'Invalid learning export')
 folder=manager.store_for(row).base/'learning-reports'/export_id;manifest=read_json(checked_file(folder,'manifest.json'));require(manifest.get('complete') and manifest.get('contestId')==row['id'],'Learning export unavailable',404)
 require(isinstance(team,str) and (team=='all' or team in {t['login'] for t in manifest['teams']}),'Team not in this export',404);name='all-teams.zip' if team=='all' else team+'.zip';file=checked_file(folder,name)
 app.store.audit(handler.actor,'learning.download','success',details={'contestId':row['id'],'exportId':export_id,'team':team});handler.send(200,file.read_bytes(),'application/zip',{'Content-Disposition':'attachment; filename="'+row['id']+'-'+name+'"'});return True
