"""Resolve managed contest paths without recreating a retired legacy workspace."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]

def managed_state(*, active=False, root=ROOT):
 root=Path(root).resolve();registry=root/'.local/contest-manager/registry.json'
 if not registry.exists():
  legacy=root/'.local/instances/lcpc-omu-preparation'
  if legacy.is_dir():return legacy
  raise RuntimeError('No managed contest is configured. Open the organizer dashboard or specify --state.')
 data=json.loads(registry.read_text());cid=data.get('active') if active else data.get('selected')
 if not cid:raise RuntimeError('No contest is active. Complete and activate the draft from the organizer dashboard first.')
 row=next((r for r in data['contests'] if r['id']==cid),None)
 if row is None:raise RuntimeError('The managed contest registry has no matching workspace.')
 state=Path(row['state']).resolve()
 if state.parent != root/'.local/instances' or state.name!=cid or not state.is_dir():
  raise RuntimeError('The managed contest workspace is missing or invalid. Specify a valid --state.')
 return state
