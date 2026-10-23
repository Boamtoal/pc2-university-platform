"""Small reversible operating controls; never starts a contest clock."""
from pathlib import Path
import subprocess,os,signal,time,re,json

def awake(ctl):
 pid=ctl.pid_for('server')
 if not pid:raise RuntimeError('Start the server before enabling keep-awake')
 pf=ctl.LOCAL/'awake.pid'
 if pf.exists():
  q=subprocess.run(['ps','-o','command=','-p',pf.read_text().strip()],capture_output=True,text=True)
  if 'caffeinate -i -s -t 28800 -w '+str(pid) in q.stdout:print('Keep-awake already active');return
 p=subprocess.Popen(['/usr/bin/caffeinate','-i','-s','-t','28800','-w',str(pid)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
 pf.write_text(str(p.pid))
 print('Keep-awake active for at most 8 hours, bound to this server. Keep lid open and connect power.')
def awake_stop(ctl):
 pf=ctl.LOCAL/'awake.pid'
 if pf.exists():
  q=subprocess.run(['ps','-o','command=','-p',pf.read_text().strip()],capture_output=True,text=True)
  if 'caffeinate -i -s -t 28800 -w ' in q.stdout:os.kill(int(pf.read_text()),signal.SIGTERM)
  pf.unlink(missing_ok=True)
def logs(ctl,role='server'):
 if role not in [*ctl.ROLES,'proxy','login-gateway','tunnel']:raise RuntimeError('Unknown log role')
 f=(ctl.DEFAULT if role=='tunnel' else ctl.LOCAL)/(role+'.log')
 if not f.exists():raise RuntimeError('No log for '+role)
 values=[]
 for p in [ctl.LOCAL/'credentials.properties',ctl.DEFAULT/'credentials.properties']:
  if p.exists():values += [l.split('=',1)[1] for l in p.read_text().splitlines() if '=' in l]
 # Limit memory and output, redact known credentials and UUID session tokens.
 with f.open('rb') as s:s.seek(max(0,f.stat().st_size-32000));text=s.read().decode(errors='replace')
 text='\n'.join(text.splitlines()[-40:])
 for v in values:text=text.replace(v,'[REDACTED]')
 text=re.sub(r'\b[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}\b','[SESSION-ID]',text)
 print(text)
