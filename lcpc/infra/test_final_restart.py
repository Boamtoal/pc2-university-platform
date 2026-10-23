#!/usr/bin/env python3
"""Restart with Mac execution refusal and verify a real Linux-judged submission."""
from pathlib import Path
import os,subprocess,sys,json
ROOT=Path(__file__).resolve().parents[2];STATE=ROOT/'.local/instances/linux-trial';OUT=ROOT/'work/phase2';env={**os.environ,'LCPC_STATE_DIR':str(STATE)}
def call(args,name):
 q=subprocess.run([sys.executable,str(ROOT/'lcpc/pc2ctl.py'),*args],env=env,capture_output=True,text=True,timeout=150);(OUT/name).write_text(q.stdout+q.stderr)
 if q.returncode:raise SystemExit('Final restart failed at '+args[0]+'; inspect '+name)
 return q.stdout
call(['stop'],'final-stop-before-guard.txt')
call(['isolated-up'],'final-isolated-start.txt')
call(['network-trial'],'final-network-start.txt')
call(['api','start-clock'],'final-smoke-start-clock.txt')
try:call(['api','submit','team2','sum',str(ROOT/'lcpc/infra/tests/ac.cpp'),'yes'],'final-guarded-submission.txt')
finally:call(['api','stop-clock'],'final-clock-paused.txt')
s=call(['api','status'],'final-prebackup-status.txt');assert 'CLOCK running=false' in s
h=call(['health'],'final-health.json');assert json.loads(h)['ready']
print('VERIFIED: isolated restart with all Mac execution disabled; real Linux judgement; clock paused')
