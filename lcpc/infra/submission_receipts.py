"""Bounded persistent retry receipts. Never stores submitted source or raw session tokens."""
import hashlib,json,re,sqlite3,time
from pathlib import Path
from contextlib import contextmanager
class Receipts:
 def __init__(self,state):
  self.path=Path(state)/'participant-activity/submission-receipts.sqlite3';self.path.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
  with self.db() as db:db.execute('CREATE TABLE IF NOT EXISTS receipts(scope TEXT PRIMARY KEY,payload_hash TEXT NOT NULL,created REAL NOT NULL,status INTEGER,body BLOB)')
  self.path.chmod(0o600)
 @contextmanager
 def db(self):
  db=sqlite3.connect(self.path,timeout=5)
  try:
   with db:yield db
  finally:db.close()
 def claim(self,token,key,body):
  if not isinstance(key,str) or not re.fullmatch('[a-f0-9]{32}',key):raise ValueError('Invalid submission request ID')
  scope=hashlib.sha256((token+':'+key).encode()).hexdigest();payload=hashlib.sha256(body).hexdigest()
  with self.db() as db:
   db.execute('BEGIN IMMEDIATE');db.execute('DELETE FROM receipts WHERE created<?',(time.time()-86400,))
   row=db.execute('SELECT payload_hash,status,body FROM receipts WHERE scope=?',(scope,)).fetchone()
   if row:
    if row[0]!=payload:return scope,(409,b'{"error":"This submission request ID belongs to different content. Refresh the submission form."}')
    if row[1] is None:return scope,(409,b'{"error":"Submission delivery is uncertain. Check My submissions before retrying."}')
    return scope,(row[1],bytes(row[2]))
   if db.execute('SELECT count(*) FROM receipts').fetchone()[0]>=10000:return scope,(429,b'{"error":"Submission retry storage is full. Contact the organizer."}')
   db.execute('INSERT INTO receipts(scope,payload_hash,created) VALUES(?,?,?)',(scope,payload,time.time()))
  return scope,None
 def complete(self,scope,status,body):
  # Transport/server failures remain uncertain. Replaying them must not run source twice.
  if 200<=status<500 and len(body)<=65536:
   with self.db() as db:db.execute('UPDATE receipts SET status=?,body=? WHERE scope=?',(status,body,scope))
