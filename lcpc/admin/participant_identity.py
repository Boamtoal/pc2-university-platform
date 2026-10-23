"""Contest-scoped participant identity. Only an allowlisted public manifest reaches the LAN."""
import base64,copy,hashlib,json,re,uuid
from pathlib import Path
from core import ROOT,require
from dashboard_branding import image
from submission_review import query
import participant_theme
SLOTS={'pc2':('PC²','pc2-logo.png'),'icpc':('ICPC','icpc-logo.png'),'university':('Omar Al-Mukhtar University','omu-logo.png'),'contest':('LCPC OMU','lcpc-logo.png')}
FIELDS={'name':(80,True),'universityName':(160,True),'universityNameAr':(160,False),'contestLabel':(160,True),'instructionsTitle':(120,True),'instructionsTitleAr':(120,False),'instructionsSubtitle':(200,True),'instructionsSubtitleAr':(200,False),'footerText':(200,False),'footerTextAr':(200,False)}
DEFAULT={'name':'LCPC OMU','universityName':'Omar Al-Mukhtar University','universityNameAr':'جامعة عمر المختار','contestLabel':'Practice Contest','instructionsTitle':'Participant Instructions','instructionsTitleAr':'تعليمات المشاركة','instructionsSubtitle':'Omar Al-Mukhtar University · Programming Contests','instructionsSubtitleAr':'جامعة عمر المختار · المسابقات البرمجية','footerText':'','footerTextAr':'','colors':dict(participant_theme.DEFAULT),'logos':[{ 'id':key,'label':label,'header':True,'resources':key in ('university','contest'),'scoreboard':key in ('university','contest'),'image':None} for key,(label,_) in SLOTS.items()]}
def version(value):return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
def load(store):
 with store.db() as db:row=db.execute("SELECT value FROM settings WHERE key='participant.identity'").fetchone()
 value=json.loads(row[0]) if row else copy.deepcopy(DEFAULT)
 value['colors']={**participant_theme.DEFAULT,**value.get('colors',{})};return value
def logo_bytes(value,slot):
 logo=next(v for v in value['logos'] if v['id']==slot)
 if logo['image']:return base64.b64decode(logo['image']['base64']),logo['image']['mime']
 return (ROOT/'lcpc/branding/assets'/SLOTS[slot][1]).read_bytes(),'image/png'
def manifest(value):
 result={k:value[k] for k in FIELDS};result.update(schema=1,version=version(value),colors=value['colors'],logos=[])
 for logo in value['logos']:
  body,mime=logo_bytes(value,logo['id']);name=hashlib.sha256(body).hexdigest()+('.png' if mime=='image/png' else '.jpg')
  result['logos'].append({k:logo[k] for k in ('id','label','header','resources','scoreboard')}|{'custom':bool(logo['image']),'url':'/assets/lcpc-branding/identity/'+name})
 return result

def atomic(path,body):
 path.parent.mkdir(parents=True,exist_ok=True);temporary=path.with_name('.'+path.name+'.'+uuid.uuid4().hex);temporary.write_bytes(body);temporary.chmod(0o600);temporary.replace(path)
def publish(store,value=None):
 value=load(store) if value is None else value;public=manifest(value);base=store.state/'participant-resources';web=store.state/'wti/WebContent/WTI-UI'
 # Images are immutable and written before either manifest. No original image is overwritten.
 for logo in public['logos']:
  body,_=logo_bytes(value,logo['id']);name=Path(logo['url']).name;atomic(base/'identity-assets'/name,body)
  if (web/'index.html').exists():atomic(web/'assets/lcpc-branding/identity'/name,body)
 atomic(base/'participant-theme.css',participant_theme.css(value['colors']).encode())
 if (web/'index.html').exists():atomic(web/'assets/lcpc-branding/participant-theme-values.css',participant_theme.css(value['colors']).encode())
 encoded=json.dumps(public,ensure_ascii=False).encode();atomic(base/'identity.json',encoded)
 if (web/'index.html').exists():atomic(web/'assets/lcpc-branding/participant-identity.json',encoded)
 return public

def public(store,cid):
 value=load(store);out={k:value[k] for k in FIELDS};v=version(value);out.update(version=v,contestId=cid,colors=value['colors'],logos=[])
 for logo in value['logos']:
  out['logos'].append({k:logo[k] for k in ('id','label','header','resources','scoreboard')}|{'custom':bool(logo['image']),'defaultUrl':'/api/participant-identity/logo?contestId='+cid+'&slot='+logo['id']+'&default=1','url':'/api/participant-identity/logo?contestId='+cid+'&slot='+logo['id']+'&v='+v})
 return out

def validate(current,data):
 require(data.get('version')==version(current),'Participant identity changed. Reload before saving.',409)
 require(not(set(data)-set(FIELDS)-{'contestId','version','logos','colors','reset'}),'Unexpected identity field')
 if data.get('reset') is True:return copy.deepcopy(DEFAULT)
 value=copy.deepcopy(current)
 value['colors']=participant_theme.validate(data.get('colors',current['colors']))
 for key,(limit,required) in FIELDS.items():
  text=data.get(key,'');require(isinstance(text,str) and (not required or bool(text.strip())) and len(text.strip())<=limit and not any(ord(c)<32 for c in text),'Use readable text for '+key+' (up to '+str(limit)+' characters)');value[key]=text.strip()
 logos=data.get('logos');require(isinstance(logos,list) and len(logos)==4,'Configure the four logo slots')
 require(all(isinstance(v,dict) for v in logos),'Invalid logo configuration');require(all(isinstance(v.get('id'),str) for v in logos),'Invalid logo slot');require({v.get('id') for v in logos}==set(SLOTS),'Use each logo slot exactly once')
 for logo in logos:
  require(not(set(logo)-{'id','label','header','resources','scoreboard','upload','resetImage'}),'Unexpected logo field')
  target=next(v for v in value['logos'] if v['id']==logo['id']);label=logo.get('label');require(isinstance(label,str) and 1<=len(label.strip())<=160 and not any(ord(c)<32 for c in label),'Use a readable logo name');target['label']=label.strip()
  for location in ('header','resources','scoreboard'):
   require(type(logo.get(location)) is bool,'Choose where each logo appears');target[location]=logo[location]
  require(type(logo.get('resetImage',False)) is bool,'Invalid logo reset')
  if logo.get('resetImage'):target['image']=None
  if logo.get('upload'):
   require(not logo.get('resetImage'),'Choose an upload or restore the default image');target['image']=image(logo['upload'],max_dimension=8192)
 value['logos']=[next(v for v in value['logos'] if v['id']==logo['id']) for logo in logos]
 return value

def save(store,data):
 current=load(store);value=validate(current,data)
 # Validate all text/images first; a later invalid logo can never partially save earlier fields.
 with store.db() as db:
  db.execute("INSERT OR REPLACE INTO settings VALUES('participant.identity',?)",(json.dumps(value,ensure_ascii=False),))
  try:publish(store,value)
  except Exception:
   publish(store,current);raise
 return value

def inherit(source,destination):
 value=load(source)
 with destination.db() as db:db.execute("INSERT OR REPLACE INTO settings VALUES('participant.identity',?)",(json.dumps(value,ensure_ascii=False),))
 publish(destination,value)

def route(handler,path,data=None):
 if path not in ('/api/participant-identity','/api/participant-identity/logo'):return False
 handler.user('owner');app=handler.app;cid=app.manager.data['selected'];store=app.resources
 if data is None:
  values=query(handler,required=True)
  if path.endswith('/logo'):
   slots=values.get('slot',[]);require(len(slots)==1 and slots[0] in SLOTS,'Choose a logo');body,mime=logo_bytes(DEFAULT if values.get('default')==['1'] else load(store),slots[0]);handler.send(200,body,mime);return True
  handler.send(200,public(store,cid)|{'readOnly':app.manager.selected()['status']=='archived'});return True
 require(path=='/api/participant-identity','Not found',404);app.manager.guard(data);app.manager.allow_native_mutation();value=save(store,data)
 app.store.audit(handler.actor,'participant.identity-updated','success',details={'contestId':cid,'version':version(value),'customLogos':[v['id'] for v in value['logos'] if v['image']]})
 handler.send(200,public(store,cid));return True
