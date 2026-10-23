"""Version checked replacement of vendor run alerts; retain vendor fallback if our module fails."""
from pathlib import Path
MARKER='/* LCPC global result notifications v1 */'
BEFORE='incomingRun(e){this.enableRunsNotifications&&this._dialogService.open(Z8,{data:{id:e}})}'
AFTER='incomingRun(e){if(globalThis.LCPCResultNotifications)globalThis.LCPCResultNotifications.wake(e);else this.enableRunsNotifications&&this._dialogService.open(Z8,{data:{id:e}})}'

def install(web):
 path=Path(web)/'main.js';text=path.read_text()
 if MARKER in text:
  if text.count(AFTER)!=1:raise RuntimeError('Unexpected participant result notification hook')
  return
 if text.count(BEFORE)!=1:raise RuntimeError('Unsupported WTI result notification bundle; no bundle changes written')
 backup=path.with_name('main.before-result-notifications.js.original')
 if not backup.exists():backup.write_text(text)
 path.write_text(MARKER+'\n'+text.replace(BEFORE,AFTER,1))
