"""Read only the published, problem-linked resource catalog."""
from pathlib import Path
import hashlib,json,re
from urllib.parse import quote

def catalog(state):
 path=Path(state)/'participant-resources/catalog.json'
 return json.loads(path.read_text()) if path.exists() else None

def file_response(state,path,download=False):
 data=catalog(state)
 if data is None:return None
 files=[r for p in data['problems'] for r in p['resources']]+data.get('booklets',[])
 match=re.fullmatch(r'/problems/files/([a-f0-9]{32})',path)
 resource=None
 if match:resource=next((r for r in files if r['id']==match[1]),None)
 elif path=='/problems/booklet.pdf':resource=next((r for r in data.get('booklets',[]) if r['language']=='en'),None)
 else:
  legacy=re.fullmatch(r'/problems/([A-Z]{1,3})\.pdf',path)
  if legacy:
   problem=next((p for p in data['problems'] if p['letter']==legacy[1]),None)
   if problem:resource=next((r for r in problem['resources'] if r['kind']=='statement' and r['language']=='en'),None)
 if not resource:return (404,b'{"error":"published resource not found"}','application/json',{})
 if not re.fullmatch('[a-f0-9]{32}',resource.get('id','')):return (404,b'{}','application/json',{})
 file=Path(state)/'admin-dashboard/uploads'/resource['id']
 if not file.is_file() or file.is_symlink():return (404,b'{}','application/json',{})
 body=file.read_bytes()
 if hashlib.sha256(body).hexdigest()!=resource['sha256']:return (503,b'{"error":"resource integrity check failed"}','application/json',{})
 disposition='attachment' if download or resource['kind']=='helper' else 'inline'
 filename=quote(resource['filename'],safe='')
 return (200,body,resource['mime'],{'Content-Disposition':disposition+'; filename="resource'+Path(resource['filename']).suffix.lower()+'"; filename*=UTF-8\'\''+filename})
