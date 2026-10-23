#!/usr/bin/env python3
"""Follow private LAN changes; never log in to PC2 or change contest state."""
import argparse,fcntl,json,os,signal,sys,time
from pathlib import Path
parser=argparse.ArgumentParser();parser.add_argument('--state',required=True);args=parser.parse_args()
os.environ['LCPC_STATE_DIR']=str(Path(args.state).resolve())
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pc2ctl as ctl
from infra import network
running=True
def finish(*_):
 global running
 running=False
signal.signal(signal.SIGTERM,finish);signal.signal(signal.SIGINT,finish)
with (ctl.LOCAL/'network-auto.lock').open('a') as lock:
 try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 except BlockingIOError:raise SystemExit('An adaptive LAN monitor is already active')
 last=None
 while running:
  try:
   profile=json.loads((ctl.LOCAL/'network/profile.json').read_text())
   if not profile.get('automatic'):break
   if not ctl.pid_for('server'):break
   row=network.current_lan(profile.get('interface'))
   needs_change=any(profile.get(k)!=row[key] for k,key in [('bind','ip'),('cidr','cidr'),('interface','interface')]) or profile.get('hostname')!=network.local_hostname()
   proxy_ready=network.role_running(ctl,'proxy',str(network.CADDY))
   gateway_ready=network.role_running(ctl,'login-gateway',str(network.ROOT/'lcpc/infra/login_gateway.py'))
   name_ready=profile['hostname']==network.machine_hostname() or network.role_running(ctl,'local-name',network.DNS_SD)
   if needs_change or not proxy_ready or not gateway_ready or not name_ready:profile=network.adaptive_update(ctl)
   status={'available':True,'origin':profile['origin'],'hostname_origin':profile['hostname_origin'],'interface':profile['interface']}
  except Exception as error:
   status={'available':False,'message':str(error)}
   try:
    network.stop_role(ctl,'local-name',network.DNS_SD)
    network.stop_role(ctl,'proxy',str(network.CADDY))
   except Exception as stop_error:status['stop_error']=str(stop_error)
  if status!=last:
   status_file=ctl.LOCAL/'network/auto-status.json';temp=status_file.with_suffix('.tmp')
   temp.write_text(json.dumps({**status,'updated':time.time()},indent=2)+'\n');temp.replace(status_file)
   print(json.dumps(status),flush=True);last=status
  for _ in range(30):
   if not running:break
   time.sleep(.1)
