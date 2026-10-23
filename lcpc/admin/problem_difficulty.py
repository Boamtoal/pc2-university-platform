"""Private organizer ratings, keyed by the stable native problem short name."""
import json
KEY='problem.difficulties'

def load(store):
 with store.db() as db:row=db.execute('SELECT value FROM settings WHERE key=?',(KEY,)).fetchone()
 return json.loads(row[0]) if row else {}

def save(store,values):
 if not isinstance(values,dict):raise ValueError('Problem difficulties must be an object')
 for short,value in values.items():
  if not isinstance(short,str) or not short or not isinstance(value,dict):raise ValueError('Invalid problem difficulty')
  if type(value.get('value')) is not int or not 1<=value['value']<=10000 or type(value.get('estimated')) is not bool:raise ValueError('Use a difficulty of 1–10000 and an estimated flag')
 with store.db() as db:db.execute('INSERT OR REPLACE INTO settings VALUES(?,?)',(KEY,json.dumps(values)))

def annotate(snapshot,store):
 values=load(store)
 return {**snapshot,'problems':[{**p,'difficulty':values.get(p.get('shortName'),{}).get('value'),
  'difficultyEstimated':values.get(p.get('shortName'),{}).get('estimated',False)} for p in snapshot.get('problems',[])]}

def inherit(source,destination,problems):
 keys={p['shortName'] for p in problems};save(destination,{k:v for k,v in load(source).items() if k in keys})
