"""Stage only team source/current inputs in the existing isolated Linux execution VM."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,tarfile,tempfile,uuid,time
from core import ROOT,require
from contests import write_json,read_json

def execution_status(case):
 if not case.get('executed'):return 'Compilation Error - not executed'
 return {0:'Completed',139:'Runtime Error',243:'Memory Limit Exceeded',244:'Time Limit Exceeded',245:'Time Limit Exceeded',246:'Sandbox Error'}.get(case.get('exit'),'Execution Error')

def prepare(native,root,snapshot,cache):
 problems={p['id']:p for p in native['problems']};settings={p['id']:p for p in snapshot['problems']};runs={(r['site'],r['number']):r for r in snapshot['runs']};tasks=[];mapping={}
 policy=hashlib.sha256((ROOT/'lcpc/infra/linux/sandbox-broker.py').read_bytes()).hexdigest()
 for run in native['runs']:
  saved=runs.get((run['site'],run['number']));sources=run.get('sources',[])
  if not saved or len(sources)!=1:continue
  p=settings[run['problemId']];tests=problems[run['problemId']]['tests'];language=saved.get('language','')
  mode='compile20' if 'C++20' in language else 'compile17' if 'C++17' in language else 'compilepython' if 'Python' in language else None
  if mode is None:continue
  material={'source':sources[0]['sha256'],'compiler':mode,'memory':p['memoryLimit'],'seconds':p['timeLimit'],'inputs':[(t['number'],t['input'].get('sha256')) for t in tests],'policy':policy,'schema':1}
  key=hashlib.sha256(json.dumps(material,sort_keys=True).encode()).hexdigest();mapping[(run['site'],run['number'])]=key
  if (cache/key/'manifest.json').is_file() or any(t['key']==key for t in tasks):continue
  tasks.append({'key':key,'source':sources[0]['path'],'compiler':mode,'memory':p['memoryLimit'],'seconds':p['timeLimit'],'tests':[{'number':t['number'],'inputSource':t['input']['path']} for t in tests if t['input'].get('available')],'label':str(run['site'])+'-'+str(run['number'])})
 return tasks,mapping

def run(manager,row,native,native_root,snapshot):
 from infra import vm
 cache=Path(row['state'])/'admin-dashboard/learning-replays';cache.mkdir(mode=0o700,parents=True,exist_ok=True)
 tasks,mapping=prepare(native,native_root,snapshot,cache)
 total=sum(len(t['tests']) for t in tasks)
 if not tasks:return mapping,cache,0
 vm.ensure_running();vm.guest(['sudo','test','-x','/opt/lcpc/bin/sandbox-broker.py'],capture_output=True,timeout=15)
 mounted=vm.guest(['findmnt','-rn','-t','virtiofs,9p'],capture_output=True,text=True,check=False,timeout=15)
 require(not mounted.stdout.strip(),'Learning replay refuses shared host mounts',409)
 vm.guest(['sudo','-u','pc2judge','sudo','-n','/opt/lcpc/bin/sandbox-broker.py','check'],capture_output=True,timeout=60)
 guest='/var/lib/pc2judge/learning-'+uuid.uuid4().hex
 with tempfile.TemporaryDirectory(prefix='replay-',dir=cache) as tmp:
  temp=Path(tmp);stage=temp/'stage';stage.mkdir();payload=[]
  for index,task in enumerate(tasks):
   directory='task-'+str(index);folder=stage/directory;folder.mkdir();shutil.copyfile(native_root/task['source'],folder/('source.py' if task['compiler']=='compilepython' else 'source.cpp'))
   for case in task['tests']:
    case['input']=str(case['number'])+'.in';shutil.copyfile(native_root/case['inputSource'],folder/case['input'])
   payload.append({**task,'directory':directory})
  write_json(stage/'tasks.json',{'tasks':payload});shutil.copyfile(ROOT/'lcpc/infra/linux/learning-replay.py',stage/'coordinator.py')
  archive=temp/'stage.tar'
  with tarfile.open(archive,'w') as tar:
   for file in stage.rglob('*'):
    if file.is_file():tar.add(file,arcname=str(file.relative_to(stage)))
  guest_archive='/tmp/'+Path(guest).name+'.tar';guest_result=guest_archive+'.results.tar'
  try:
   vm.lima(['copy',str(archive),vm.NAME+':'+guest_archive],capture_output=True,timeout=120)
   vm.guest(['sudo','mkdir','-p',guest],capture_output=True,timeout=15);vm.guest(['sudo','tar','xf',guest_archive,'-C',guest],capture_output=True,timeout=60);vm.guest(['sudo','chown','-R','pc2judge:pc2judge',guest],capture_output=True,timeout=15)
   from runtime_paths import executable
   command=[executable('limactl','LCPC_LIMA_BIN',(vm.LIMA,)),'shell',vm.NAME,'--','sudo','-u','pc2judge','python3','-I',guest+'/coordinator.py',guest]
   with (temp/'replay.log').open('wb') as log:
    process=subprocess.Popen(command,env=vm.ENV,stdout=subprocess.PIPE,stderr=log,text=True)
    try:
     for line in process.stdout:
      if not line.startswith('{'):continue
      progress=json.loads(line);done=progress['completed'];manager.job.update(message=f"Analysing run {progress['run']}, test {progress['case']} ({done}/{total})",progress={'completed':done,'total':total,'percent':min(90,int(done/max(total,1)*90))});write_json(manager.base/'job.json',manager.job)
     require(process.wait()==0,'Isolated test replay failed; no incomplete learning report was published',503)
    finally:
     if process.poll() is None:process.terminate();process.wait(timeout=15)
   # Archive only generated results. Source, inputs and guest credentials never return.
   dirs=[task['directory']+'/results' for task in payload]
   vm.guest(['sudo','tar','cf',guest_result,'-C',guest,*dirs],capture_output=True,timeout=60);vm.guest(['sudo','chmod','644',guest_result],capture_output=True,timeout=15)
   local=temp/'results.tar';vm.lima(['copy',vm.NAME+':'+guest_result,str(local)],capture_output=True,timeout=120)
   extracted=temp/'results';extracted.mkdir()
   with tarfile.open(local) as tar:
    require(sum(m.size for m in tar.getmembers())<=512*1024*1024,'Replay output exceeds 512 MiB',413)
    for member in tar.getmembers():
     name=Path(member.name);require(not name.is_absolute() and '..' not in name.parts and (member.isdir() or member.isfile()),'Unsafe replay result',409)
    tar.extractall(extracted,filter='data')
   for task in payload:
    source=extracted/task['directory']/'results';require((source/'manifest.json').is_file(),'Incomplete isolated replay',409)
    target=cache/task['key'];shutil.copytree(source,target);meta=read_json(target/'manifest.json');meta.update(sourceKey=task['key'],compiler=task['compiler'],memoryLimit=task['memory'],timeLimit=task['seconds']);write_json(target/'manifest.json',meta)
  finally:
   vm.guest(['sudo','rm','-rf','--',guest,guest_archive,guest_result],capture_output=True,check=False,timeout=30)
 return mapping,cache,total

def attach(report,teamroot,mapping,cache):
 from learning_reports import text_preview
 for problem in report['problems']:
  tests={t['number']:t for t in problem['tests']}
  for attempt in problem['attempts']:
   key=mapping.get((attempt['site'],attempt['number']));attempt['replayTests']=[]
   if not key or not (cache/key/'manifest.json').exists():continue
   meta=read_json(cache/key/'manifest.json');base=Path('analysis-replay')/(str(attempt['site'])+'-'+str(attempt['number']));target=teamroot/base;shutil.copytree(cache/key,target)
   attempt['replay']={k:v for k,v in meta.items() if k!='tests'}
   attempt['replay']['compilerStderr']=(target/'compiler.err').read_bytes()[:8000].decode('utf-8',errors='replace')
   for recorded in meta['tests']:
    n=recorded['number'];reference=tests.get(n)
    if not reference:continue
    output=target/(str(n)+'.out');error=target/(str(n)+'.err')
    item={**recorded,'executionStatus':execution_status(recorded),'input':text_preview(teamroot,reference['input'],400),'expected':text_preview(teamroot,reference['expected'],1200),'output':None,'stderr':None,'comparison':'Not executed'}
    if item['input']:item['input']['path']=reference['input']['path']
    if item['expected']:item['expected']['path']=reference['expected']['path']
    if output.is_file():
     body=output.read_bytes();item['output']={'text':body[:1200].decode('utf-8',errors='replace'),'truncated':len(body)>1200,'path':str(base/output.name),'bytes':len(body)}
     expected=(teamroot/reference['expected']['path']).read_bytes() if reference['expected'].get('available') else None
     item['comparison']='Exact byte match' if body==expected else 'Tokens match (whitespace differs)' if expected is not None and body.split()==expected.split() else 'Different output'
    if error.is_file():item['stderr']={'text':error.read_bytes()[:1200].decode('utf-8',errors='replace'),'path':str(base/error.name)}
    attempt['replayTests'].append(item)
