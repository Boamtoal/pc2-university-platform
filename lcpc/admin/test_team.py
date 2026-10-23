"""One private diagnostic participant per contest, outside the official roster."""
import secrets
from pathlib import Path
from core import require

NUMBER=99999
LOGIN='team'+str(NUMBER)
NAME='Organizer Test Team'

def is_test(row):return row.get('login',row.get('team'))==LOGIN
def official(rows):return [r for r in rows if not is_test(r)]
def new_account():return {'number':NUMBER,'login':LOGIN,'name':NAME,'password':secrets.token_urlsafe(24),'enabled':True,'visible':False,'testAccount':True}

def ensure_draft(path):
 from contests import read_json,write_json
 path=Path(path)
 if not path.exists():return
 draft=read_json(path);rows=draft['teams'];found=next((t for t in rows if t['login']==LOGIN),None)
 # Never silently replace an existing participant or its password.
 require(not found or found.get('testAccount') is True,'Reserved test-account number is already in use; resolve the account collision.',409)
 if not found:rows.append(new_account());write_json(path,draft)
 elif found.get('visible') is not False:found['visible']=False;write_json(path,draft)

def info(app):
 row=next((t for t in app.bridge.snapshot().get('teams',[]) if is_test(t)),None)
 return {'available':bool(row),'login':LOGIN,'name':row.get('name',NAME) if row else NAME,'enabled':bool(row and row.get('enabled')),'active':app.manager.data['active']==app.manager.data['selected']}

def credentials(app):
 from contests import read_json
 state=Path(app.manager.selected()['state']);path=state/'admin-dashboard/draft.json'
 require(app.manager.selected()['status']!='archived','Unarchive this contest before retrieving test access.',409)
 require(path.is_file(),'This older contest has no managed test account. Create a new contest to receive one automatically.',409)
 draft=read_json(path);account=next((t for t in draft['teams'] if is_test(t) and t.get('testAccount')),None)
 require(account and info(app)['available'],'The managed test account is unavailable.',409)
 if app.manager.data['active']==app.manager.data['selected']:
  account=cache_credentials(state,app.bridge.call('test-team.credentials'))
 elif (state/'secured').exists():
  cache=state/'admin-dashboard/test-team-access.json'
  require(cache.is_file(),'Activate this contest to retrieve its current test-account password.',409)
  account=read_json(cache)
 return {'contestId':app.manager.data['selected'],'login':LOGIN,'password':account['password'],'name':account['name']}

def cache_credentials(state,value):
 from contests import write_json
 require(value.get('login')==LOGIN and isinstance(value.get('password'),str) and 1<=len(value['password'])<=128,'PC² did not confirm the reserved test account.',409)
 account={k:value[k] for k in ('login','password','name')};write_json(Path(state)/'admin-dashboard/test-team-access.json',account);return account
