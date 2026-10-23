"""Independent contest workspaces and a single active PC2 runtime.
Authentication remains in the original control store. Drafts never copy runs or passwords.
"""
from pathlib import Path
import contextlib,copy,fcntl,hashlib,json,os,re,secrets,shutil,subprocess,sys,threading,time,uuid,zipfile
from core import ROOT,Store,Bridge,Error,require,stamp,password_policy
from test_team import LOGIN as TEST_LOGIN,NUMBER as TEST_NUMBER,new_account,ensure_draft,official

def write_json(path,data):
 path.parent.mkdir(parents=True,exist_ok=True,mode=0o700);tmp=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp');tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2));tmp.chmod(0o600);tmp.replace(path)
def read_json(path):return json.loads(path.read_text())
def clean(value,maxlen=200):
 require(isinstance(value,str) and 0<len(value.strip())<=maxlen and not any(ord(c)<32 for c in value),'Invalid text');return value.strip()

class DraftBridge:
 process=None
 def __init__(self,state,ensure_test=True):
  self.state=Path(state);self.path=self.state/'admin-dashboard/draft.json'
  if ensure_test:ensure_draft(self.path)
 def snapshot(self,fresh=False):
  d=read_json(self.path);c=d['contest'];return {'contest':{**c,'penaltyMinutes':d['penaltyMinutes'],'running':False,'elapsedSeconds':0,'remainingSeconds':c['lengthSeconds']},'teams':[{k:v for k,v in t.items() if k!='password'}|{'online':False} for t in d['teams']],'problems':[{k:v for k,v in p.items() if k not in ('dataDirectory','sourceId')} for p in d['problems']],'languages':[{'name':x['name'],'active':x['active']} for x in d['languages']],'runs':[],'clarifications':[],'judgements':[],'standings':{},'judging':{'mode':d['workflow'],'preliminaryResultsCounted':False,'preliminaryNotifications':False},'updatedAt':stamp()}
 def call(self,op,args=None):
  a=args or {};d=read_json(self.path)
  if op=='snapshot':return self.snapshot()
  if op=='contest.update':d['contest'].update({k:v for k,v in a.items() if k in ('title','shortName','freezeRemaining','thawed','scheduledStart')});d['timeZone']=a.get('scheduleTimeZone',d['timeZone'])
  elif op=='judging.workflow':d['workflow']=a['mode'];[p.update(judgingMode=a['mode']) for p in d['problems']]
  elif op=='clock.extend':d['contest']['lengthSeconds']+=a['seconds']
  elif op=='team.create':
   password_policy(a['password']);number=max([t['number'] for t in official(d['teams'])]+[0])+1;require(number<TEST_NUMBER,'Team capacity reached');d['teams'].append({'login':'team'+str(number),'number':number,'name':a['name'],'password':a['password'],'enabled':True,'visible':True})
  elif op=='team.update':
   require(a['login']!=TEST_LOGIN,'Manage the reserved test account from Participant test & access',409)
   t=next((t for t in d['teams'] if t['login']==a['login']),None);require(t,'Team not found',404);t.update({k:a[k] for k in ('name','enabled','visible')})
   if a.get('password'):t['password']=a['password']
  elif op=='problem.update':
   p=next((p for p in d['problems'] if p['id']==a['id']),None);require(p,'Problem not found',404);p.update({k:a[k] for k in ('name','timeLimit','memoryLimit','active')});p.update({k:a[k] for k in ('colorName','colorRGB') if k in a})
  elif op=='problem.create':
   require(not any(p['letter']==a['letter'] for p in d['problems']),'Problem letter is already in use',409)
   directory=Path(a['directory']);require(directory.parent==self.state/'admin-dashboard/judge-data','Invalid private data directory')
   profile=next((p for p in d['problems'] if p['id']==a.get('template')),None)
   pid=uuid.uuid4().hex;d['problems'].append({'id':pid,'shortName':'p'+pid[:12],'letter':a['letter'],'name':a['name'],'timeLimit':a['timeLimit'],'memoryLimit':a['memoryLimit'],'active':False,'tests':len(list(directory.glob('*.in'))),'dataDirectory':directory.name,'sourceId':profile.get('sourceId',profile['id']) if profile else '', 'judgingMode':d['workflow'],'colorName':a.get('colorName',''),'colorRGB':a.get('colorRGB','')});write_json(self.path,d);return {'ok':True,'id':pid}
  else:raise Error(409,'This is an offline workspace. Activate it from Contests before using live controls.')
  write_json(self.path,d);return {'ok':True}
 def close(self):pass

class ReadOnlyBridge:
 process=None
 def __init__(self,state):self.state=Path(state)
 def snapshot(self,fresh=False):return read_json(self.state/'admin-dashboard/last-snapshot.json')
 def call(self,*_):raise Error(409,'This contest is offline. Activate it before changing native PC2 data.')
 def close(self):pass

class ContestManager:
 def __init__(self,app,base=None):
  self.app=app;self.lock=threading.RLock();self.job=None
  live=app.store.state.is_relative_to(ROOT/'.local/instances')
  self.base=Path(base) if base else (ROOT/'.local/contest-manager' if live else app.store.state/'contest-manager')
  self.base.mkdir(mode=0o700,parents=True,exist_ok=True);self.registry=self.base/'registry.json';self.instances=(ROOT/'.local/instances' if live else self.base/'instances');self.instances.mkdir(mode=0o700,exist_ok=True)
  if not self.registry.exists():write_json(self.registry,{'selected':app.store.state.name,'active':app.store.state.name,'contests':[{'id':app.store.state.name,'state':str(app.store.state),'status':'active','created':stamp()}]})
  self.data=read_json(self.registry);jobfile=self.base/'job.json'
  if jobfile.exists():
   self.job=read_json(jobfile)
   if self.job['status']=='running':self.job.update(status='failed',message='The previous dashboard stopped during this job. Review contest and service state before retrying.');write_json(jobfile,self.job)
  self.stores={str(app.store.state):app.store};self.bridges={}
  if self.data['active']==app.store.state.name:self.bridges[app.store.state.name]=app.bridge
  # A restart retains the selected workspace; identity and sessions stay central.
  self.select(self.data['selected'],initial=True)
 def save(self):write_json(self.registry,self.data)
 def row(self,cid):
  row=next((r for r in self.data['contests'] if r['id']==cid),None);require(row,'Contest not found',404);return row
 def store_for(self,row):
  key=row['state']
  if key not in self.stores:self.stores[key]=Store(key)
  return self.stores[key]
 def bridge_for(self,row):
  cid=row['id']
  if cid not in self.bridges:
   state=Path(row['state']);self.bridges[cid]=Bridge(state) if self.data['active']==cid else (ReadOnlyBridge(state) if (state/'secured').exists() else DraftBridge(state,ensure_test=row['status']!='archived'))
  return self.bridges[cid]
 def selected(self):return self.row(self.data['selected'])
 def select(self,cid,initial=False):
  require(initial or not self.busy(),'A contest operation is already in progress',409);row=self.row(cid)
  self.app.bridge=self.bridge_for(row);self.app.resources=self.store_for(row);self.data['selected']=cid
  if not initial:self.save()
 def busy(self):return bool(self.job and self.job['status']=='running')
 def guard(self,data,mutation=True):
  require(not self.busy(),'A contest operation is in progress. Wait for it to finish.',409)
  if mutation:require(data.get('contestId')==self.data['selected'],'The selected contest changed. Refresh before continuing.',409)
 def listing(self):
  rows=[]
  for row in self.data['contests']:
   state=Path(row['state']);snapshot={};unavailable=False
   if row['id']==self.data['selected']:
    try:snapshot=(getattr(self.app.bridge,'cached',None) or {}) if self.busy() else self.app.bridge.snapshot()
    except Exception:unavailable=True
   elif (state/'secured').exists() and (state/'admin-dashboard/last-snapshot.json').exists():snapshot=read_json(state/'admin-dashboard/last-snapshot.json')
   elif (state/'admin-dashboard/draft.json').exists():snapshot=DraftBridge(state,ensure_test=row['status']!='archived').snapshot()
   rows.append({k:v for k,v in row.items() if k!='state'}|{'unavailable':unavailable,'title':snapshot.get('contest',{}).get('title',row['id']),'teams':len(official(snapshot.get('teams',[]))),'problems':len(snapshot.get('problems',[])),'submissions':len(official(snapshot.get('runs',[]))),'durationSeconds':snapshot.get('contest',{}).get('lengthSeconds',0)})
  backups=[]
  for file in sorted((self.base/'backups').glob('*/manifest.json'),reverse=True):
   info=read_json(file);package=file.parent/'backup.zip'
   if package.exists():backups.append({'id':file.parent.name,'contestId':info['contestId'],'created':info['created'],'bytes':package.stat().st_size})
  return {'backups':backups,'contests':rows,'selected':self.data['selected'],'active':self.data['active'],'job':self.job,'singleActive':True}
 def create(self,a):
  title=clean(a.get('title'));short=clean(a.get('shortName'),80);slug=a.get('slug','');require(isinstance(slug,str) and re.fullmatch('[a-z0-9][a-z0-9-]{0,45}',slug),'Use a unique lowercase ID (letters, digits and hyphens)')
  require(not any(r['id']==slug for r in self.data['contests']) and not(self.instances/slug).exists(),'Contest ID already exists',409)
  require(type(a.get('durationMinutes')) is int and 1<=a['durationMinutes']<=1440,'Duration must be 1–1440 minutes');require(type(a.get('penaltyMinutes')) is int and 0<=a['penaltyMinutes']<=120,'Penalty must be 0–120 minutes');require(a.get('workflow') in ('automatic','review','human'),'Choose a judging workflow')
  require(a.get('copyProblems') in (True,False) and a.get('copyResources') in (True,False),'Choose template options');source=self.selected()
  source_state=Path(source['state']);dest=self.instances/slug;temp=self.instances/('.creating-'+uuid.uuid4().hex);temp.mkdir(mode=0o700)
  try:
   snap=copy.deepcopy(self.app.bridge.snapshot(fresh=True));draft_path=source_state/'admin-dashboard/draft.json'
   if source['id']==self.data['active']:
    template=self.app.bridge.call('template.export',{'includeProblems':a['copyProblems']});file=Path(template['path']).resolve();require(file.parent==source_state/'admin-dashboard/template-exports','Unexpected template path',409)
    require(hashlib.sha256(file.read_bytes()).hexdigest()==template['sha256'],'Template hash mismatch',409);languages=template['languages']
   else:
    cached=source_state/'admin-dashboard/clone-template.json'
    require(cached.exists() or draft_path.exists(),'This offline contest has no saved template. Activate and deactivate it once before cloning.',409)
    old=read_json(cached if cached.exists() else draft_path);file=source_state/'admin-dashboard'/('clone-template.bin' if cached.exists() else 'template.bin');template={'sha256':old['templateSha256']};languages=old['languages']
   (temp/'admin-dashboard').mkdir(mode=0o700);shutil.copyfile(file,temp/'admin-dashboard/template.bin')
   problems=(copy.deepcopy(read_json(draft_path)['problems']) if draft_path.exists() and not(source_state/'secured').exists() else snap['problems']) if a['copyProblems'] else []
   for p in problems:
    if p.get('dataDirectory'):shutil.copytree(source_state/'admin-dashboard/judge-data'/p['dataDirectory'],temp/'admin-dashboard/judge-data'/p['dataDirectory'])
   draft={'format':1,'contest':{'title':title,'shortName':short,'lengthSeconds':a['durationMinutes']*60,'freezeRemaining':'00:00:00','thawed':False,'scheduledStart':''},'teams':[new_account()],'problems':problems,'languages':languages,'templateSha256':template['sha256'],'workflow':a['workflow'],'penaltyMinutes':a['penaltyMinutes'],'timeZone':self.app.resources.schedule_preferences()['timeZone']}
   write_json(temp/'admin-dashboard/draft.json',draft)
   resources=Store(temp);resources.save_schedule_preferences(self.app.resources.schedule_preferences())
   from participant_identity import inherit
   inherit(self.app.resources,resources)
   from problem_difficulty import inherit as inherit_difficulties
   inherit_difficulties(self.app.resources,resources,problems)
   if a['copyResources']:
    ids={p['id'] for p in problems}|{'__contest__'}
    for r in self.app.resources.resources():
     if r['problem'] not in ids:continue
     import base64
     resources.upload({**r,'base64':base64.b64encode((self.app.resources.uploads/r['id']).read_bytes()).decode()},trusted=True)
   # Instructions/branding are shared organization defaults; problem files are per contest.
   shutil.copytree(ROOT/'lcpc/public-instructions',temp/'participant-resources/instructions')
   (temp/'participant-resources/problems').mkdir(parents=True);shutil.copyfile(ROOT/'lcpc/public-problems/index.html',temp/'participant-resources/problems/index.html')
   for handler in list(resources.logger.handlers):handler.close();resources.logger.removeHandler(handler)
   temp.rename(dest)
   row={'id':slug,'state':str(dest),'status':'draft','created':stamp(),'template':source['id']};self.data['contests'].append(row);self.save();return {'ok':True,'id':slug}
  except Exception:shutil.rmtree(temp,ignore_errors=True);raise
 def start_job(self,kind,cid,actor):
  require(not self.busy(),'A contest operation is already in progress',409);row=self.row(cid)
  if kind=='activate':
   active=self.data['active']
   if active:
    self.app.store.audit(actor,'contest.activation-blocked','denied',details={'id':cid,'activeContest':active},alert=('warning','A second contest activation was blocked. Deactivate '+active+' first.'))
    raise Error(409,'Another contest is active: '+str(active)+'. Deactivate it first. A paused clock still belongs to an active contest.')
   require(row['status'] not in ('archived','error') and not(Path(row['state'])/'admin-dashboard/installing').exists(),'Unarchive or recover this contest before activation',409)
   if row['status']=='draft':
    snap=DraftBridge(row['state']).snapshot();require(official(snap['teams']) and any(p['active'] and p['tests']>0 for p in snap['problems']),'Add teams and at least one active problem with judge tests before activation',409)
  elif kind=='recover':
   require(row['status'] in ('error','activating'),'This contest has no failed activation to recover',409)
   require(self.data['active'] in (None,cid),'Another contest owns the active server',409)
  elif kind=='deactivate':
   require(self.data['active']==cid,'This contest is not active',409);snap=self.bridge_for(row).snapshot(fresh=True);require(not snap['contest']['running'],'Pause the contest before deactivating it',409);require(all(r['deleted'] or r['final'] for r in snap['runs']),'Finalize all pending submissions before deactivation',409)
  elif kind=='learning':
   from learning_reports import export_ready
   require(export_ready(self,row,self.bridge_for(row).snapshot()),'Finish the contest or stop its server before creating learning reports',409)
  elif kind=='backup':require(self.data['active']!=cid,'Deactivate the contest before making a consistent full backup. Reports can be exported while it is active.',409)
  else:raise Error(400,'Unsupported contest job')
  job={'id':uuid.uuid4().hex,'kind':kind,'contest':cid,'status':'running','message':'Preparing '+kind,'created':stamp()};self.job=job;write_json(self.base/'job.json',job)
  self.app.store.audit(actor,'contest.'+kind,'requested',details={'id':cid})
  def execute():
   try:
    from contest_runtime import activate,deactivate,backup,recover
    from learning_reports import generate as learning
    result={'activate':activate,'deactivate':deactivate,'backup':backup,'recover':recover,'learning':learning}[kind](self,row)
    with self.lock:job.update(status='completed',message=kind.capitalize()+' completed',result=result);write_json(self.base/'job.json',job);self.save()
    self.app.store.audit(actor,'contest.'+kind,'success',details={'id':cid})
   except Exception as error:
    with self.lock:job.update(status='failed',message=str(error)[:1000]);write_json(self.base/'job.json',job);self.save()
    self.app.store.audit(actor,'contest.'+kind,'failed',details={'id':cid,'type':type(error).__name__},alert=('error','Contest '+kind+' failed. Inspect its status before retrying.'))
  self.worker=threading.Thread(target=execute,daemon=False);self.worker.start();return {'ok':True,'job':job}
 def release_stopped(self,cid):
  from contest_runtime import controller,other_server
  row=self.row(cid);state=Path(row['state']);ctl=controller(state)
  require(self.data['active']==cid,'This contest is not reserved',409)
  require(not any(ctl.pid_for(r) for r in ctl.ROLES),'Contest services are still running. Use Deactivate or recover the services first.',409)
  sys.path.insert(0,str(ROOT/'lcpc'));from infra import network,vm
  require(not(vm.ACTIVE.exists() and vm.ACTIVE.read_text().strip()==str(state)),'Stop the isolated judge before releasing this contest',409)
  network.stop(ctl);self.data['active']=None;row['status']='error' if (state/'server/profiles.properties').exists() and not(state/'admin-dashboard/last-snapshot.json').exists() else ('inactive' if (state/'secured').exists() else 'draft');self.bridges[cid].close() if cid in self.bridges else None
  self.bridges[cid]=ReadOnlyBridge(state) if (state/'secured').exists() else DraftBridge(state)
  if self.data['selected']==cid:self.app.bridge=self.bridges[cid]
  self.save();return {'ok':True}
 def archive(self,cid,archived):
  row=self.row(cid);require(self.data['active']!=cid,'Deactivate the contest before archiving it',409)
  row['status']=('archived' if archived else ('inactive' if (Path(row['state'])/'secured').exists() else 'draft'));self.save();return {'ok':True}
 def allow_native_mutation(self):require(self.selected()['status']!='archived','This contest is archived. Unarchive it before editing.',409)
 def close(self):
  if getattr(self,'worker',None) and self.worker.is_alive():self.worker.join()
  for bridge in self.bridges.values():bridge.close()
