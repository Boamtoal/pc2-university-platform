"""Version-checked hooks into the extracted WTI authentication service.

Keep vendor ZIP/JAR files intact. The small hooks delegate storage and restore
to the readable session.js module. Refuse an unfamiliar bundle before writing.
"""
from pathlib import Path

MARKER='/* LCPC tab session v1 */'

def install(web):
 path=Path(web)/'main.js'
 text=path.read_text()
 if MARKER in text:return
 old_root=r'''let NW=(()=>{class t{constructor(e){this._httpClient=e,this.configLoaded=!1}ngOnInit(){this._httpClient.get("assets/appconfig.json").subscribe(e=>{this.configLoaded=!0,e&&Object.keys(e).forEach(i=>at[i]=e[i])},e=>{console.log("could not find appconfig.json in assets directory. using default values!"),this.configLoaded=!0})}static{this.\u0275fac=function(i){return new(i||t)(m(tr))}}'''
 new_root=r'''let NW=(()=>{class t{constructor(e,i,r,o){this._httpClient=e,this._lcpcAuth=i,this._lcpcSocket=r,this._lcpcContest=o,this.configLoaded=!1}ngOnInit(){const ready=()=>globalThis.LCPCSession.startup(this._lcpcAuth,this._lcpcSocket,this._lcpcContest).finally(()=>{this.configLoaded=!0});this._httpClient.get("assets/appconfig.json").subscribe(e=>{e&&Object.keys(e).forEach(i=>at[i]=e[i]),ready()},()=>{at.baseUrl=location.origin+"/api",at.websocketUrl=(location.protocol==="https:"?"wss://":"ws://")+location.host+"/websocket/WTISocket",ready()})}static{this.\u0275fac=function(i){return new(i||t)(m(tr),m(sn),m(us),m(an))}}'''
 replacements=[
  ('this._teamsService=e,this._router=i,this._defaultRoute="/runs"}',
   'this._teamsService=e,this._router=i,this._defaultRoute="/runs",globalThis.LCPCSession.restore(this)}'),
  ('completeLogin(e,i){this._token=e,this._userName=i,this._router.navigateByUrl',
   'completeLogin(e,i){this._token=e,this._userName=i,globalThis.LCPCSession.save(e,i),this._router.navigateByUrl'),
  ('completeLogout(){this._token=void 0,this._userName=void 0,this._router.navigateByUrl',
   'completeLogout(){this._token=void 0,this._userName=void 0,globalThis.LCPCSession.clear(),this._router.navigateByUrl'),
  (old_root,new_root),
 ]
 for before,after in replacements:
  if text.count(before)!=1:raise RuntimeError('WTI session hook does not match this bundle; no bundle changes written')
  text=text.replace(before,after,1)
 backup=path.with_name('main.vendor.js.original')
 if not backup.exists():backup.write_text(path.read_text())
 path.write_text(MARKER+'\n'+text)
