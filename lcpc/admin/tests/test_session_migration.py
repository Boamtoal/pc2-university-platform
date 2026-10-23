import sqlite3,sys,tempfile,time,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core import Store,digest,password_hash

class LegacySession(unittest.TestCase):
 def test_existing_local_session_survives_schema_migration_but_cannot_be_used_remotely(self):
  with tempfile.TemporaryDirectory() as directory:
   state=Path(directory);base=state/'admin-dashboard';base.mkdir();token='legacy-fixture-session';now=time.time()
   with sqlite3.connect(base/'dashboard.sqlite3') as db:
    db.execute('CREATE TABLE sessions(token TEXT PRIMARY KEY,username TEXT NOT NULL,csrf TEXT NOT NULL,created REAL NOT NULL,seen REAL NOT NULL)')
    db.execute('INSERT INTO sessions VALUES(?,?,?,?,?)',(digest(token),'owner','fixture-csrf',now,now))
   store=Store(state)
   with store.db() as db:db.execute('INSERT INTO users(username,password,role,must_change) VALUES(?,?,?,0)',('owner',password_hash('fixture-password-migration'),'owner'))
   session=store.session(token,'127.0.0.1','local');self.assertIsNotNone(session);self.assertEqual(session['csrf'],'fixture-csrf');self.assertIsNone(store.session(token,'127.0.0.1','remote'));self.assertIsNone(store.session(token,'192.168.10.25','local'));self.assertIsNotNone(store.session(token,'127.0.0.1','local'))
   for handler in list(store.logger.handlers):handler.close();store.logger.removeHandler(handler)

if __name__=='__main__':unittest.main()
