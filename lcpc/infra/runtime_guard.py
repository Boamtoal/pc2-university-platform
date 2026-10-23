"""Fail closed when a second managed PC2 server is requested."""
from pathlib import Path
import json,shlex,subprocess

def server_states(root):
 result=subprocess.run(['ps','-axo','stat=,command='],capture_output=True,text=True,check=True);states=[]
 for line in result.stdout.splitlines():
  parts=line.strip().split(None,1)
  if len(parts)!=2 or parts[0].startswith('Z'):continue
  try:args=shlex.split(parts[1])
  except ValueError:continue
  if not args or Path(args[0]).name!='java' or 'LCPCLaunch' not in args:continue
  index=args.index('LCPCLaunch')
  if args[index+1:index+2]!=['server']:continue
  value=next((a.split('=',1)[1] for a in args if a.startswith('-Dlcpc.secrets=')),None)
  if value:
   path=Path(value).resolve()
   if path.is_relative_to(Path(root).resolve()):states.append(path.parent)
 return states

def ensure_single(root,state):
 state=Path(state).resolve()
 if any(other!=state for other in server_states(root)):raise RuntimeError('Another contest server is active. Deactivate it before starting this contest. A paused clock still occupies the server.')
 registry=Path(root)/'.local/contest-manager/registry.json'
 if registry.exists():
  data=json.loads(registry.read_text());active=data.get('active')
  row=next((r for r in data.get('contests',[]) if r['id']==active),None)
  if row and Path(row['state']).resolve()!=state:raise RuntimeError('Another contest is reserved as active: '+active+'. Deactivate it first.')
