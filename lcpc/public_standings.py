#!/usr/bin/env python3
"""Read-only public standings process; shares the monitor lock with API tools."""
import os,sys,fcntl,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'lcpc'))
if '--state' in sys.argv:os.environ['LCPC_STATE_DIR']=str(Path(sys.argv[sys.argv.index('--state')+1]).resolve())
if 'LCPC_STATE_DIR' not in os.environ:
 from workspace_state import managed_state
 try:os.environ['LCPC_STATE_DIR']=str(managed_state(active=True))
 except RuntimeError as error:raise SystemExit(str(error))
import pc2ctl as ctl
with (ctl.LOCAL/'api-client.lock').open('a') as lock:
 try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 except BlockingIOError:raise SystemExit('A scoreboard monitor is already active')
 command=ctl.cmd('api');command[command.index('-cp')+1]+=':'+str(ctl.LOCAL/'wti/WebTeamInterface-1.1.jar');command[-2:]=['PublicStandings',str(ctl.LOCAL/'wti/WebContent/WTI-UI/standings/data.json')]
 raise SystemExit(subprocess.run(command,cwd=ctl.LOCAL/'api').returncode)
