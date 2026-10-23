#!/usr/bin/python3 -I
"""Root-owned PC2 sandbox broker. Only the dedicated judge may call via sudo.
Each invocation gets a bounded tmpfs, isolated filesystem, network namespace,
dynamic UID, cgroup v2 memory/pids/cpu controls and systemd syscall filtering.
No user-provided command line is executed; compiler and runner paths are fixed.
"""
from pathlib import Path
import os,sys,re,subprocess,tempfile,shutil,uuid,json,signal,time,fcntl
HOME=Path('/var/lib/pc2judge')
JOBS=Path('/var/lib/lcpc-jobs')
ROOTFS='/var/lib/lcpc-root'
AUDIT=Path('/var/lib/lcpc-jobs/audit.jsonl')
def check(ok,msg):
 if not ok:raise RuntimeError(msg)
def shellfree(args,**kwargs):return subprocess.run(args,check=True,**kwargs)
def safe_file(name):
 name=name.removeprefix('./')
 check(re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.-]{0,100}',name) is not None,'Invalid filename')
 p=Path.cwd()/name
 check(p.parent.resolve().is_relative_to(HOME),'Working directory outside judge home')
 check(p.is_file() and not p.is_symlink(),'Missing/unsafe input file')
 check(p.stat().st_size<=8*1024*1024,'Input too large')
 return p

def main():
 check(os.geteuid()==0,'Must run via dedicated sudo rule')
 check(os.environ.get('SUDO_USER','root') in ['pc2judge','root'],'Unauthorized caller')
 check(Path('/sys/fs/cgroup/cgroup.controllers').exists(),'cgroup v2 missing')
 if sys.argv[1:] == ['check']:
  # Real startup probe, not a replacement for the acceptance test suite.
  oldcwd=Path.cwd();oldargv=sys.argv[:]
  with tempfile.TemporaryDirectory(prefix='.preflight-',dir=HOME) as tmp:
   try:
    os.chdir(tmp)
    Path('probe.cpp').write_text('#include <bits/stdc++.h>\n#include <sys/socket.h>\nint main(){if(std::ifstream("/var/lib/pc2judge/credentials.properties").good())return 91;if(socket(AF_INET,SOCK_STREAM,0)>=0)return 92;return 0;}\n')
    sys.argv=[oldargv[0],'compile17','probe.cpp','probe'];check(main()==0,'Compiler isolation probe failed')
    sys.argv=[oldargv[0],'run','128','5','./probe'];check(main()==0,'Runtime isolation probe failed')
    return 0
   finally:os.chdir(oldcwd);sys.argv=oldargv
 mode=sys.argv[1];compile=mode in ['compile17','compile20','compilepython']
 python=mode=='compilepython'
 if compile:
  check(len(sys.argv)==4,'Expected source and executable name')
  src=safe_file(sys.argv[2]);dest=sys.argv[3]
  check(re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.-]{0,100}',dest) is not None,'Invalid output name')
  check(not (Path.cwd()/dest).is_symlink(),'Unsafe output target')
  memory=768;cpu=25;wall=35
 else:
  check(mode=='run' and (len(sys.argv)==5 or (len(sys.argv)==6 and sys.argv[4]=='/opt/lcpc/bin/runpython')),'Expected memory, time and approved executable')
  python=len(sys.argv)==6
  memory=int(sys.argv[2]);cpu=int(sys.argv[3]);wall=cpu+1
  check(32<=memory<=1024 and 1<=cpu<=10,'Limits outside safe envelope')
  src=safe_file(sys.argv[5] if python else sys.argv[4]);dest=None
 job=Path(tempfile.mkdtemp(prefix='job-',dir=JOBS));unit='lcpc-job-'+uuid.uuid4().hex
 started=time.monotonic();mounted=False;props={};rc=246
 def kill(signum=None,frame=None):
  subprocess.run(['/usr/bin/systemctl','kill','--kill-whom=all','--signal=KILL',unit],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 for sig in [signal.SIGTERM,signal.SIGINT,signal.SIGHUP]:signal.signal(sig,kill)
 lock=open('/run/lock/lcpc-sandbox.lock','w');fcntl.flock(lock,fcntl.LOCK_EX)
 try:
  shellfree(['/usr/bin/mount','-t','tmpfs','-o','size=64m,nodev,nosuid,mode=0777','tmpfs',str(job)])
  mounted=True
  staged=job/('main.py' if python else 'main.cpp' if compile else 'program');shutil.copyfile(src,staged);staged.chmod(0o444 if compile else 0o555)
  if python:
   argv=['/usr/bin/python3','-I','-B','-c',"compile(open('/work/main.py','rb').read(), 'submission.py', 'exec', dont_inherit=True)"] if compile else ['/usr/bin/python3','-I','-B','/work/main.py']
  else:
   argv=['/usr/bin/g++','-std=c++'+('17' if mode=='compile17' else '20'),'-O2','-pipe','-Wall','-Wextra','-o','/work/program','/work/main.cpp'] if compile else ['/work/program']
  settings={
   'Type':'exec','DynamicUser':'yes','NoNewPrivileges':'yes','CapabilityBoundingSet':'',
   'RootDirectory':ROOTFS,'WorkingDirectory':'/work','BindPaths':str(job)+':/work','ReadWritePaths':'/work',
   'BindReadOnlyPaths':' '.join(p for p in ['/usr','/bin','/lib','/lib64'] if Path(p).exists()),'PrivateNetwork':'yes','RestrictAddressFamilies':'AF_UNIX',
   'PrivateDevices':'yes','PrivateIPC':'yes','ProtectSystem':'strict','ProtectHome':'yes','ProtectControlGroups':'yes',
   'ProtectKernelTunables':'yes','ProtectKernelModules':'yes','ProtectKernelLogs':'yes',
   'ProtectProc':'invisible','ProcSubset':'pid','RestrictNamespaces':'yes','RestrictRealtime':'yes',
   'RestrictSUIDSGID':'yes','LockPersonality':'yes','SystemCallArchitectures':'native',
   'SystemCallFilter':'@system-service','SystemCallErrorNumber':'EPERM',
   'TemporaryFileSystem':'/tmp:rw,nosuid,nodev,noexec,size=32M',
   'MemoryMax':str(memory)+'M','MemorySwapMax':'0','TasksMax':'16','CPUQuota':'100%','CPUAccounting':'yes',
   'LimitCPU':str(cpu)+':'+str(cpu),'RuntimeMaxSec':str(wall),
   'LimitFSIZE':'1048576','LimitNOFILE':'64','LimitCORE':'0','UMask':'0077',
   'KillMode':'control-group','TimeoutStopSec':'1','OOMPolicy':'kill','RemainAfterExit':'yes',
   'Environment':'PATH=/usr/bin:/bin LANG=C.UTF-8 HOME=/tmp'
  }
  c=['/usr/bin/systemd-run','--quiet','--pipe','--unit='+unit]
  for k,v in settings.items():c+=['--property='+k+'='+v]
  with tempfile.TemporaryFile() as out,tempfile.TemporaryFile() as err:
   proc=subprocess.Popen(c+['--',*argv],stdin=sys.stdin.buffer,stdout=out,stderr=err)
   deadline=time.monotonic()+wall+8
   # Retain the unit for its accounting, but explicitly stop it after the main
   # process exits: --pipe otherwise waits forever with RemainAfterExit=yes.
   while time.monotonic()<deadline:
    show=subprocess.run(['/usr/bin/systemctl','show',unit,'--property=Result,ExecMainCode,ExecMainStatus,ExecMainExitTimestampMonotonic,MemoryPeak,CPUUsageNSec,TasksMax,MemoryMax,PrivateNetwork,RootDirectory'],capture_output=True,text=True)
    props=dict(l.split('=',1) for l in show.stdout.splitlines() if '=' in l)
    if int(props.get('ExecMainExitTimestampMonotonic','0'))>0:
     rc=int(props.get('ExecMainStatus','246'));break
    if props.get('CPUUsageNSec','').isdigit() and int(props['CPUUsageNSec'])>=cpu*1000000000:
     kill();rc=244;break
    if proc.poll() is not None:rc=proc.returncode;break
    time.sleep(.04)
   else:kill();rc=245
   subprocess.run(['/usr/bin/systemctl','stop',unit],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
   try:proc.wait(timeout=3)
   except subprocess.TimeoutExpired:proc.kill();proc.wait()
   result=props.get('Result')
   if result=='oom-kill':rc=243
   elif result=='timeout' or props.get('ExecMainStatus') in ['9','24']:rc=244
   elif rc and not compile:rc=139
   if rc==0 and compile:
    exe=staged if python else job/'program';check(exe.is_file() and not exe.is_symlink(),'Compiler produced no executable')
    fd=os.open(Path.cwd()/dest,os.O_WRONLY|os.O_CREAT|os.O_TRUNC|os.O_NOFOLLOW,0o700)
    with os.fdopen(fd,'wb') as f,exe.open('rb') as s:shutil.copyfileobj(s,f)
    os.chown(Path.cwd()/dest,src.stat().st_uid,src.stat().st_gid);os.chmod(Path.cwd()/dest,0o700)
   out.seek(0);err.seek(0)
   sys.stdout.buffer.write(out.read(1048576));sys.stderr.buffer.write(err.read(1048576))
 finally:
  kill();subprocess.run(['/usr/bin/systemctl','stop',unit],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  subprocess.run(['/usr/bin/systemctl','reset-failed',unit],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  if mounted:subprocess.run(['/usr/bin/umount',str(job)],check=True)
  job.rmdir()
  with AUDIT.open('a') as f:f.write(json.dumps({'unit':unit,'mode':mode,'exit':rc,'seconds':round(time.monotonic()-started,3),'memory_mb':memory,'cpu_limit_sec':cpu,'properties':props})+'\n')
  fcntl.flock(lock,fcntl.LOCK_UN)
 return rc
if __name__=='__main__':
 try:sys.exit(main())
 except Exception as e:print('LCPC sandbox refused execution: '+str(e),file=sys.stderr);sys.exit(246)
