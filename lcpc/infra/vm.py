"""Dedicated Lima VZ judge management; project paths are never guest mounts."""
from pathlib import Path
import os,subprocess,json,time,signal,tarfile,tempfile,shutil
ROOT=Path(__file__).resolve().parents[2]
ENV={**os.environ,'LIMA_HOME':str(ROOT/'.local/lima')}
from runtime_paths import executable
LIMA=os.environ.get('LCPC_LIMA_BIN') or shutil.which('limactl') or '/opt/homebrew/bin/limactl';NAME='lcpc-judge'
ACTIVE=ROOT/'.local/linux-active-state'
def lima(args,**kw):
 kw.setdefault('check',True)
 return subprocess.run([executable('limactl','LCPC_LIMA_BIN',(LIMA,)),*args],env=ENV,**kw)
def guest(args,**kw):return lima(['shell',NAME,'--',*args],**kw)
def ensure_running():
 # Resume only the dedicated, previously installed VM. Never download an image
 # or silently create a different execution environment during activation.
 if not (Path(ENV['LIMA_HOME'])/NAME/'lima.yaml').is_file():
  raise RuntimeError('The isolated judge VM has not been installed. Complete server setup before activation.')
 result=lima(['list',NAME,'--json'],capture_output=True,text=True,timeout=15)
 rows=[json.loads(line) for line in result.stdout.splitlines() if line.strip()]
 if len(rows)!=1 or rows[0].get('name')!=NAME:raise RuntimeError('The dedicated judge VM could not be identified')
 status=rows[0].get('status')
 if status=='Running':return
 if status!='Stopped':raise RuntimeError('The judge VM is not ready to start; inspect its status before recovery')
 lima(['start','--tty=false',NAME],capture_output=True,text=True,timeout=180)
def vm_health(ctl):
 q=guest(['sudo','/opt/lcpc/bin/healthcheck.sh'],capture_output=True,text=True,timeout=15)
 data=json.loads(q.stdout)
 return data

def install_guest(ctl):
 stage=ROOT/'.local/guest-stage';stage.mkdir(mode=0o700,exist_ok=True)
 for f in (ROOT/'lcpc/infra/linux').iterdir():
  if f.is_file():shutil.copyfile(f,stage/f.name)
 guest(['mkdir','-p','/tmp/lcpc-stage'])
 for f in stage.iterdir():lima(['copy',str(f),NAME+':/tmp/lcpc-stage/'+f.name],capture_output=True)
 guest(['sudo','sh','/tmp/lcpc-stage/install-hardening.sh'])
 with tempfile.TemporaryDirectory(dir=ROOT/'.local') as d:
  archive=Path(d)/'pc2-runtime.tar.gz'
  with tarfile.open(archive,'w:gz') as t:
   for p in (ROOT/'lib').glob('*.jar'):t.add(p,arcname='lib/'+p.name)
   for name in ['LCPCLaunch.class','SecretRedactingOutputStream.class','JudgeGuardPolicy.class','JudgeGuardSelfTest.class','judge-guard-agent.jar']:
    t.add(ROOT/'lcpc/build'/name,arcname='classes/'+name)
  lima(['copy',str(archive),NAME+':/tmp/pc2-runtime.tar.gz'],capture_output=True)
 guest(['sudo','tar','xzf','/tmp/pc2-runtime.tar.gz','-C','/opt/lcpc'])
 guest(['sudo','rm','/tmp/pc2-runtime.tar.gz'])
 guest(['sudo','chown','-R','root:root','/opt/lcpc'])
 guest(['sudo','chmod','-R','go-w','/opt/lcpc'])
 print('Guest PC2 runtime and sandbox installed')

def configure_judge(ctl):
 """Copies only judge password, never contest/admin/team credentials."""
 props=dict(l.split('=',1) for l in (ctl.LOCAL/'credentials.properties').read_text().splitlines())
 with tempfile.TemporaryDirectory(dir=ROOT/'.local') as d:
  p=Path(d)/'judge.properties';p.write_text('judge1='+props['judge1']+'\n');p.chmod(0o600)
  lima(['copy',str(p),NAME+':/tmp/lcpc-judge.properties'],capture_output=True)
 guest(['sudo','install','-o','pc2judge','-g','pc2judge','-m','0600','/tmp/lcpc-judge.properties','/var/lib/pc2judge/credentials.properties'])
 guest(['rm','/tmp/lcpc-judge.properties'])
 guest(['sudo','sh','-c',"printf '[client]\\nserver=127.0.0.1:50002\\n' > /var/lib/pc2judge/pc2v9.ini; chown pc2judge:pc2judge /var/lib/pc2judge/pc2v9.ini; chmod 600 /var/lib/pc2judge/pc2v9.ini"])

def start_tunnel(ctl):
 config=ROOT/'.local/judge-ssh.config'
 q=lima(['show-ssh','--format=config',NAME],capture_output=True,text=True)
 config.write_text(q.stdout);config.chmod(0o600)
 pf=ROOT/'.local/tunnel.pid'
 if pf.exists():
  try:
   pid=int(pf.read_text());os.kill(pid,0)
   args=subprocess.check_output(['ps','-o','command=','-p',str(pid)],text=True)
   if str(config) in args and '-R' in args:return
  except (ProcessLookupError,subprocess.CalledProcessError):pass
 with (ROOT/'.local/tunnel.log').open('ab') as log:
  p=subprocess.Popen(['/usr/bin/ssh','-F',str(config),'-N','-T','-o','ControlMaster=no','-o','ControlPath=none','-o','ControlPersist=no','-o','ForwardAgent=no','-o','ExitOnForwardFailure=yes','-o','ServerAliveInterval=10','-o','ServerAliveCountMax=3','-R','127.0.0.1:50002:127.0.0.1:'+str(ctl.ports()['port']),'lima-'+NAME],stdout=log,stderr=log,start_new_session=True)
 pf.write_text(str(p.pid));time.sleep(1)
 if p.poll() is not None:raise RuntimeError('Private judge SSH tunnel failed')
 print('Private SSH tunnel ready')

def judge_start(ctl):
 mode=ctl.LOCAL/'mode.json'
 if not mode.exists() or json.loads(mode.read_text()).get('mode') not in ['isolated-trial','competition']:
  raise RuntimeError('Linux Judge requires an explicitly configured isolated contest')
 if ACTIVE.exists() and ACTIVE.read_text().strip()!=str(ctl.LOCAL):
  raise RuntimeError('Linux Judge belongs to another contest; stop it in that state first')
 if ctl.pid_for('judge'):raise RuntimeError('Mac AutoJudge is running. Stop it before Linux Judge.')
 ensure_running()
 configure_judge(ctl);start_tunnel(ctl)
 ACTIVE.write_text(str(ctl.LOCAL)+'\n')
 guest(['sudo','systemctl','start','pc2judge.service'])
 for _ in range(15):
  time.sleep(1)
  h=vm_health(ctl)
  if h['ready']:
   time.sleep(1)
   if vm_health(ctl)['ready']:break
 else:raise RuntimeError('Linux Judge did not authenticate; inspect private coordinator log')
 print('Isolated Linux Judge active')

def judge_stop(ctl):
 if ACTIVE.exists() and ACTIVE.read_text().strip()!=str(ctl.LOCAL):
  raise RuntimeError('Linux Judge belongs to another contest; refusing to stop it')
 guest(['sudo','systemctl','stop','pc2judge.service'])
 pf=ROOT/'.local/tunnel.pid'
 if pf.exists():
  try:
   pid=int(pf.read_text());args=subprocess.check_output(['ps','-o','command=','-p',str(pid)],text=True)
   if str(ROOT/'.local/judge-ssh.config') in args:os.kill(pid,signal.SIGTERM)
  except (ProcessLookupError,subprocess.CalledProcessError):pass
 ACTIVE.unlink(missing_ok=True)
 print('Linux judge and private tunnel stopped')
