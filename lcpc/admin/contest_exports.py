"""Read-only reports and encrypted, consistent offline archives; no source re-execution."""
from pathlib import Path
import copy,csv,hashlib,io,json,os,shutil,sqlite3,subprocess,sys,tarfile,tempfile,uuid,zipfile
from contextlib import closing
from core import ROOT,Error,require,stamp
from contests import write_json
BUNDLED_PYTHON=Path(os.environ.get('LCPC_PDF_PYTHON',sys.executable)).expanduser()
def csv_bytes(columns,rows):
 stream=io.StringIO(newline='');writer=csv.writer(stream);writer.writerow(columns)
 def cell(v):
  if v is None:return ''
  if isinstance(v,(dict,list)):v=json.dumps(v,ensure_ascii=False)
  text=str(v)
  # Spreadsheet formula injection applies even to quoted cells.
  return "'"+text if text.lstrip().startswith(('=','+','-','@','\t','\r')) else text
 for row in rows:writer.writerow([cell(row.get(c)) for c in columns])
 return b'\xef\xbb\xbf'+stream.getvalue().encode('utf-8')
def standings(snapshot):
 value=snapshot.get('standings',{}).get('contestStandings',{});rows=value.get('teamStanding',[])
 if isinstance(rows,dict):rows=[rows]
 return rows

def report_data(manager,row):
 bridge=manager.bridge_for(row);store=manager.store_for(row)
 from problem_difficulty import annotate
 snapshot=annotate(bridge.snapshot(fresh=True),store)
 with manager.app.store.db() as db:
  audit=[];contest_ids={r['id'] for r in manager.data['contests']}
  for record in db.execute('SELECT id,created,actor,event,outcome,details,previous,signature FROM audit ORDER BY id'):
   details=json.loads(record['details']);scope=details.get('contestId')
   if scope is None and details.get('id') in contest_ids:scope=details['id']
   if scope==row['id'] or (scope is None and row['id']==manager.app.store.state.name):audit.append(dict(record))
 return {'format':'LCPC-REPORT-1','exportedAt':stamp(),'contestId':row['id'],'status':row['status'],'snapshot':snapshot,'resources':store.resources()+store.resources(deleted=True),'audit':audit,'notes':['CSV/PDF are reports, not restorable backups.','Standings are the private PC2 standings, ignoring public freeze.','Source files and private judge data are included only in the encrypted full backup.','Older audit entries without a contest ID belong to the original contest.']}

def csv_report(data):
 s=data['snapshot'];from test_team import official,is_test
 sections={
 'contest.csv':(['key','value'],[{'key':k,'value':v} for k,v in s['contest'].items()]+[{'key':'exportedAt','value':data['exportedAt']},{'key':'contestId','value':data['contestId']}]),
 'teams.csv':(['number','login','name','enabled','visible','online'],official(s.get('teams',[]))),
 'problems.csv':(['letter','id','shortName','name','difficulty','difficultyEstimated','timeLimit','memoryLimit','tests','active','judgingMode'],s.get('problems',[])),
 'submissions.csv':(['site','number','team','teamName','problem','problemId','language','elapsedMinutes','verdict','final','preliminary','automaticVerdict','workflowState','accepted','deleted'],official(s.get('runs',[]))),
 'test-submissions.csv':(['site','number','team','teamName','problem','language','verdict','final','automaticVerdict','workflowState'],[r for r in s.get('runs',[]) if is_test(r)]),
 'clarifications.csv':(['site','number','team','problem','question','answer','answered','all','deleted'],s.get('clarifications',[])),
 'languages.csv':(['name','active'],s.get('languages',[])),
 'standings.csv':(['overallRank','rank','teamName','solved','points','problemSummaryInfo'],standings(s)),
 'resources.csv':(['id','problem','kind','language','label','filename','mime','size','sha256','published','deleted','created','version'],data['resources']),
 'audit.csv':(['id','created','actor','event','outcome','details','previous','signature'],data['audit'])}
 out=io.BytesIO()
 with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as archive:
  for name,(cols,rows) in sections.items():archive.writestr(name,csv_bytes(cols,rows))
  archive.writestr('snapshot.json',json.dumps(data,ensure_ascii=False,indent=2));archive.writestr('README.txt','\n'.join(data['notes'])+'\nCSV fields that could be interpreted as spreadsheet formulas are prefixed with an apostrophe.\n')
 return out.getvalue()

def pdf_report(data):
 require(BUNDLED_PYTHON.is_file(),'The configured PDF runtime is missing. CSV export remains available.',503)
 (ROOT/'.local').mkdir(mode=0o700,parents=True,exist_ok=True)
 with tempfile.TemporaryDirectory(prefix='report-',dir=ROOT/'.local') as temp:
  source=Path(temp)/'report.json';target=Path(temp)/'report.pdf'
  from test_team import official
  printable=copy.deepcopy(data)
  for key in ('teams','runs','clarifications'):printable['snapshot'][key]=official(printable['snapshot'].get(key,[]))
  write_json(source,printable)
  result=subprocess.run([str(BUNDLED_PYTHON),str(ROOT/'lcpc/admin/report_pdf.py'),str(source),str(target)],capture_output=True,timeout=90)
  require(result.returncode==0 and target.exists(),'PDF generation failed. Check the server runtime.',503);return target.read_bytes()

def full_backup(manager,row):
 sys.path.insert(0,str(ROOT/'lcpc'));from infra.secure_backup import keypair,run
 from contest_runtime import controller
 state=Path(row['state']);ctl=controller(state)
 require(manager.data['active']!=row['id'] and not any(ctl.pid_for(r) for r in ctl.ROLES),'Contest components must be stopped before backup',409)
 key,cert=keypair(ROOT/'.local');bid=uuid.uuid4().hex;out=manager.base/'backups'/bid;out.mkdir(mode=0o700,parents=True)
 try:
  with tempfile.TemporaryDirectory(prefix='backup-',dir=manager.base) as temp:
   temp=Path(temp);clear=temp/'contest.tar.gz';sql=temp/'sql';sql.mkdir()
   # Central sessions are never restored as authenticated sessions.
   for label,store in [('contest',manager.store_for(row)),('control',manager.app.store)]:
    dest=sqlite3.connect(sql/(label+'.sqlite3'))
    with store.db() as source:source.backup(dest)
    dest.execute('DELETE FROM sessions');dest.execute('DELETE FROM failures');dest.commit();dest.close()
   activity=state/'participant-activity/activity.sqlite3'
   if activity.exists():
    with closing(sqlite3.connect(activity)) as source,closing(sqlite3.connect(sql/'activity.sqlite3')) as dest:
     source.backup(dest);dest.execute('DELETE FROM identities');dest.execute('DELETE FROM clients');dest.commit()
     # Archive a standalone database: do not leave session removal in an omitted WAL.
     dest.execute('PRAGMA journal_mode=DELETE')
   with tarfile.open(clear,'x:gz') as archive:
    def skip(info):
     if info.issym() or info.islnk():raise Error(409,'Symlinks are not allowed in managed backups')
     name=Path(info.name).name
     if name.endswith(('.pid','.lock')) or name in ('dashboard.sqlite3','dashboard.sqlite3-wal','dashboard.sqlite3-shm','activity.sqlite3','activity.sqlite3-wal','activity.sqlite3-shm'):return None
     info.mode=0o700 if info.isdir() else 0o600;return info
    archive.add(state,arcname='contest',filter=skip)
    if activity.exists():archive.add(sql/'activity.sqlite3',arcname='contest/participant-activity/activity.sqlite3')
    archive.add(sql/'contest.sqlite3',arcname='contest/admin-dashboard/dashboard.sqlite3')
    archive.add(sql/'control.sqlite3',arcname='control/dashboard.sqlite3')
    archive.add(manager.app.store.base/'audit.key',arcname='control/audit.key')
    archive.add(manager.registry,arcname='management/registry.json')
    for name in ('admin','admin-ui','infra','src','branding','public-instructions','public-problems'):
     archive.add(ROOT/'lcpc'/name,arcname='operations/lcpc/'+name,filter=skip)
    for name in ('pc2ctl.py','public_standings.py','build-tools.sh'):archive.add(ROOT/'lcpc'/name,arcname='operations/lcpc/'+name)
    document={'format':'LCPC-MANAGED-BACKUP-1','contestId':row['id'],'created':stamp(),'jarSha256':hashlib.sha256((ROOT/'lib/pc2.jar').read_bytes()).hexdigest(),'notes':'Restore into a NEW instance on a compatible PC2 installation. Restore the control database and audit.key together if restoring administrator identity. Sessions were removed. Rebuild Java helpers, review paths/network and rotate restored service credentials. The Linux VM and macOS are not disk-imaged. Keep recipient.key and recipient.crt separately; the archive cannot be decrypted without them.'}
    raw=json.dumps(document,indent=2).encode();info=tarfile.TarInfo('RESTORE.json');info.size=len(raw);info.mode=0o600;archive.addfile(info,io.BytesIO(raw))
   target=out/'contest.tar.gz.cms';run(['cms','-encrypt','-binary','-aes-256-gcm','-in',str(clear),'-out',str(target),'-outform','DER','-recip',str(cert),'-keyopt','rsa_padding_mode:oaep'])
   manifest={'format':'LCPC-MANAGED-BACKUP-1','contestId':row['id'],'created':stamp(),'cipher_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'plaintext_sha256':hashlib.sha256(clear.read_bytes()).hexdigest(),'certificate_sha256':hashlib.sha256(cert.read_bytes()).hexdigest(),'encryption':'AES-256-GCM / RSA-OAEP'};write_json(out/'manifest.json',manifest)
   with zipfile.ZipFile(out/'backup.zip','x',zipfile.ZIP_STORED) as package:package.write(target,target.name);package.write(out/'manifest.json','manifest.json')
  (out/'backup.zip').chmod(0o600);return {'backupId':bid,'filename':row['id']+'-backup.zip','bytes':(out/'backup.zip').stat().st_size}
 except Exception:shutil.rmtree(out,ignore_errors=True);raise
