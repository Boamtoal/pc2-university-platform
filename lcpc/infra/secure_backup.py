"""Authenticated CMS backup using OpenSSL AES-256-GCM and RSA-OAEP.
The decryption key is kept separately, never placed inside contest archives.
"""
from pathlib import Path
import subprocess,shutil,tarfile,hashlib,json,tempfile,datetime,zoneinfo,os
OPENSSL='/opt/homebrew/bin/openssl'
def run(args):
 return subprocess.run([OPENSSL,*args],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
def keypair(base):
 d=base/'backup-keys';d.mkdir(mode=0o700,exist_ok=True)
 key=d/'recipient.key';cert=d/'recipient.crt'
 if not key.exists():
  run(['req','-new','-x509','-newkey','rsa:3072','-nodes','-days','3650','-subj','/CN=LCPC OMU Backup Recipient/','-keyout',str(key),'-out',str(cert)])
  key.chmod(0o600);cert.chmod(0o600)
 if not cert.exists():raise RuntimeError('Backup keypair incomplete')
 return key,cert
def encrypted_backup(ctl):
 ctl.ensure_stopped()
 state=ctl.LOCAL;base=ctl.DEFAULT;key,cert=keypair(base)
 dest=base/'backups';dest.mkdir(exist_ok=True)
 stamp=datetime.datetime.now(zoneinfo.ZoneInfo('Africa/Tripoli')).strftime('%Y%m%d-%H%M%S')
 target=dest/(stamp+'.tar.gz.cms')
 if target.exists():raise RuntimeError('Archive name already exists')
 with tempfile.TemporaryDirectory(prefix='backup-',dir=base) as temp:
  snapshot=Path(temp)/'contest.tar.gz'
  with tarfile.open(snapshot,'x:gz') as tar:
   for name in ['credentials.properties','settings.json','secured','mode.json','preparation.json','TEAM-ACCOUNTS.md','cdp','server','wti','network','admin-dashboard','participant-resources']:
    if (state/name).exists():tar.add(state/name,arcname=name)
   for role in ['api','judge','judge2','admin','team1','board']:
    tar.add(state/role/'pc2v9.ini',arcname=role+'/pc2v9.ini')
   for name in ['lcpc/infra','lcpc/src','lcpc/pc2ctl.py','lcpc/build-tools.sh','lcpc/admin','lcpc/admin-ui','lcpc/public-problems','lcpc/public-instructions','lcpc/public-standings']:
    tar.add(ctl.ROOT/name,arcname='_ops/'+name)
   tar.add(ctl.ROOT/'lcpc/trialctl.py',arcname='_ops/lcpc/trialctl.py')
   if (ctl.ROOT/'lcpc/eventctl.py').exists():tar.add(ctl.ROOT/'lcpc/eventctl.py',arcname='_ops/lcpc/eventctl.py')
   if (ctl.ROOT/'lcpc/branding').exists():tar.add(ctl.ROOT/'lcpc/branding',arcname='_ops/lcpc/branding')
   for p in ctl.ROOT.glob('PC2-LCPC-OMU-*.md'):tar.add(p,arcname='_ops/'+p.name)
  run(['cms','-encrypt','-binary','-aes-256-gcm','-in',str(snapshot),'-out',str(target),'-outform','DER','-recip',str(cert),'-keyopt','rsa_padding_mode:oaep'])
  manifest={'format':'LCPC-CMS-1','encryption':'AES-256-GCM','key_transport':'RSA-OAEP','created':stamp,'cipher_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'plaintext_sha256':hashlib.sha256(snapshot.read_bytes()).hexdigest(),'pc2_sha256':hashlib.sha256((ctl.ROOT/'lib/pc2.jar').read_bytes()).hexdigest()}
  target.chmod(0o600);target.with_suffix(target.suffix+'.json').write_text(json.dumps(manifest,indent=2)+'\n')
 print(target)
 return target

def decrypt_verified(base,archive,dest):
 archive=Path(archive).resolve();manifest=json.loads(archive.with_suffix(archive.suffix+'.json').read_text())
 if hashlib.sha256(archive.read_bytes()).hexdigest()!=manifest['cipher_sha256']:raise RuntimeError('Encrypted archive checksum mismatch')
 key=base/'backup-keys/recipient.key';cert=base/'backup-keys/recipient.crt'
 run(['cms','-decrypt','-binary','-inform','DER','-in',str(archive),'-recip',str(cert),'-inkey',str(key),'-out',str(dest)])
 if hashlib.sha256(dest.read_bytes()).hexdigest()!=manifest['plaintext_sha256']:raise RuntimeError('Decrypted archive mismatch')
 return manifest

def encrypted_restore(ctl,archive):
 with tempfile.TemporaryDirectory(prefix='restore-',dir=ctl.DEFAULT) as d:
  clear=Path(d)/'verified.tar.gz';decrypt_verified(ctl.DEFAULT,archive,clear)
  clear.with_suffix(clear.suffix+'.sha256').write_text(hashlib.sha256(clear.read_bytes()).hexdigest()+' verified.tar.gz\n')
  ctl.restore(clear)
