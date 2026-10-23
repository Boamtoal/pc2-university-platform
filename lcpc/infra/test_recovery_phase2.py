#!/usr/bin/env python3
"""Consistent encrypted snapshots, independent restores and clean fresh-template boot."""
from pathlib import Path
import subprocess,os,sys,json,re,time
ROOT=Path(__file__).resolve().parents[2];TRIAL=ROOT/'.local/instances/linux-trial';OUT=ROOT/'work/phase2'
rows=[]
def call(state,args,evidence=None):
 q=subprocess.run([sys.executable,str(ROOT/'lcpc/pc2ctl.py'),*args],env={**os.environ,'LCPC_STATE_DIR':str(state)},capture_output=True,text=True,timeout=150)
 if evidence:(OUT/evidence).write_text(q.stdout+q.stderr)
 if q.returncode:raise RuntimeError('Recovery command failed: '+args[0]+'; inspect private evidence '+str(evidence))
 return q.stdout

def snapshot(s):
 return sorted(l for l in s.splitlines() if l.startswith(('RUN ','STANDING ')))
before=call(TRIAL,['api','stop-clock'],'recovery-before.txt');expected=snapshot(before)
assert sum(l.startswith('RUN ') for l in expected)>=30 and all('final=false' not in l for l in expected)
call(TRIAL,['stop'],'recovery-trial-stop.txt')
archive=call(TRIAL,['backup-encrypted'],'recovery-backup.txt').strip();assert archive.endswith('.cms')
(OUT/'final-encrypted-backup-path.txt').write_text(archive+'\n')
restored=Path(call(TRIAL,['restore-encrypted',archive],'recovery-restore.txt').strip())
call(restored,['start'],'recovery-restored-start.txt')
after=call(restored,['api','audit'],'recovery-restored-audit.txt');assert snapshot(after)==expected;assert 'CLOCK running=false' in after
rows.append({'test':'isolated trial encrypted restore','verified':True,'run_count':sum(l.startswith('RUN ') for l in expected),'independent_directory':str(restored)})
call(restored,['stop'],'recovery-restored-stop.txt')
baseline=(OUT/'encrypted-backup-path.txt').read_text().strip()
restored_base=Path(call(ROOT/'.local',['restore-encrypted',baseline],'baseline-independent-restore.txt').strip())
call(restored_base,['start'],'baseline-restored-start.txt')
audit=call(restored_base,['api','audit'],'baseline-restored-audit.txt');runs=[l for l in audit.splitlines() if l.startswith('RUN ')]
assert len(runs)==6 and all('final=true' in l for l in runs);assert 'CLOCK running=false' in audit
rows.append({'test':'original Phase 1 encrypted restore','verified':True,'run_count':6,'independent_directory':str(restored_base)})
call(restored_base,['stop'],'baseline-restored-stop.txt')
fresh=ROOT/'.local/instances/fresh-isolated-check'
if (fresh/'server/profiles.properties').exists():
 fresh=ROOT/'.local/instances'/('fresh-isolated-'+time.strftime('%Y%m%d-%H%M%S'))
 call(ROOT/'.local',['init-isolated-test',fresh.name],'fresh-template.txt')
call(fresh,['bootstrap'],'fresh-isolated-bootstrap.txt');audit=call(fresh,['api','audit'],'fresh-isolated-audit.txt')
assert not any(l.startswith('RUN ') for l in audit.splitlines());assert len([l for l in audit.splitlines() if l.startswith('STANDING ')])==5
assert 'CLOCK running=false' in audit
rows.append({'test':'new isolated template fresh database','verified':True,'run_count':0,'teams':5})
call(fresh,['stop'],'fresh-isolated-stop.txt')
call(TRIAL,['isolated-up'],'final-isolated-start.txt')
call(TRIAL,['network-trial'],'final-network-start.txt')
health=call(TRIAL,['health'],'final-health.json');assert json.loads(health)['ready']
after=call(TRIAL,['api','status'],'recovery-after-restart.txt');assert snapshot(after)==expected;assert 'CLOCK running=false' in after
rows.append({'test':'isolated restart retains all runs and standings; clock remains paused','verified':True})
(OUT/'recovery-summary.json').write_text(json.dumps(rows,indent=2)+'\n')
print('VERIFIED: encrypted restores preserve trial and original results; fresh template starts with zero runs; paused isolated trial resumed')
