"""Non-destructive health checks. No contest clock changes and no submissions."""
from pathlib import Path
import os,json,subprocess,urllib.request,time,shutil,ssl

def resources():
 d=shutil.disk_usage(Path(__file__).resolve().parents[2]);load=os.getloadavg()
 p=subprocess.run(['memory_pressure','-Q'],capture_output=True,text=True,timeout=5)
 pct=None
 import re
 m=re.search(r'free percentage:\s*(\d+)%',p.stdout)
 if m:pct=int(m.group(1))
 return {'disk_free_gib':round(d.free/1024**3,2),'load_1min':round(load[0],2),'memory_free_percentage':pct}

def inspect(ctl,mode='local'):
 if mode not in ['local','isolated-trial','production','competition']:raise RuntimeError('Unknown health mode')
 result={'mode':mode,'timestamp':time.time(),'resources':resources(),'checks':[]}
 def add(name,status,detail):result['checks'].append({'name':name,'status':status,'detail':detail})
 for role in ['server','wti','judge']:
  try:
   pid=ctl.pid_for(role)
   if role=='judge' and mode!='local':
    add('no_macos_autojudge','VERIFIED' if not pid else 'BLOCKED','Mac AutoJudge '+('stopped' if not pid else 'RUNNING'));continue
   add(role,'VERIFIED' if pid else 'BLOCKED','running' if pid else 'stopped')
   if pid and role in ['server','wti']:ctl.listener_check(role,pid)
   if pid and mode!='local' and role in ['server','wti']:
    args=subprocess.run(['ps','-o','command=','-p',str(pid)],capture_output=True,text=True).stdout
    add(role+'_mac_execution_disabled','VERIFIED' if '-Dlcpc.denyExecution=true' in args else 'BLOCKED','all Mac compile/run paths must be disabled in isolated mode')
  except Exception as e:add(role,'BLOCKED',str(e))
 try:
  with urllib.request.urlopen('http://127.0.0.1:'+str(ctl.ports()['web_port'])+'/',timeout=5) as r:
   body=r.read(40000);add('wti_http','VERIFIED' if r.status==200 and b'<html' in body.lower() else 'BLOCKED','HTTP '+str(r.status))
 except Exception as e:add('wti_http','BLOCKED',str(e))
 try:
  q=ctl.api(['status'],capture=True)
  add('server_authenticated_api','VERIFIED' if q.returncode==0 else 'BLOCKED','authenticated scoreboard account' if not q.returncode else 'failed; inspect private logs')
 except Exception as e:add('server_authenticated_api','BLOCKED',str(e))
 r=result['resources'];add('host_disk','VERIFIED' if r['disk_free_gib']>=8 else 'BLOCKED',str(r['disk_free_gib'])+' GiB free; require >=8')
 add('host_memory','VERIFIED' if r['memory_free_percentage'] is not None and r['memory_free_percentage']>=10 else 'BLOCKED',str(r['memory_free_percentage'])+'% free; require >=10')
 secret=ctl.LOCAL/'credentials.properties'
 add('credentials_permissions','VERIFIED' if secret.stat().st_mode&0o077==0 and ctl.LOCAL.stat().st_mode&0o077==0 else 'BLOCKED','private state and credentials must exclude other users')
 if mode!='local':
  try:add('no_macos_manual_judge','VERIFIED' if not ctl.pid_for('judge2') else 'BLOCKED','manual Mac judging must remain stopped')
  except Exception as e:add('no_macos_manual_judge','BLOCKED',str(e))
  from infra.vm import vm_health
  try:
   j=vm_health(ctl);add('linux_judge','VERIFIED' if j['ready'] else 'BLOCKED',j)
  except Exception as e:add('linux_judge','BLOCKED',str(e))
  profile=ctl.LOCAL/'network/profile.json'
  if profile.exists():
   try:
    profile_data=json.loads(profile.read_text());origin=profile_data['origin']
    is_http=profile_data.get('transport')=='http'
    if is_http:
     from infra.network import verify_private_lan
     if not profile_data.get('insecure_lan_authorized') or not profile_data.get('lan_confirmed'):raise RuntimeError('HTTP requires explicit organizer authorization and confirmed private LAN')
     verify_private_lan(profile_data['bind'],profile_data['cidr'])
     if origin!='http://'+profile_data['bind']+':8088':raise RuntimeError('Unexpected HTTP origin')
    context=None if is_http else ssl.create_default_context(cafile=str(profile.parent/'ca.crt'))
    with urllib.request.urlopen(origin+'/assets/appconfig.json',context=context,timeout=5) as response:
     config=json.load(response);socket_origin=('ws' if is_http else 'wss')+'://'+origin.split('://',1)[1]
     ok=config['baseUrl']==origin+'/api' and config['websocketUrl']==socket_origin+'/websocket/WTISocket'
     add('participant_http' if is_http else 'participant_https','VERIFIED' if ok else 'BLOCKED','Organizer-authorized HTTP on confirmed private LAN' if is_http else 'TLS certificate verified; HTTPS/WSS origin matches')
   except Exception as e:add('participant_proxy','BLOCKED',str(e))
 if mode=='production':
  gate=ctl.LOCAL/'production-acceptance.json'
  add('production_acceptance','BLOCKED','real LAN, trust deployment and integrated isolated load/recovery evidence must be approved; no production acceptance recorded')
 result['ready']=all(x['status']=='VERIFIED' for x in result['checks'])
 print(json.dumps(result,ensure_ascii=False,indent=2))
 return result
