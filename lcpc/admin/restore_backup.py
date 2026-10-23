#!/usr/bin/env python3
"""Restore a managed backup into a NEW offline workspace. Never overwrites a contest."""
from pathlib import Path
import argparse,fcntl,hashlib,json,os,re,shutil,sqlite3,subprocess,sys,tarfile,tempfile,zipfile
sys.path.insert(0,str(Path(__file__).resolve().parent))
from core import ROOT,Error,require,stamp
from contests import write_json
OPENSSL='/opt/homebrew/bin/openssl'

def restore(archive,keydir,dest):
 archive=Path(archive).resolve();keydir=Path(keydir).resolve();dest=Path(dest).resolve();require(not dest.exists(),'Destination already exists; refusing to overwrite',409)
 with tempfile.TemporaryDirectory(prefix='.restore-',dir=dest.parent) as folder:
  folder=Path(folder)
  with zipfile.ZipFile(archive) as package:
   require(set(package.namelist())=={'contest.tar.gz.cms','manifest.json'} and len(package.infolist())==2,'Unexpected backup package')
   require(package.getinfo('manifest.json').file_size<=65536,'Invalid manifest');manifest=json.loads(package.read('manifest.json'));require(manifest.get('format')=='LCPC-MANAGED-BACKUP-1','Unsupported backup format')
   with package.open('contest.tar.gz.cms') as source,(folder/'encrypted.cms').open('wb') as target:shutil.copyfileobj(source,target)
  require(hashlib.sha256((folder/'encrypted.cms').read_bytes()).hexdigest()==manifest['cipher_sha256'],'Encrypted archive integrity check failed',409)
  cert=keydir/'recipient.crt';key=keydir/'recipient.key';require(cert.is_file() and key.is_file(),'Provide recipient.key and recipient.crt')
  require(hashlib.sha256(cert.read_bytes()).hexdigest()==manifest['certificate_sha256'],'This recovery key belongs to a different backup recipient',409)
  result=subprocess.run([OPENSSL,'cms','-decrypt','-binary','-inform','DER','-in',str(folder/'encrypted.cms'),'-recip',str(cert),'-inkey',str(key),'-out',str(folder/'contest.tar.gz')],capture_output=True)
  require(result.returncode==0,'Backup authentication/decryption failed',409);require(hashlib.sha256((folder/'contest.tar.gz').read_bytes()).hexdigest()==manifest['plaintext_sha256'],'Decrypted archive integrity check failed',409)
  extracted=folder/'content';extracted.mkdir(mode=0o700)
  with tarfile.open(folder/'contest.tar.gz') as package:
   names=set()
   for entry in package.getmembers():
    path=Path(entry.name);require(not path.is_absolute() and '..' not in path.parts and (entry.isfile() or entry.isdir()) and entry.name not in names,'Unsafe or duplicate archive entry',409);names.add(entry.name)
   package.extractall(extracted,filter='data')
  source=extracted/'contest';require(source.is_dir(),'Contest state is missing',409)
  # Carry independent owner credentials into a newly bootstrapped control plane.
  # In an existing manager the original identity remains central.
  control=extracted/'control/dashboard.sqlite3'
  if control.exists():
   resource_db=source/'admin-dashboard/dashboard.sqlite3';target=sqlite3.connect(resource_db);identity=sqlite3.connect(control);identity.row_factory=sqlite3.Row
   try:
    target.execute('DELETE FROM users');target.execute('DELETE FROM sessions');target.execute('DELETE FROM failures')
    cols=[r[1] for r in identity.execute('PRAGMA table_info(users)')]
    for row in identity.execute('SELECT * FROM users'):target.execute('INSERT INTO users('+','.join(cols)+') VALUES('+','.join('?' for _ in cols)+')',tuple(row))
    target.commit()
   finally:target.close();identity.close()
  for path in source.rglob('*.pid'):path.unlink()
  for folderpath,dirs,files in os.walk(source):
   os.chmod(folderpath,0o700)
   for file in files:os.chmod(Path(folderpath)/file,0o600)
  recovery=source/'_recovery';recovery.mkdir(mode=0o700)
  for name in ('control','operations','management','RESTORE.json'):
   candidate=extracted/name
   if candidate.exists():shutil.move(str(candidate),str(recovery/name))
  source.rename(dest)
  # Mark pre-runtime drafts distinctly; activation must not mistake them for native state.
  return {'id':dest.name,'state':str(dest),'status':'inactive' if (dest/'secured').exists() else 'draft','created':stamp(),'restoredFrom':manifest['contestId']}

def main():
 os.umask(0o077);parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--archive',required=True);parser.add_argument('--key-dir',required=True);parser.add_argument('--id',required=True);args=parser.parse_args();require(re.fullmatch('[a-z0-9][a-z0-9-]{0,45}',args.id),'Use a lowercase contest ID')
 base=ROOT/'.local/contest-manager';base.mkdir(mode=0o700,parents=True,exist_ok=True);instances=ROOT/'.local/instances';instances.mkdir(mode=0o700,exist_ok=True)
 # Do not race with a running control plane's in-memory catalog.
 processes=subprocess.check_output(['ps','-axo','command='],text=True)
 require(not any(str(ROOT/'lcpc/admin/server.py') in line and '--state' in line and (line.strip().startswith('/') or line.strip().startswith('python')) for line in processes.splitlines()),'Stop the organizer dashboard before registering a restored workspace',409)
 with (base/'restore.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);registry=base/'registry.json';data=json.loads(registry.read_text()) if registry.exists() else {'selected':args.id,'active':None,'contests':[]};require(not any(r['id']==args.id for r in data['contests']),'Contest ID already exists',409)
  row=restore(args.archive,args.key_dir,instances/args.id);data['contests'].append(row);write_json(registry,data);print('Restored offline workspace: '+args.id+'. Review paths and configuration before activation.')
if __name__=='__main__':
 try:main()
 except (Error,OSError,ValueError,zipfile.BadZipFile,tarfile.TarError) as error:raise SystemExit(str(error))
