"""Offline private-LAN participant proxy. Backend services remain on 127.0.0.1."""
from pathlib import Path
import os,json,subprocess,ipaddress,time,signal,re,hashlib
from urllib.parse import urlsplit
ROOT=Path(__file__).resolve().parents[2]
from runtime_paths import executable
OPENSSL=executable('openssl','LCPC_OPENSSL',('/opt/homebrew/bin/openssl',))
CADDY=ROOT/'.local/tools/caddy'
DNS_SD='/usr/bin/dns-sd'
SHORT_HOSTNAME='lcpc.local'
SOCKET_PATTERN=r'^/websocket/WTISocket/[0-9a-fA-F]{8}(-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}$'
def prepare(ctl,bind='127.0.0.1',cidr='127.0.0.1/32',transport='https',*,hostname=None,automatic=False,interface=None):
 pf=ctl.LOCAL/'proxy.pid'
 if pf.exists():
  q=subprocess.run(['ps','-o','command=','-p',pf.read_text().strip()],capture_output=True,text=True)
  if str(ctl.LOCAL/'network/Caddyfile') in q.stdout:raise RuntimeError('Run network-stop before changing certificates or network profile')
 if transport not in ('https','http'):raise RuntimeError('Unsupported transport')
 if hostname and (transport!='http' or not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.local',hostname)):raise RuntimeError('Use this Mac’s local hostname with the authorized HTTP LAN profile')
 if transport=='http':verify_private_lan(bind,cidr)
 ip=ipaddress.ip_address(bind);net=ipaddress.ip_network(cidr,strict=False)
 if ip.version!=4 or net.version!=4 or not ip.is_private or ip.is_unspecified or ip.is_multicast or ip not in net:raise RuntimeError('Use a specific private/local IPv4 address within the allowed CIDR')
 d=ctl.LOCAL/'network';d.mkdir(mode=0o700,exist_ok=True)
 # No OS trust store modification; clients must explicitly trust the CA.
 ca_key=d/'ca.key';ca=d/'ca.crt';key=d/'server.key';cert=d/'server.crt'
 def run(a):subprocess.run([OPENSSL,*a],check=True,capture_output=True)
 if transport=='https':
  if not ca_key.exists():run(['req','-new','-x509','-newkey','rsa:3072','-nodes','-days','3650','-subj','/CN=LCPC OMU Local CA/','-addext','basicConstraints=critical,CA:TRUE','-addext','keyUsage=critical,keyCertSign,cRLSign','-keyout',str(ca_key),'-out',str(ca)])
  run(['req','-new','-newkey','rsa:2048','-nodes','-subj','/CN='+bind,'-keyout',str(key),'-out',str(d/'server.csr')])
  (d/'server.ext').write_text('subjectAltName=IP:'+bind+'\nextendedKeyUsage=serverAuth\nbasicConstraints=CA:FALSE\nkeyUsage=digitalSignature,keyEncipherment\n')
  run(['x509','-req','-in',str(d/'server.csr'),'-CA',str(ca),'-CAkey',str(ca_key),'-CAcreateserial','-days','365','-extfile',str(d/'server.ext'),'-out',str(cert)])
 public=d/'web/assets';public.mkdir(parents=True,exist_ok=True)
 origin=transport+'://'+bind+(':'+str(8443 if transport=='https' else 8088))
 hostname_origin='http://'+hostname+':8088' if hostname else None
 additional_origins=['http://'+machine_hostname()+':8088'] if automatic and machine_hostname()!=hostname else []
 origins=[origin]+([hostname_origin] if hostname_origin else [])+additional_origins
 origin_pattern='^('+'|'.join(value.replace('.','[.]') for value in origins)+')$'
 socket_origin=('wss' if transport=='https' else 'ws')+'://'+origin.split('://',1)[1]
 tls_line=f' tls "{cert}" "{key}"' if transport=='https' else ''
 (public/'appconfig.json').write_text(json.dumps({'baseUrl':origin+'/api','websocketUrl':socket_origin+'/websocket/WTISocket'})+'\n')
 config=f'''{{
 admin off
 auto_https off
 servers {{
  protocols h1 h2
  expected_underscore_headers team_id
  timeouts {{
   read_header 10s
   read_body 15s
   idle 2m
  }}
 }}
}}
{', '.join(origins)} {{
 bind {bind}
{tls_line}
 route {{
 @outside not remote_ip {cidr}
 respond @outside 403
 @badOrigin {{
  header Origin *
  not header_regexp allowedOrigin Origin "{origin_pattern}"
 }}
 respond @badOrigin 403
 @invalidSocket {{
  path /websocket/*
  not path_regexp socketSession "{SOCKET_PATTERN}"
 }}
 respond @invalidSocket 403
 header {{
  -Server
  X-Content-Type-Options nosniff
  Referrer-Policy no-referrer
  X-Frame-Options DENY
 }}
 request_body {{
  max_size 2MB
 }}
 handle /swagger* {{
  respond 404
 }}
 handle /assets/appconfig.json {{
  header Cache-Control no-store
  reverse_proxy 127.0.0.1:8090 {{
   header_up X-LCPC-Peer {{remote_host}}
  }}
 }}
 @participantResources path /problems /problems/* /instructions /instructions/* /api/teams/resources-session /api/teams/resources /api/teams/logout
 handle @participantResources {{
  header Cache-Control "no-store, private"
  reverse_proxy 127.0.0.1:8090 {{
   header_up X-LCPC-Peer {{remote_host}}
  }}
 }}
 handle /api/teams/login {{
  reverse_proxy 127.0.0.1:8090 {{
   header_up X-LCPC-Peer {{remote_host}}
  }}
 }}
 @submission {{
  path /api/teams/run
  method POST
 }}
 handle @submission {{
  reverse_proxy 127.0.0.1:8090 {{
   header_up X-LCPC-Peer {{remote_host}}
  }}
 }}
 @participantAPI path /api/teams/* /api/contest/* /api/contests/*
 handle @participantAPI {{
  reverse_proxy 127.0.0.1:8090 {{
   header_up X-LCPC-Peer {{remote_host}}
  }}
 }}
 handle {{
  reverse_proxy 127.0.0.1:{ctl.ports()['web_port']} {{
   transport http {{
    dial_timeout 3s
    response_header_timeout 15s
   }}
  }}
 }}
 }}
}}
'''
 (d/'Caddyfile').write_text(config)
 profile={'bind':bind,'cidr':cidr,'origin':origin,'transport':transport,'lan_confirmed':False,'insecure_lan_authorized':transport=='http'}
 if hostname:profile.update(hostname=hostname,hostname_origin=hostname_origin)
 if additional_origins:profile['additional_origins']=additional_origins
 if automatic:profile.update(automatic=True,interface=interface)
 (d/'profile.json').write_text(json.dumps(profile,indent=2)+'\n')
 for p in d.iterdir():
  if p.is_file():p.chmod(0o600)
 if CADDY.exists():subprocess.run([str(CADDY),'validate','--config',str(d/'Caddyfile'),'--adapter','caddyfile'],check=True,capture_output=True)
 print(transport.upper()+' profile prepared: '+origin)
 if not ip.is_loopback:print('LAN binding is configured only; not activated or approved.')
 return d

def frontend_config(profile,host):
 """Use the page's approved hostname/IP, never an arbitrary Host header."""
 for origin in [profile['origin'],profile.get('hostname_origin'),*profile.get('additional_origins',[])]:
  if origin and host.lower()==urlsplit(origin).netloc.lower():
   return {'baseUrl':origin+'/api','websocketUrl':('wss' if origin.startswith('https:') else 'ws')+'://'+urlsplit(origin).netloc+'/websocket/WTISocket'}
 raise ValueError('Unknown participant host')

def start(ctl,*,watcher=False):
 d=ctl.LOCAL/'network';p=json.loads((d/'profile.json').read_text())
 gateway_port=int(p.get('gateway_port',8090))
 if gateway_port not in (8090,8092):raise RuntimeError('Invalid managed participant gateway port')
 if p.get('automatic') and not watcher:return enable_auto(ctl)
 if not ipaddress.ip_address(p['bind']).is_loopback:
  if not p.get('lan_confirmed'):raise RuntimeError('Confirm the actual private contest LAN with network-confirm before activation')
  verify_private_lan(p['bind'],p['cidr'])
 if not CADDY.exists():raise RuntimeError('Verified Caddy binary not installed yet')
 for role,c in [('login-gateway',[os.sys.executable,str(ROOT/'lcpc/infra/login_gateway.py'),'--port',str(gateway_port),'--backend',str(ctl.ports()['web_port']),'--state-tag',str(ctl.LOCAL)]),('proxy',[str(CADDY),'run','--config',str(d/'Caddyfile'),'--adapter','caddyfile'])]:
  pf=ctl.LOCAL/(role+'.pid')
  if pf.exists():
   try:
    pid=int(pf.read_text());os.kill(pid,0)
    args=subprocess.check_output(['ps','-o','command=','-p',str(pid)],text=True)
    needle=str(d/'Caddyfile') if role=='proxy' else str(ctl.LOCAL)
    if needle in args and ('caddy' if role=='proxy' else 'login_gateway.py') in args:continue
    if args.strip():raise RuntimeError('PID identity mismatch for '+role)
   except (ProcessLookupError,subprocess.CalledProcessError):pass
  env={**os.environ,'XDG_CONFIG_HOME':str(d/'runtime/config'),'XDG_DATA_HOME':str(d/'runtime/data')}
  with (ctl.LOCAL/(role+'.log')).open('ab') as log:proc=subprocess.Popen(c,cwd=ROOT,env=env,stdout=log,stderr=log,start_new_session=True)
  pf.write_text(str(proc.pid));time.sleep(.5)
  if proc.poll() is not None:raise RuntimeError(role+' failed; inspect private log')
 if p.get('automatic'):ensure_local_name(ctl,p)
 print('Participant proxy started: '+p['origin']+'; allowed CIDR '+p['cidr'])

def verify_private_lan(bind,cidr):
 ip=ipaddress.ip_address(bind);net=ipaddress.ip_network(cidr,strict=False)
 allowed=[ipaddress.ip_network(n) for n in ['10.0.0.0/8','172.16.0.0/12','192.168.0.0/16']]
 if ip.version!=4 or net.version!=4 or ip not in net or not any(net.subnet_of(n) for n in allowed):raise RuntimeError('LAN must use a specific RFC1918 IPv4 address and CIDR; public and wildcard binding forbidden')
 q=subprocess.run(['/sbin/ifconfig'],capture_output=True,text=True,check=True)
 addresses=[l.strip().split()[1] for l in q.stdout.splitlines() if l.strip().startswith('inet ')]
 if bind not in addresses:raise RuntimeError('Configured LAN IP is not assigned to this Mac. Stop and prepare the new profile.')

def confirm(ctl,bind,cidr):
 d=ctl.LOCAL/'network';p=json.loads((d/'profile.json').read_text())
 if p['bind']!=bind or p['cidr']!=cidr:raise RuntimeError('Confirmation must match the prepared IP and CIDR exactly')
 verify_private_lan(bind,cidr);p['lan_confirmed']=True
 (d/'profile.json').write_text(json.dumps(p,indent=2)+'\n')
 print('Private contest LAN confirmed: '+p['origin']+' within '+cidr)

def stop(ctl):
 for role,needle in [('network-watch',str(ROOT/'lcpc/infra/network_watch.py')),('local-name',DNS_SD),('proxy',str(CADDY)),('login-gateway',str(ROOT/'lcpc/infra/login_gateway.py'))]:
  stop_role(ctl,role,needle)

def stop_role(ctl,role,needle):
  pf=ctl.LOCAL/(role+'.pid')
  if not pf.exists():return
  try:
   pid=int(pf.read_text());cmd=subprocess.check_output(['ps','-o','command=','-p',str(pid)],text=True)
   state_marker=process_marker(ctl,role)
   if needle not in cmd or state_marker not in cmd:raise RuntimeError('PID identity mismatch for '+role)
   os.kill(pid,signal.SIGTERM)
   deadline=time.monotonic()+5
   while time.monotonic()<deadline:
    state=subprocess.run(['ps','-o','stat=','-p',str(pid)],capture_output=True,text=True).stdout.strip()
    if not state or state.startswith('Z'):break
    time.sleep(.05)
   else:raise RuntimeError(role+' did not stop; preserving its PID')
   pf.unlink(missing_ok=True)
  except (ProcessLookupError,subprocess.CalledProcessError):pass

def role_running(ctl,role,needle):
 pf=ctl.LOCAL/(role+'.pid')
 if not pf.exists():return False
 pid=pf.read_text().strip()
 q=subprocess.run(['ps','-o','stat=,command=','-p',pid],capture_output=True,text=True)
 state=q.stdout.strip()
 if not state or state.split()[0].startswith('Z'):return False
 marker=process_marker(ctl,role)
 if needle not in state or marker not in state:raise RuntimeError('PID identity mismatch for '+role)
 return True

def process_marker(ctl,role):
 if role=='local-name':return 'LCPC-'+hashlib.sha256(str(ctl.LOCAL).encode()).hexdigest()[:10]
 return str(ctl.LOCAL/'network/Caddyfile') if role=='proxy' else str(ctl.LOCAL)

def local_hostname():return SHORT_HOSTNAME

def machine_hostname():
 name=subprocess.check_output(['/usr/sbin/scutil','--get','LocalHostName'],text=True).strip().lower()
 if not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?',name):raise RuntimeError('A valid Mac local hostname is required')
 return name+'.local'

def ensure_local_name(ctl,profile):
 """Publish a short Bonjour alias without renaming the Mac or editing clients."""
 if profile['hostname']==machine_hostname():
  stop_role(ctl,'local-name',DNS_SD);return
 registration={'hostname':profile['hostname'],'ip':profile['bind']}
 saved=ctl.LOCAL/'network/local-name.json'
 if role_running(ctl,'local-name',DNS_SD):
  if saved.exists() and json.loads(saved.read_text())==registration:return
  stop_role(ctl,'local-name',DNS_SD)
 command=[DNS_SD,'-P',process_marker(ctl,'local-name'),'_http._tcp','local.','8088',profile['hostname'],profile['bind']]
 with (ctl.LOCAL/'local-name.log').open('ab') as log:
  proc=subprocess.Popen(command,stdout=log,stderr=log,start_new_session=True)
 (ctl.LOCAL/'local-name.pid').write_text(str(proc.pid));time.sleep(.5)
 if proc.poll() is not None:raise RuntimeError('Local name registration failed; inspect local-name.log')
 saved.write_text(json.dumps(registration)+'\n')

def current_lan(preferred=None):
 from lan_info import addresses
 rows=addresses(subprocess.check_output(['/sbin/ifconfig'],text=True))
 route=subprocess.run(['/sbin/route','-n','get','default'],capture_output=True,text=True)
 match=re.search(r'^\s*interface:\s*(\S+)',route.stdout,re.M)
 for interface in [match.group(1) if match else None,preferred]:
  candidates=[r for r in rows if interface and r['interface']==interface]
  if len(candidates)==1:return candidates[0]
 if len(rows)==1:return rows[0]
 raise RuntimeError('No unambiguous private LAN is connected')

def adaptive_update(ctl):
 path=ctl.LOCAL/'network/profile.json';profile=json.loads(path.read_text())
 if profile.get('transport')!='http' or not profile.get('insecure_lan_authorized'):raise RuntimeError('Adaptive access requires the organizer-authorized private HTTP LAN profile')
 row=current_lan(profile.get('interface'));hostname=local_hostname()
 changed=not profile.get('automatic') or any(profile.get(k)!=v for k,v in {'bind':row['ip'],'cidr':row['cidr'],'hostname':hostname,'interface':row['interface']}.items())
 if changed:
  verify_private_lan(row['ip'],row['cidr'])
  stop_role(ctl,'proxy',str(CADDY))
  prepare(ctl,row['ip'],row['cidr'],'http',hostname=hostname,automatic=True,interface=row['interface'])
  confirm(ctl,row['ip'],row['cidr'])
 start(ctl,watcher=True)
 return json.loads(path.read_text())

def enable_auto(ctl):
 profile=adaptive_update(ctl)
 script=ROOT/'lcpc/infra/network_watch.py';pf=ctl.LOCAL/'network-watch.pid'
 if role_running(ctl,'network-watch',str(script)):
  print('Adaptive LAN already active: '+profile['hostname_origin']+'/#/login');return
 with (ctl.LOCAL/'network-watch.log').open('ab') as log:
  proc=subprocess.Popen([os.sys.executable,'-B',str(script),'--state',str(ctl.LOCAL)],cwd=ROOT,stdout=log,stderr=log,start_new_session=True)
 pf.write_text(str(proc.pid));time.sleep(.3)
 if proc.poll() is not None:raise RuntimeError('Adaptive LAN monitor failed; inspect network-watch.log')
 print('Adaptive LAN active: '+profile['hostname_origin']+'/#/login')
