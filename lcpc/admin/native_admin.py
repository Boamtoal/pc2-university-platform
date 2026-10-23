"""Owner-only PC2 Administrator routes, with explicit commands and audit metadata."""
import base64,csv,difflib,io,json,re,time
from pathlib import Path
from urllib.parse import parse_qs,urlsplit
from core import Error,require,password_ok,totp
from contests import write_json
from contest_exports import csv_bytes
SECTIONS={'accounts','languages','groups','categories','judgements','sites','problems','contest','clocks','finalization','balloons','profiles','autojudges','connections','notifications','scoring','playback','eventfeeds','deliveries','inputValidation','shadow','plugins'}
COMMANDS={'save','scoring.save','autojudge.save','notifications.save','connection.disconnect','account.logoff','site.connect','clocks.startAll','clocks.pauseAll','clock.site','run.edit','run.release','run.rejudgeBatch','clarification.edit','clarification.release','definition.delete','problem.data.replace','submit.onBehalf','playback.start','accounts.bulk','accounts.import','balloon.delivered','reset.perform','playback.import','playback.stop','configuration.commit'}

def reauth(handler,data):
 import hmac
 with handler.app.store.db() as db:user=db.execute('SELECT * FROM users WHERE username=?',(handler.actor,)).fetchone()
 require(isinstance(data.get('password'),str) and len(data['password'])<=128,'Enter the current owner password',403)
 require(password_ok(data.get('password',''),user['password']),'Current owner password is incorrect',403)
 require(not user['totp'] or any(hmac.compare_digest(totp(user['totp'],time.time()+n*30),str(data.get('code',''))) for n in (-1,0,1)),'A valid authenticator code is required',403)

def sensitive(args):
 command=args['command'];fields=args.get('fields',{});require(isinstance(fields,dict),'Invalid native fields')
 return command in {'accounts.bulk','accounts.import','definition.delete','site.connect','reset.perform','submit.onBehalf','run.rejudgeBatch','problem.data.replace','playback.start','playback.import','playback.stop','configuration.commit'} or (command=='save' and (args.get('domain') in {'accounts','languages','sites','balloons','judgements'} or fields.get('EnableAutoRegistration') is True or fields.get('AllowMultipleLoginsPerTeam') is True))

def native_active(handler):
 manager=handler.app.manager;require(manager.data['selected']==manager.data['active'] and manager.selected()['status']=='active','Open the active contest to use native PC2 administration. Draft preparation remains available in Teams, Problems, Resources and Contest Controls.',409)

def handle(handler,path,data=None):
 if not path.startswith('/api/native/'):return False
 user=handler.user('owner');manager=handler.app.manager;store=handler.app.store;resources=handler.app.resources;op=path.rsplit('/',1)[1]
 if data is None:
  require(not manager.busy(),'A contest lifecycle job is in progress',409);native_active(handler)
  if op=='catalog':
   value=handler.app.bridge.call('admin.catalog');write_json(resources.base/'native-catalog.json',value);handler.send(200,value);return True
  if op=='section':
   args=parse_qs(urlsplit(handler.path).query);section=args.get('section',[''])[0];require(section in SECTIONS,'Unknown PC2 section');value=handler.app.bridge.call('admin.query',{'section':section});write_json(resources.base/('native-'+section+'.json'),value);handler.send(200,value);return True
  raise Error(404,'Not found')
 manager.guard(data);native_active(handler)
 if op=='configuration-preview':
  bundle=data.get('bundle');require(isinstance(bundle,dict),'Upload a configuration JSON object');value=handler.app.bridge.call('admin.execute',{'command':'configuration.preview','bundle':bundle});store.audit(handler.actor,'native.configuration-preview','success',details={'contestId':manager.data['selected'],'domain':bundle.get('domain'),'count':value.get('count')});handler.send(200,value);return True
 if op=='logs':
  role=data.get('role');require(role in {'server','wti','judge','bridge','dashboard','network','proxy','gateway'},'Unknown log source');value=handler.app.bridge.call('admin.logs',{'role':role});store.audit(handler.actor,'native.log-read','success',details={'contestId':manager.data['selected'],'role':role});handler.send(200,value);return True
 if op=='tests':
  args={'id':data.get('id')};require(isinstance(args['id'],str) and 0<len(args['id'])<=240,'Invalid problem')
  if 'test' in data:require(type(data['test']) is int and 1<=data['test']<=10000,'Invalid test number');args['test']=data['test']
  value=handler.app.bridge.call('admin.tests',args);store.audit(handler.actor,'native.tests','success',details={'contestId':manager.data['selected'],**args});handler.send(200,value);return True
 if op=='report':
  rid=data.get('report');require(isinstance(rid,str) and re.fullmatch('[A-Za-z0-9]{1,100}',rid),'Invalid report');reauth(handler,data)
  filters=data.get('filter',{});require(isinstance(filters,dict) and not(set(filters)-{'problems','languages','teams','groups','sites','judgements','states','excludeDeleted','minimumSeconds','maximumSeconds'}),'Invalid report filter')
  for key,values in filters.items():
   if key=='excludeDeleted':require(type(values) is bool,'Invalid deleted filter')
   elif key in ('minimumSeconds','maximumSeconds'):require(type(values) is int and 0<=values<=604800,'Invalid report time range')
   else:require(isinstance(values,list) and len(values)<=1000 and all(isinstance(v,str) and len(v)<=240 for v in values),'Invalid filter values')
  value=handler.app.bridge.call('admin.report',{'report':rid,'filter':filters});store.audit(handler.actor,'native.report','success',details={'contestId':manager.data['selected'],'report':rid})
  handler.send(200,value['text'],'text/plain; charset=utf-8',{'Content-Disposition':'attachment; filename="pc2-'+rid+'.txt"'});return True
 if op=='compare':
  queries=data.get('runs');require(isinstance(queries,list) and len(queries)==2,'Choose exactly two submissions');sources=[]
  for query in queries:
   require(isinstance(query,dict) and type(query.get('number')) is int and query['number']>0 and type(query.get('site',1)) is int,'Invalid submission');value=handler.app.bridge.call('source',{'number':query['number'],'site':query.get('site',1)})
   text=''
   for file in value.get('files',[]):
    raw=base64.b64decode(file['base64']);require(len(raw)<=512*1024,'Choose source files up to 512 KiB for comparison',413);text+='// FILE: '+file['name']+'\n'+raw.decode('utf-8',errors='replace')+'\n'
   sources.append(text)
  diff=''.join(difflib.unified_diff(sources[0].splitlines(True),sources[1].splitlines(True),fromfile='Run '+str(queries[0]['number']),tofile='Run '+str(queries[1]['number'])))
  store.audit(handler.actor,'native.source-compare','success',details={'contestId':manager.data['selected'],'runs':[q['number'] for q in queries]});handler.send(200,{'identical':sources[0]==sources[1],'diff':diff});return True
 if op=='import-preview':
  try:raw=base64.b64decode(data.get('base64',''),validate=True);require(len(raw)<=2*1024*1024,'CSV import is limited to 2 MiB',413);text=raw.decode('utf-8-sig')
  except (ValueError,TypeError,UnicodeError):raise Error(400,'Upload a UTF-8 CSV file')
  require(text.strip(),'The CSV file is empty');delimiter='\t' if '\t' in text.splitlines()[0] else ',';reader=csv.DictReader(io.StringIO(text),delimiter=delimiter);allowed={'type','site','login','name','password','country','institution'};require(reader.fieldnames and set(reader.fieldnames)<=allowed and 'name' in reader.fieldnames,'Use CSV headers: name, type, site, login, password, country, institution')
  rows=[]
  for row in reader:
   require(len(rows)<500 and None not in row,'Use at most 500 complete rows',413);row={k:(v or '').strip() for k,v in row.items()};row['type']=(row.get('type') or 'TEAM').upper()
   try:row['site']=int(row.get('site') or 1)
   except ValueError:raise Error(400,'Site must be a number')
   rows.append(row)
  result=handler.app.bridge.call('admin.execute',{'command':'accounts.import','rows':rows,'preview':True});import secrets
  token=secrets.token_hex(16);write_json(resources.base/'imports'/(token+'.json'),{'created':time.time(),'actor':handler.actor,'rows':rows});handler.send(200,{'token':token,'count':result['count'],'rows':[{k:v for k,v in row.items() if k!='password'} for row in rows]});return True
 if op=='execute':
  manager.allow_native_mutation();require(data.get('confirm')=='CONFIRM','Type CONFIRM before applying a native PC2 action');args=data.get('args');require(isinstance(args,dict) and args.get('command') in COMMANDS,'Unsupported native administrator command');reason=data.get('reason','');require(isinstance(reason,str) and 8<=len(reason.strip())<=1000,'Give a reason of 8–1000 characters')
  require(not {'directory','preview'}.intersection(args),'Internal paths and preview flags cannot be supplied')
  if sensitive(args):reauth(handler,data)
  if args['command']=='accounts.import':
   token=args.get('token','');require(isinstance(token,str) and re.fullmatch('[a-f0-9]{32}',token),'Preview the CSV import first');plan=resources.base/'imports'/(token+'.json');require(plan.exists(),'Import preview expired',409);value=json.loads(plan.read_text());require(value['actor']==handler.actor and value['created']>time.time()-300,'Import preview expired',409);args={'command':'accounts.import','rows':value['rows']}
  if args['command']=='playback.import':
   directory,main=prepare_replay(resources,data.get('base64'));args={**args,'directory':str(directory),'main':main}
  if args['command']=='problem.data.replace':
   from core import prepare_judge_data
   require(isinstance(args.get('id'),str),'Choose a problem');directory=prepare_judge_data(resources,data.get('base64'));args={**args,'directory':str(directory)}
  if args['command']=='reset.perform':
   require(data.get('resetContestId')==manager.data['selected'],'Type the exact contest ID before resetting');require(any(b['contestId']==manager.data['selected'] for b in manager.listing().get('backups',[])),'Create a full backup of this contest before resetting it',409)
  safe={k:args[k] for k in ('command','domain','id','count','number','site') if k in args};safe.update(contestId=manager.data['selected'],reason=reason.strip());store.audit(handler.actor,'native.action','requested',details=safe)
  if args['command']=='accounts.import':
   try:plan.rename(plan.with_suffix('.used'))
   except FileNotFoundError:raise Error(409,'Import preview was already consumed')
  try:result=handler.app.bridge.call('admin.execute',args)
  except Exception:
   store.audit(handler.actor,'native.action','failed',details=safe,alert=('error','PC2 did not confirm a native administrator action. Inspect actual state before retrying.'));raise
  store.audit(handler.actor,'native.action','success',details=safe)
  try:resources.publish_catalog(handler.app.bridge.snapshot(fresh=True))
  except Exception:
   store.audit(handler.actor,'native.refresh','failed',details={'contestId':manager.data['selected']},alert=('warning','A native action completed but catalog refresh failed. Inspect actual PC2 state before retrying.'))
   result['warning']='The native action completed, but catalog refresh failed. Reload actual PC2 state before retrying.'
  if args['command']=='configuration.commit':
   import zipfile
   output=io.BytesIO()
   with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as archive:
    archive.writestr('result.json',json.dumps({k:v for k,v in result.items() if k!='credentials'},indent=2))
    if result.get('credentials'):archive.writestr('created-account-credentials.csv',csv_bytes(['site','login','name','password'],result['credentials']))
   handler.send(200,output.getvalue(),'application/zip',{'Content-Disposition':'attachment; filename="pc2-configuration-import-result.zip"'});return True
  if 'credentials' in result:
   body=csv_bytes(['site','login','name','password'],result['credentials']);handler.send(200,body,'text/csv; charset=utf-8',{'Content-Disposition':'attachment; filename="pc2-new-account-credentials.csv"'});return True
  handler.send(200,result);return True
 raise Error(404,'Not found')


def prepare_replay(store,encoded):
 import zipfile,uuid,shutil
 try:body=base64.b64decode(encoded,validate=True)
 except (TypeError,ValueError):raise Error(400,'Invalid playback ZIP encoding')
 require(0<len(body)<=20*1024*1024,'Playback ZIP must be at most 20 MiB',413)
 directory=store.base/'replays'/uuid.uuid4().hex;directory.mkdir(mode=0o700,parents=True)
 try:
  with zipfile.ZipFile(io.BytesIO(body)) as archive:
   require(1<=len(archive.infolist())<=1000,'Playback ZIP must contain 1–1000 files');names=set();total=0
   for item in archive.infolist():
    if item.is_dir():continue
    name=item.filename.replace('\\','/');path=Path(name);require(not path.is_absolute() and '..' not in path.parts and path.suffix.lower() in {'.txt','.tsv','.replay','.cpp','.cc','.c','.h','.hpp','.py','.java'} and not(item.flag_bits&1) and ((item.external_attr>>16)&0o170000)!=0o120000,'Unsafe playback ZIP entry')
    require(name not in names,'Duplicate playback ZIP entry');names.add(name);total+=item.file_size;require(total<=50*1024*1024,'Playback data exceeds 50 MiB',413);target=directory/path;target.parent.mkdir(mode=0o700,parents=True,exist_ok=True);target.write_bytes(archive.read(item));target.chmod(0o600)
  preferred=[name for name in ('playback.txt','replay.txt','playback.tsv','replay.tsv') if name in names];candidates=[n for n in names if Path(n).suffix.lower() in {'.tsv','.replay','.txt'}];require(preferred or len(candidates)==1,'Include playback.txt or replay.txt at the ZIP root');main=preferred[0] if preferred else candidates[0];text=(directory/main).read_text(encoding='utf-8-sig');lines=[line for line in text.splitlines() if line.strip() and not line.lstrip().startswith('#')];require(1<=len(lines)<=10000,'Use 1–10000 playback events')
  prepared=[]
  for line in lines:
   fields=[];keys=set()
   for token in line.split('|'):
    require('=' in token,'Playback fields must use native name=value syntax');key,value=token.split('=',1);key=key.strip().lower();value=value.strip();require(key not in keys,'Duplicate playback field');keys.add(key)
    require(not re.search(r'(^[/\\]|(^|[/\\])\.\.([/\\]|$)|^[A-Za-z]:|[$~\x00])',value),'Playback references must stay inside the uploaded ZIP')
    if key=='mainfile':
     target=(directory/Path(main).parent/value).resolve();require(target.is_relative_to(directory.resolve()) and target.is_file() and target.suffix.lower() in {'.cpp','.cc','.c','.py','.java'},'Playback source must be included in the ZIP');value=str(target)
    fields.append(key+'='+value)
   require('action' in keys,'Missing native playback action');prepared.append('|'.join(fields))
  native_file=directory/'dashboard-native.replay';require(not native_file.exists(),'Reserved playback filename');native_file.write_text('\n'.join(prepared)+'\n',encoding='utf-8');native_file.chmod(0o600)
  return directory,native_file.name
 except (zipfile.BadZipFile,UnicodeError,ValueError):shutil.rmtree(directory,ignore_errors=True);raise Error(400,'Invalid playback ZIP or UTF-8 event file')
 except Exception:shutil.rmtree(directory,ignore_errors=True);raise
