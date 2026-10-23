"""Control-plane identity only. Participant branding files are never edited here."""
import base64,binascii,hashlib,json,re,struct,zlib
from core import ROOT,require
DEFAULT={'name':'LCPC OMU','subtitle':'Organizer workspace','primaryColor':'#173f68','sidebarColor':'#102b47','activeIndicatorColor':'#eab746','activeSectionColor':'#173f68','menuHoverColor':'#244664','rowHoverColor':'#eaf2fa','focusColor':'#e9b73d','logo':None}
def load(store):
 with store.db() as db:row=db.execute("SELECT value FROM settings WHERE key='dashboard.branding'").fetchone()
 saved=json.loads(row[0]) if row else {}
 return {**DEFAULT,**saved,'activeSectionColor':saved.get('activeSectionColor',saved.get('primaryColor',DEFAULT['activeSectionColor']))}
def version(value):return hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()
def public(store):
 value=load(store);return {k:v for k,v in value.items() if k!='logo'}|{'customLogo':bool(value['logo']),'version':version(value),'logoUrl':'/api/dashboard-branding/logo?v='+version(value)}
def image(raw,*,max_dimension=2048):
 require(isinstance(raw,str) and len(raw)<=1400000,'Use a PNG or JPEG logo up to 1 MiB')
 try:body=base64.b64decode(raw,validate=True)
 except (ValueError,binascii.Error):require(False,'Invalid image encoding')
 require(0<len(body)<=1048576,'Use a logo up to 1 MiB')
 width=height=0;kind=''
 if body.startswith(b'\x89PNG\r\n\x1a\n'):
  offset=8;ended=False;kind='image/png'
  while offset+12<=len(body):
   n=int.from_bytes(body[offset:offset+4],'big');tag=body[offset+4:offset+8];end=offset+12+n;require(end<=len(body),'Invalid PNG');data=body[offset+8:offset+8+n];crc=int.from_bytes(body[offset+8+n:end],'big');require(zlib.crc32(tag+data)&0xffffffff==crc,'Invalid PNG checksum')
   if offset==8:require(tag==b'IHDR' and n==13,'Invalid PNG header');width,height=struct.unpack('>II',data[:8])
   offset=end
   if tag==b'IEND':ended=True;break
  require(ended and offset==len(body),'Invalid PNG ending')
 elif body.startswith(b'\xff\xd8\xff') and body.endswith(b'\xff\xd9'):
  kind='image/jpeg';offset=2
  while offset+4<=len(body):
   require(body[offset]==255,'Invalid JPEG marker');offset+=1
   while offset<len(body) and body[offset]==255:offset+=1
   require(offset<len(body),'Invalid JPEG');marker=body[offset];offset+=1
   if marker in (0xD8,0xD9) or 0xD0<=marker<=0xD7:continue
   if marker==0xDA:break
   require(offset+2<=len(body),'Invalid JPEG');length=int.from_bytes(body[offset:offset+2],'big');require(length>=2 and offset+length<=len(body),'Invalid JPEG segment')
   if marker in (0xC0,0xC1,0xC2):require(length>=8,'Invalid JPEG dimensions');height,width=struct.unpack('>HH',body[offset+3:offset+7])
   offset+=length
 else:require(False,'Choose a raster PNG or JPEG image. SVG and remote image URLs are not accepted.')
 require(1<=width<=max_dimension and 1<=height<=max_dimension and width*height<=32000000,'Logo dimensions must be 1–'+str(max_dimension)+' pixels per side and at most 32 megapixels')
 return {'mime':kind,'base64':base64.b64encode(body).decode(),'sha256':hashlib.sha256(body).hexdigest()}
def save(store,data):
 current=load(store);require(data.get('version')==version(current),'Dashboard identity changed. Reload before saving.',409)
 require(not(set(data)-{'contestId','version','name','subtitle','primaryColor','sidebarColor','activeIndicatorColor','activeSectionColor','menuHoverColor','rowHoverColor','focusColor','logo','resetLogo','reset'}),'Unexpected branding field')
 if data.get('reset') is True:value=dict(DEFAULT)
 else:
  value={**current}
  for key,limit in [('name',60),('subtitle',100)]:
   text=data.get(key);require(isinstance(text,str) and 1<=len(text.strip())<=limit and not any(ord(c)<32 for c in text),'Use a readable '+key+' of 1–'+str(limit)+' characters');value[key]=text.strip()
  for key in ('primaryColor','sidebarColor','activeIndicatorColor','activeSectionColor','menuHoverColor','rowHoverColor','focusColor'):
   color=data.get(key,current[key]);require(isinstance(color,str) and re.fullmatch('#[0-9a-fA-F]{6}',color),'Use #RRGGBB colors');value[key]=color.lower()
  require(type(data.get('resetLogo',False)) is bool,'Invalid logo reset')
  if data.get('resetLogo'):value['logo']=None
  if data.get('logo'):value['logo']=image(data['logo'])
 with store.db() as db:db.execute("INSERT OR REPLACE INTO settings VALUES('dashboard.branding',?)",(json.dumps(value),))
 return public(store)
def foreground(color):
 rgb=[int(color[i:i+2],16)/255 for i in (1,3,5)];lum=sum(w*(v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4) for w,v in zip((.2126,.7152,.0722),rgb));return '#ffffff' if lum<.179 else '#111827'
def theme(store):
 value=load(store)
 variables={'navy':value['sidebarColor'],'identity-primary':value['primaryColor'],'identity-active-indicator':value['activeIndicatorColor'],'identity-active-section':value['activeSectionColor'],'identity-menu-hover':value['menuHoverColor'],'identity-row-hover':value['rowHoverColor'],'identity-focus':value['focusColor']}
 for name,key in [('primary','primaryColor'),('sidebar','sidebarColor'),('active-section','activeSectionColor'),('menu-hover','menuHoverColor'),('row-hover','rowHoverColor')]:variables['identity-on-'+name]=foreground(value[key])
 return ':root{'+''.join('--'+key+':'+color+';' for key,color in variables.items())+'}'+  '.sidebar,.sidebar nav button,.sidebar-brand span,.sidebar-bottom,.sidebar-bottom p,.nav-group{color:var(--identity-on-sidebar)}'+  '.sidebar nav button.active{border-left-color:var(--identity-active-indicator);background:var(--identity-active-section);color:var(--identity-on-active-section)}'+  '.sidebar nav button:hover{filter:none}.sidebar nav button:hover:not(.active),.section-tabs button:hover:not(.active){background:var(--identity-menu-hover);color:var(--identity-on-menu-hover)}'+  '.primary,.participant-launch,.run-tabs button.active{background:var(--identity-primary);border-color:var(--identity-primary);color:var(--identity-on-primary)}'+  '.section-tabs button.active{background:var(--identity-active-section);border-color:var(--identity-active-section);color:var(--identity-on-active-section)}'+  '.clickable-row:hover,.clickable-row:focus-visible{background:var(--identity-row-hover);color:var(--identity-on-row-hover)}'+  '.clickable-row:hover small,.clickable-row:focus-visible small{color:inherit}'+  'button:focus-visible,a:focus-visible,input:focus-visible,select:focus-visible,textarea:focus-visible,.clickable-row:focus-visible{outline-color:var(--identity-focus)}.sidebar-brand strong{color:inherit}'

def route(handler,path,data=None):
 if path not in ('/api/dashboard-branding','/api/dashboard-branding/logo','/dashboard-theme.css'):return False
 store=handler.app.store
 if data is None:
  if path=='/dashboard-theme.css':handler.send(200,theme(store),'text/css; charset=utf-8');return True
  if path.endswith('/logo'):
   logo=load(store)['logo'];body=base64.b64decode(logo['base64']) if logo else (ROOT/'lcpc/branding/assets/lcpc-logo.png').read_bytes();handler.send(200,body,logo['mime'] if logo else 'image/png');return True
  handler.send(200,public(store));return True
 handler.user('owner');require(path=='/api/dashboard-branding','Not found',404);value=save(store,data);store.audit(handler.actor,'dashboard.identity-updated','success',details={'customLogo':value['customLogo'],'version':value['version']});handler.send(200,value);return True
