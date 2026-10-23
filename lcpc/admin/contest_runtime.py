"""Lifecycle jobs. Never starts a contest clock; preserves failed startup state."""
from pathlib import Path
import contextlib,fcntl,hashlib,json,os,secrets,shlex,shutil,subprocess,sys,time,zipfile
from core import ROOT,Bridge,Error,require
from contests import write_json,read_json,DraftBridge,ReadOnlyBridge

def controller(state):
 # Load a separate module so no global controller state leaks between contests.
 import importlib.util
 spec=importlib.util.spec_from_file_location('contest_controller_'+state.name,ROOT/'lcpc/pc2ctl.py');ctl=importlib.util.module_from_spec(spec);spec.loader.exec_module(ctl);ctl.LOCAL=state;return ctl

def prepare_instance(row):
 state=Path(row['state']);draft=read_json(state/'admin-dashboard/draft.json')
 require(not (state/'server/profiles.properties').exists(),'An incomplete initialized contest needs recovery; refusing to bootstrap over it',409)
 for role in ['server','judge','judge2','admin','team1','board','api']:
  (state/role).mkdir(mode=0o700,exist_ok=True);(state/role/'pc2v9.ini').write_text('[client]\nserver=127.0.0.1:50002\n[server]\nport=50002\n')
 credentials={u:secrets.token_urlsafe(32) for u in ['contest','site1','administrator1','judge1','judge2','scoreboard1','scoreboard2']}
 for t in draft['teams']:credentials[t['login']]=t['password']
 (state/'credentials.properties').write_text(''.join(k+'='+v+'\n' for k,v in credentials.items()));write_json(state/'settings.json',{'port':50002,'web_port':8080});write_json(state/'mode.json',{'mode':'competition','managed':True})
 config=state/'cdp/config';config.mkdir(parents=True,exist_ok=True)
 # JSON string scalars are valid YAML and cannot inject extra config keys.
 q=lambda s:json.dumps(s,ensure_ascii=True)
 lines=['name: '+q(draft['contest']['title']),'short-name: '+q(draft['contest']['shortName']),"duration: '00:01:00'",'running: false','auto-start-contest: false','auto-stop-clock-at-end: true','load-data-files: true','load-sample-judges-data: true','computer-judged: true','manual-review: false','send-prelim-judgement: false','languages:']
 for lang in draft['languages']:
  require('/opt/lcpc/bin/' in lang['compilerCmd'],'Only the existing isolated Linux language profiles may be activated',409)
  lines+=['  - name: '+q(lang['name']),'    active: '+str(lang['active']).lower(),*['    '+key+': '+q(lang[key]) for key in ('compilerCmd','exemask','execCmd')]]
 lines+=['accounts:','  - account: JUDGE','    site: 1','    count: 2','  - account: SCOREBOARD','    site: 1','    count: 2','auto-judging:','  - account: JUDGE','    site: 1','    number: 1','    letters: all','    enabled: yes','problemset: []','sites:','  - number: 1',"    name: 'University contest server'",'    IP: 127.0.0.1','    port: 50002','    password: '+q(credentials['site1'])]
 (config/'contest.yaml').write_text('\n'.join(lines)+'\n');(state/'cdp/reject.ini').write_text('Compilation Error|CE\nRun-time Error|RTE\nTime Limit Exceeded|TLE\nMemory Limit Exceeded|MLE\nWrong Answer|WA\nExcessive Output|EE\nOutput Format Error|EFE\nOther - Contact Staff|CS\n')
 if not(state/'wti').exists():
  with zipfile.ZipFile(ROOT/'projects/WebTeamInterface-1.1-7065.zip') as archive:archive.extractall(state/'unpack')
  (state/'unpack/WebTeamInterface-1.1').rename(state/'wti');(state/'unpack').rmdir()
 from infra.branding import install
 install(state)
 (state/'wti/pc2v9.ini').write_text('[client]\nserver=127.0.0.1:50002\n[server]\nwtiport=8080\nwtiwsName=/websocket\nwtiscoreboardaccount=scoreboard2\nwtiscoreboardpassword='+credentials['scoreboard2']+'\nwtiOverridePublicIP=127.0.0.1\nallowedOSName1=Mac OS X\nallowedOSName2=Windows\nallowedOSName3=Linux\n')
 for folder,dirs,files in os.walk(state):
  os.chmod(folder,0o700)
  for name in files:os.chmod(Path(folder)/name,0o600)

@contextlib.contextmanager
def runtime_lock():
 path=ROOT/'.local/contest-runtime.lock';path.parent.mkdir(exist_ok=True)
 with path.open('a') as handle:
  try:fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:raise Error(409,'Another contest lifecycle operation is in progress')
  yield

def other_server(state):
 sys.path.insert(0,str(ROOT/'lcpc'))
 from infra.runtime_guard import server_states
 return any(other!=state for other in server_states(ROOT))

def stop_exporters(ctl,state,control_state):
 # Stop the verified Java exporter as well as its Python launcher. Killing
 # only a launcher would leave its child signed into the scoreboard account.
 exporters=[]
 for line in subprocess.check_output(['ps','-axo','pid=,stat=,command='],text=True).splitlines():
  parts=line.strip().split(None,2)
  if len(parts)!=3 or parts[1].startswith('Z'):continue
  try:args=shlex.split(parts[2]);pid=int(parts[0])
  except ValueError:continue
  if not args:continue
  java=Path(args[0]).name=='java' and 'PublicStandings' in args and '-Dlcpc.secrets='+str(state/'credentials.properties') in args
  script=str(ROOT/'lcpc/public_standings.py')
  python=script in args and ('python' in Path(args[0]).name) and (('--state' in args and args[args.index('--state')+1:args.index('--state')+2]==[str(state)]) or (args[-1:]==[script] and state==control_state))
  if java or python:exporters.append(pid)
 for pid in exporters:
  try:os.kill(pid,15)
  except ProcessLookupError:pass
 for _ in range(100):
  if not any(ctl.alive(pid) for pid in exporters):break
  time.sleep(.1)
 require(not any(ctl.alive(pid) for pid in exporters),'Public standings did not stop cleanly; the contest remains reserved',409)
 (state/'public-standings.pid').unlink(missing_ok=True)

def recover(manager,row):
 return activate(manager,row,recovery=True)

def stage(manager,row,message):
 write_json(Path(row['state'])/'admin-dashboard/runtime-stage.json',{'stage':message,'contest':row['id']})
 if getattr(manager,'job',None):
  manager.job['message']=message;write_json(manager.base/'job.json',manager.job)

def activate(manager,row,recovery=False):
 state=Path(row['state']);sys.path.insert(0,str(ROOT/'lcpc'));ctl=controller(state)
 with runtime_lock():
  require((not manager.data['active'] or recovery and manager.data['active']==row['id']) and not other_server(state),'Another PC2 contest server is active. Deactivate it first.',409)
  require(recovery or not(state/'admin-dashboard/installing').exists(),'An incomplete draft installation requires recovery before activation',409)
  # Reserve before any process is launched. Failure retains reservation if a server survives.
  manager.data['active']=row['id'];row['status']='activating';manager.save()
  bridge=None
  try:
   stage(manager,row,'Connecting the paused PC2 server')
   if recovery:
    if row['id'] in manager.bridges:manager.bridges[row['id']].close()
    from infra import network
    network.stop(ctl)
    stop_exporters(ctl,state,manager.app.store.state)
   fresh=not(state/'secured').exists()
   if fresh:
    prepare_instance(row);ctl.start('server',('bootstrap',));result=ctl.api(['secure-bootstrap'],capture=True);require(result.returncode==0,'Credential initialization failed; inspect the private log',409)
    (state/'secured').write_text('Credential initialization completed\n')
    (state/'admin-dashboard/installing').write_text('Native draft installation in progress\n')
   else:ctl.start('server')
   if (state/'admin-dashboard/installing').exists():
    stage(manager,row,'Installing or resuming the unstarted draft')
    from manage import initialize
    initialize(state)
    bridge=Bridge(state);result=bridge.call('draft.install');ids=result['problemIds'];store=manager.store_for(row)
    with store.db() as db:
     for old,new in ids.items():db.execute('UPDATE resources SET problem=? WHERE problem=?',(new,old))
    (state/'admin-dashboard/installing').unlink(missing_ok=True)
   else:bridge=Bridge(state)
   snapshot=bridge.snapshot(fresh=True);require(not snapshot['contest']['running'],'The restored clock is unexpectedly running; participant access was not opened',409)
   write_json(state/'admin-dashboard/last-snapshot.json',snapshot);manager.store_for(row).publish_catalog(snapshot)
   from infra.branding import install_scoreboard,install_participant_ui,install_result_notifications
   install_scoreboard(state)
   install_participant_ui(state)
   install_result_notifications(state,hook=True)
   from participant_identity import publish as publish_identity
   publish_identity(manager.store_for(row))
   stage(manager,row,'Starting participant services and the isolated judge')
   ctl.start('wti')
   from infra import vm,network
   if snapshot.get('judging',{}).get('mode')!='human':vm.judge_start(ctl)
   # Reuse the approved host's adaptive LAN configuration, regenerating all paths.
   profile_path=manager.app.store.state/'network/profile.json'
   if profile_path.exists():
    profile=read_json(profile_path)
    if profile.get('automatic'):
     lan=network.current_lan(profile.get('interface'));profile.update(bind=lan['ip'],cidr=lan['cidr'],interface=lan['interface'])
    network.prepare(ctl,profile['bind'],profile['cidr'],profile.get('transport','http'),hostname=profile.get('hostname'),automatic=profile.get('automatic',False),interface=profile.get('interface'))
    if profile.get('lan_confirmed'):network.confirm(ctl,profile['bind'],profile['cidr'])
    network.start(ctl)
   stage(manager,row,'Publishing the public scoreboard')
   command=[sys.executable,'-B',str(ROOT/'lcpc/public_standings.py'),'--state',str(state)]
   with (state/'public-standings.log').open('ab') as log:proc=subprocess.Popen(command,env={**os.environ,'LCPC_STATE_DIR':str(state)},cwd=ROOT,stdout=log,stderr=log,start_new_session=True)
   (state/'public-standings.pid').write_text(str(proc.pid));time.sleep(.5);require(proc.poll() is None,'Public standings service failed to start',409)
   stage(manager,row,'Server ready; contest clock remains paused')
   row['status']='active';manager.bridges[row['id']]=bridge;manager.app.bridge=bridge;manager.app.resources=manager.store_for(row);manager.data['selected']=row['id'];manager.save();return {'clockStarted':False,'id':row['id']}
  except Exception:
   if bridge:bridge.close()
   # Fail closed: stop participant exposure, retain the active reservation until recovery.
   try:
    from infra import network
    network.stop(ctl)
   except Exception:pass
   row['status']='error'
   if not ctl.pid_for('server'):manager.data['active']=None
   manager.save();raise

def deactivate(manager,row):
 state=Path(row['state']);sys.path.insert(0,str(ROOT/'lcpc'));ctl=controller(state);bridge=manager.bridge_for(row)
 with runtime_lock():
  snapshot=bridge.snapshot(fresh=True);require(not snapshot['contest']['running'],'Pause the contest first',409);require(all(r['deleted'] or r['final'] for r in snapshot['runs']),'Finalize pending submissions first',409)
  write_json(state/'admin-dashboard/last-snapshot.json',snapshot)
  if any(t.get('testAccount') for t in snapshot.get('teams',[])):
   from test_team import cache_credentials
   cache_credentials(state,bridge.call('test-team.credentials'))
  template=bridge.call('template.export',{'includeProblems':True});file=Path(template['path']);require(file.parent==state/'admin-dashboard/template-exports','Unexpected template path',409);shutil.copyfile(file,state/'admin-dashboard/clone-template.bin');write_json(state/'admin-dashboard/clone-template.json',{'templateSha256':template['sha256'],'languages':template['languages']})
  from infra import vm,network
  network.stop(ctl)
  if vm.ACTIVE.exists() and vm.ACTIVE.read_text().strip()==str(state):vm.judge_stop(ctl)
  stop_exporters(ctl,state,manager.app.store.state)
  for role in ('wti','judge','judge2','team1','board','admin'):ctl.terminate(role)
  # Other clients logging out can invalidate the API connection's login state.
  # Reconnect after they stop, and keep the shutdown transport alive until the
  # server exits: closing it immediately can discard the queued shutdown packet.
  bridge.close();bridge=Bridge(state);manager.bridges[row['id']]=bridge
  if manager.data['selected']==row['id']:manager.app.bridge=bridge
  try:
   final=bridge.snapshot(fresh=True)
   require(not final['contest']['running'],'Pause the contest first',409)
   require(all(r['deleted'] or r['final'] for r in final['runs']),'Finalize pending submissions first',409)
   bridge.call('runtime.shutdown')
   for _ in range(100):
    if not ctl.pid_for('server'):break
    time.sleep(.15)
   require(not ctl.pid_for('server'),'PC2 did not confirm a clean shutdown; the contest remains reserved',409)
  finally:bridge.close()
  manager.data['active']=None;row['status']='inactive';manager.bridges[row['id']]=ReadOnlyBridge(state)
  if manager.data['selected']==row['id']:manager.app.bridge=manager.bridges[row['id']]
  manager.save();return {'id':row['id'],'preserved':True}

def backup(manager,row):
 from contest_exports import full_backup
 return full_backup(manager,row)
