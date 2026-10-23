#!/usr/bin/env python3
"""Temporary private-tunnel interruption with one bounded queued submission."""
from pathlib import Path
import os,sys,subprocess,time,json,signal
ROOT=Path(__file__).resolve().parents[2]
os.environ['LCPC_STATE_DIR']=str(ROOT/'.local/instances/linux-trial')
sys.path.insert(0,str(ROOT/'lcpc'))
import pc2ctl as ctl
from infra import vm
assert json.loads((ctl.LOCAL/'mode.json').read_text())['mode']=='isolated-trial'
record={'test':'temporary SSH tunnel interruption','timestamp':time.time()}
record['before']=vm.vm_health(ctl);assert record['before']['ready']
pid=int((ctl.DEFAULT/'tunnel.pid').read_text())
command=subprocess.check_output(['ps','-o','command=','-p',str(pid)],text=True)
assert str(ctl.DEFAULT/'judge-ssh.config') in command and '-R' in command
os.kill(pid,signal.SIGTERM)
with (ROOT/'work/phase2/reconnect-submission.txt').open('w') as log:
 p=subprocess.Popen([sys.executable,str(ROOT/'lcpc/pc2ctl.py'),'api','submit','team2','sum',str(ROOT/'lcpc/infra/tests/ac.cpp'),'yes'],env=os.environ,stdout=log,stderr=log)
 try:
  time.sleep(2)
  record['during']=vm.vm_health(ctl)
  assert not record['during']['coordinator_connected']
  q=ctl.api(['status'],capture=True)
  pending=[l for l in q.stdout.splitlines() if l.startswith('RUN ') and 'team2 ' in l and 'final=false' in l]
  record['queued_run_observed']=pending;assert pending
  vm.start_tunnel(ctl)
  start=time.monotonic()
  for _ in range(25):
   h=vm.vm_health(ctl)
   if h['ready']:break
   time.sleep(1)
  record['automatic_judge_reconnected']=h['ready']
  if not h['ready']:vm.guest(['sudo','systemctl','restart','pc2judge.service'])
  rc=p.wait(timeout=90)
  record['submission_exit']=rc;assert rc==0
  record['recovery_seconds']=round(time.monotonic()-start,3)
  record['after']=vm.vm_health(ctl);assert record['after']['ready']
 finally:
  if p.poll() is None:p.terminate();p.wait(timeout=5)
  (ROOT/'work/phase2/reconnect-test.json').write_text(json.dumps(record,indent=2)+'\n')
print('VERIFIED: disconnected submission queued and judged after private tunnel recovery')
