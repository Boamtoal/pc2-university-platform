"""Read-only LAN access inventory and bounded probes of the selected contest only."""
import hashlib,ipaddress,json,ssl,subprocess,time,urllib.request,urllib.error
from pathlib import Path
from core import ROOT,stamp
from lan_info import addresses
NETWORKS=[ipaddress.ip_network(v) for v in ('10.0.0.0/8','172.16.0.0/12','192.168.0.0/16')]
_cached=(0,[])
def local_addresses():
 global _cached
 if time.monotonic()-_cached[0]>5:
  text=subprocess.check_output(['/sbin/ifconfig'],text=True,timeout=2);_cached=(time.monotonic(),addresses(text))
 return _cached[1]
def access(app,*,active_workspace=False):
 active_id=app.manager.data['active'];row=app.manager.row(active_id) if active_workspace and active_id else app.manager.selected();active=app.manager.data['active']==row['id'];result={'active':active,'checkedAt':stamp(),'origin':None,'ip':None,'interface':None,'port':None,'assigned':False,'automatic':False,'links':[],'addresses':[]}
 try:result['addresses']=local_addresses()
 except (OSError,subprocess.SubprocessError):result['addressError']='Local interface information is unavailable.'
 if not active:return result
 try:
  profile=json.loads((Path(row['state'])/'network/profile.json').read_text());u=urllib.parse.urlsplit(profile['origin']);ip=ipaddress.ip_address(u.hostname)
  if ip.version!=4 or not any(ip in net for net in NETWORKS) or u.scheme not in ('http','https') or u.port!=(8088 if u.scheme=='http' else 8443) or u.username or u.password or u.path not in ('','/') or u.query or u.fragment:return result
  result.update(ip=str(ip),interface=profile.get('interface'),port=u.port,automatic=bool(profile.get('automatic')),transport=u.scheme.upper(),configuredOrigin=profile['origin'])
  matches=[a for a in result['addresses'] if a['ip']==str(ip)];result['assigned']=bool(matches)
  if not matches:return result
  result['interface']=matches[0]['interface'];result['cidr']=matches[0]['cidr'];result['origin']=profile['origin'].rstrip('/')
  for label,path,protected in [('Team login','/#/login',False),('Instructions','/instructions/',False),('Problem PDFs','/problems/',True),('Team scoreboard','/#/scoreboard',True),('Public Scoreboard','/standings/',False)]:result['links'].append({'label':label,'url':result['origin']+path,'requiresLogin':protected})
 except (OSError,ValueError,KeyError):pass
 return result
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*args):return None
def probe(state,url):
 handlers=[urllib.request.ProxyHandler({}),NoRedirect()]
 if url.startswith('https:'):handlers.append(urllib.request.HTTPSHandler(context=ssl.create_default_context(cafile=str(state/'network/ca.crt'))))
 opener=urllib.request.build_opener(*handlers)
 try:
  with opener.open(urllib.request.Request(url,headers={'User-Agent':'Organizer-read-only-check','Cache-Control':'no-cache'}),timeout=2) as response:return response.status,response.read(131073),dict(response.headers)
 except urllib.error.HTTPError as error:
  try:return error.code,error.read(4096),dict(error.headers)
  finally:error.close()
def checks(app):
 info=access(app);state=Path(app.manager.selected()['state']);rows=[]
 def add(name,status,detail):rows.append({'name':name,'status':status,'detail':detail})
 add('Managed LAN address','passed' if info['origin'] else 'failed','Assigned to '+str(info['interface'])+' · '+str(info['ip']) if info['origin'] else 'Activate this workspace and wait for an assigned managed LAN address.')
 if info['origin']:
  for name,path,kind in [('Participant login page','/','html'),('Participant configuration','/assets/appconfig.json','config'),('Public instructions','/instructions/','html'),('Private problem PDFs','/problems/','protected')]:
   try:
    status,body,headers=probe(state,info['origin']+path)
    valid=(status==200 and b'<html' in body.lower()) if kind=='html' else (status in (302,303,401,403)) if kind=='protected' else (status==200 and isinstance(json.loads(body),dict))
    add(name,'passed' if valid else 'failed','HTTP '+str(status)+(' · Sign-in required' if valid and kind=='protected' else ''))
   except Exception:add(name,'failed','The managed endpoint could not be verified; check service logs. TLS verification is never disabled.')
 if info['active']:
  try:
   judges=app.bridge.call('admin.query',{'section':'autojudges'})['rows'];connections=app.bridge.call('admin.query',{'section':'connections'})['rows'];online={r['client'] for r in connections if r.get('connected')};ready=[j['login'] for j in judges if j['enabled'] and j.get('online',j['login'] in online)]
   add('Automatic judge connection','passed' if ready else 'warning',', '.join(ready) if ready else 'No enabled automatic judge is connected. Human-only judging can be intentional.')
  except Exception:add('PC² judge connection','failed','Native connection information is unavailable.')
 snapshot=app.bridge.snapshot();active=[p for p in snapshot.get('problems',[]) if p.get('active')];missing=[p['letter'] for p in active if not p.get('tests')]
 add('Active problem judge data','passed' if active and not missing else 'failed',str(len(active))+' active problems; missing cases: '+(', '.join(missing) or 'none'))
 value={'checkedAt':stamp(),'contestId':app.manager.data['selected'],'checks':rows,'scope':'Read-only server checks. Full submission, verdict, notification and device-network scenarios require the participant rehearsal.'};return value
SCENARIOS={'login','refresh','pdf_en','pdf_ar','attachments','clarifications','pending','scoreboard','human_approval','accepted','wrong_answer','compile_error','runtime_error','time_limit'}
def configuration(snapshot,resources):
 payload={'problems':snapshot.get('problems',[]),'languages':snapshot.get('languages',[]),'judging':snapshot.get('judging',{}),'resources':[{k:r.get(k) for k in ('id','version','sha256','published')} for r in resources]}
 return hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()
