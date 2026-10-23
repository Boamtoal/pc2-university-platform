#!/usr/bin/env python3
"""Explicit lifecycle for the private organizer dashboard."""
import argparse,base64,json,os,secrets,signal,socket,subprocess,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from core import Store,Bridge,ROOT

def pid(state):
 file=state/'admin-dashboard/dashboard.pid'
 if not file.exists():return None
 try:
  number=int(file.read_text());result=subprocess.run(['ps','-o','stat=,command=','-p',str(number)],capture_output=True,text=True).stdout.strip()
  if not result or result.startswith('Z'):return None
  if str(ROOT/'lcpc/admin/server.py') not in result or str(state) not in result:raise RuntimeError('Dashboard PID identity mismatch')
  return number
 except ProcessLookupError:return None

def initialize(state):
 os.umask(0o077);store=Store(state);credential=store.initialize();service=store.base/'bridge.properties'
 if not service.exists():service.write_text('username=administrator2\npassword='+secrets.token_urlsafe(32)+'\n');service.chmod(0o600)
 work=store.base/'bridge';work.mkdir(mode=0o700,exist_ok=True);(work/'pc2v9.ini').write_text('[client]\nserver=127.0.0.1:50002\n')
 bridge=Bridge(state)
 if not (store.base/'provisioned').exists():
  # Refuse to displace an organizer's live native administrator session.
  processes=subprocess.check_output(['ps','-axo','command='],text=True)
  if any('LCPCLaunch admin' in line and str(state/'credentials.properties') in line for line in processes.splitlines()):raise RuntimeError('Close the native Administrator window once before dashboard initialization; no account was displaced')
  with (store.base/'provision.log').open('ab') as log:
   run=subprocess.run(bridge.command_line('provision'),cwd=work,stdout=subprocess.PIPE,stderr=log,text=True,timeout=40)
  if run.returncode or '"ok":true' not in run.stdout:raise RuntimeError('Service account setup failed; inspect the private provision log')
  (store.base/'provisioned').write_text('Dedicated dashboard service account configured\n')
 try:
  snapshot=bridge.snapshot()
  if not store.resources():
   problems=snapshot['problems'];source=state/'participant-resources/problems'
   for problem in problems:
    file=source/(problem['letter']+'.pdf')
    if file.exists():
     rid=store.upload({'problem':problem['id'],'kind':'statement','language':'en','label':'English statement','filename':file.name,'base64':base64.b64encode(file.read_bytes()).decode()},trusted=True)
     with store.db() as db:db.execute('UPDATE resources SET published=1 WHERE id=?',(rid,))
   file=source/'booklet.pdf'
   if file.exists():
    rid=store.upload({'problem':'__contest__','kind':'booklet','language':'en','label':'Complete problem booklet','filename':'booklet.pdf','base64':base64.b64encode(file.read_bytes()).decode()},trusted=True)
    with store.db() as db:db.execute('UPDATE resources SET published=1 WHERE id=?',(rid,))
  store.publish_catalog(snapshot);store.audit('system','dashboard.provisioned','success',details={'teams':len(snapshot['teams']),'problems':len(snapshot['problems'])})
 finally:bridge.close()
 print('Dashboard initialized; current contest clock, runs and existing teams preserved.')
 if credential:print('Initial login saved in private file:',credential)

def start(state,prepare_learning=False):
 if pid(state):print('Dashboard already running: http://127.0.0.1:8091/');return
 if not (state/'admin-dashboard/provisioned').exists() and not (state/'admin-dashboard/draft.json').exists():raise RuntimeError('Initialize the dashboard first')
 base=state/'admin-dashboard'
 command=[sys.executable,'-B',str(ROOT/'lcpc/admin/server.py'),'--state',str(state)]
 if prepare_learning:command.append('--prepare-learning')
 with (base/'server.log').open('ab') as log:process=subprocess.Popen(command,cwd=ROOT,stdout=log,stderr=log,start_new_session=True)
 (base/'dashboard.pid').write_text(str(process.pid))
 for _ in range(40):
  if process.poll() is not None:raise RuntimeError('Dashboard failed to start; inspect private server.log')
  try:
   with socket.create_connection(('127.0.0.1',8091),timeout=.2):break
  except OSError:time.sleep(.1)
 else:raise RuntimeError('Dashboard startup timed out')
 print('Organizer dashboard: http://127.0.0.1:8091/ (this computer only)')
def stop(state):
 number=pid(state)
 if number:
  os.kill(number,signal.SIGTERM)
  for _ in range(80):
   if not pid(state):break
   time.sleep(.1)
  else:raise RuntimeError('Dashboard did not stop; not forcibly killing it')
 (state/'admin-dashboard/dashboard.pid').unlink(missing_ok=True);print('Dashboard stopped')
def main():
 os.umask(0o077);parser=argparse.ArgumentParser();parser.add_argument('action',choices=['init','start','stop','status']);parser.add_argument('--state');parser.add_argument('--prepare-learning',action='store_true');args=parser.parse_args()
 sys.path.insert(0,str(ROOT/'lcpc'));from workspace_state import managed_state
 state=Path(args.state).resolve() if args.state else managed_state()
 if args.action=='init':initialize(state)
 elif args.action=='start':start(state,args.prepare_learning)
 elif args.action=='stop':stop(state)
 else:print(json.dumps({'running':bool(pid(state)),'url':'http://127.0.0.1:8091/','scope':'loopback only'}))
if __name__=='__main__':
 try:main()
 except Exception as error:raise SystemExit(str(error))
