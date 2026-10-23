#!/usr/bin/env python3
"""Check authenticated encryption, corruption rejection, and restored content."""
from pathlib import Path
import sys,json,tempfile,hashlib,subprocess
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from infra.secure_backup import decrypt_verified
root=Path(__file__).resolve().parents[2];base=root/'.local'
archive=Path((root/'work/phase2/encrypted-backup-path.txt').read_text().strip())
with tempfile.TemporaryDirectory(dir=base) as d:
 clear=Path(d)/'clear.tar.gz';m=decrypt_verified(base,archive,clear)
 assert clear.stat().st_size>0
 print('VERIFIED authenticated decrypt and plaintext SHA-256 match')
 bad=Path(d)/'damaged.cms';data=bytearray(archive.read_bytes());data[len(data)//2]^=1;bad.write_bytes(data)
 manifest=dict(m);manifest['cipher_sha256']=hashlib.sha256(data).hexdigest()
 bad.with_suffix('.cms.json').write_text(json.dumps(manifest))
 try:decrypt_verified(base,bad,Path(d)/'bad.tar.gz')
 except subprocess.CalledProcessError:print('VERIFIED AES-GCM authentication rejects tampered ciphertext even with recomputed outer checksum')
 else:raise AssertionError('Ciphertext authentication did not fail')
restore=Path((root/'work/phase2/encrypted-restore-path.txt').read_text().strip())
for p in ['server/profiles.properties','credentials.properties','settings.json','wti/WebTeamInterface-1.1.jar']:
 assert (restore/p).is_file(),p
print('VERIFIED independent extraction contains contest state, credentials, settings and WTI runtime')
