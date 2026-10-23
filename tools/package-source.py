#!/usr/bin/env python3
"""Stage a reviewed source-only release; never copy an installed contest wholesale."""
from pathlib import Path
import argparse,hashlib,json,re,shutil
ROOT=Path(__file__).resolve().parents[1]
TOP={'README.md','LICENSE','NOTICE.md','CHANGELOG.md','CONTRIBUTING.md','SECURITY.md','.gitignore'}
SCOPES={'docs':{'.md','.json'},'tools':{'.py'},'.github':{'.md','.yml','.yaml'},'lcpc/admin':{'.py','.md','.txt','.java','.cjs'},'lcpc/admin-ui':{'.js','.css','.html'},'lcpc/branding':{'.js','.css','.md','.png','.cjs','.json'},'lcpc/infra':{'.py','.sh','.yaml','.cpp','.service'},'lcpc/src':{'.java'},'lcpc/public-instructions':{'.html'},'lcpc/public-problems':{'.html'},'lcpc/public-standings':{'.js','.css','.html'},'lcpc/templates/practice':{'.yaml','.md','.in','.ans'}}
ENTRY={'lcpc/admin/timezones.json','lcpc/PROJECT_VERSION','lcpc/PARTICIPANT-RESOURCES.md','lcpc/build-tools.sh','lcpc/pc2ctl.py','lcpc/trialctl.py','lcpc/lan_info.py','lcpc/public_standings.py','lcpc/runtime_paths.py','lcpc/workspace_state.py','lcpc/infra/linux/compile17','lcpc/infra/linux/compile20','lcpc/infra/linux/compilepython','lcpc/infra/linux/runpython'}
EXCLUDE={'lcpc/src/EventProblemImport.java','lcpc/src/SixProblemAudit.java','lcpc/infra/deploy_activity.py','lcpc/infra/finalize_phase2.py','lcpc/infra/validate_six_wti.py','lcpc/infra/test_python_profile.py'}
BAD_PARTS={'.local','.git','.venv','__pycache__','node_modules','uploads','learning-reports','solutions','logs','build','output','work','tmp'}
PATTERNS=[(re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH |ENCRYPTED )?PRIVATE KEY-----'),'private key'),(re.compile(rb'\bgh[pousr]_[A-Za-z0-9]{24,}\b'),'GitHub token'),(re.compile(rb'github_pat_[A-Za-z0-9_]{30,}'),'GitHub token'),(re.compile(rb'/Us'+rb'ers/[^/\s\x00"\']+/'),'personal home path'),(re.compile(rb'10\.199\.178\.'),'event network address'),(re.compile(rb'\b169\.254\.30\.8\b'),'event device address')]
def allowed(path):
 key=path.as_posix()
 if key in EXCLUDE or any(p in BAD_PARTS for p in path.parts):return False
 if key in TOP|ENTRY:return True
 return any(key.startswith(prefix+'/') and path.suffix in suffixes for prefix,suffixes in SCOPES.items())
def inspect(path,data):
 errors=[]
 if len(data)>4*1024*1024:errors.append('unexpected large source file')
 if path.suffix!='.png':
  for regex,label in PATTERNS:
   if regex.search(data):errors.append(label)
 return errors
def package(root,output):
 root=Path(root).resolve();output=Path(output).resolve()
 if output.exists():raise ValueError('Output must be a new directory; refusing to overwrite')
 # Never recurse into an existing repository or runtime; selection is explicit.
 files=[p for p in root.rglob('*') if p.is_file() and allowed(p.relative_to(root))]
 entries=[]
 for file in sorted(files):
  relative=file.relative_to(root)
  if file.is_symlink():raise ValueError('Symlink rejected: '+str(relative))
  errors=inspect(relative,file.read_bytes())
  if errors:raise ValueError(str(relative)+': '+', '.join(errors))
  entries.append({'path':relative.as_posix(),'bytes':file.stat().st_size,'sha256':hashlib.sha256(file.read_bytes()).hexdigest()})
 required=TOP|{'lcpc/admin/timezones.json','lcpc/admin/server.py','lcpc/admin-ui/guide.js','lcpc/admin-ui/guide-content.js','lcpc/public-problems/index.html','lcpc/templates/practice/config/sum/data/secret/01.in','lcpc/templates/practice/config/sum/data/secret/01.ans'}
 missing=required-{x['path'] for x in entries}
 if missing:raise ValueError('Required source missing: '+', '.join(sorted(missing)))
 output.mkdir(parents=True)
 for entry in entries:
  source=root/entry['path'];dest=output/entry['path'];dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,dest)
  if source.stat().st_mode&0o111:dest.chmod(0o755)
 manifest={'version':'1.0.0','kind':'source-only','privateStateIncluded':False,'files':entries,'notes':['Explicit source allowlist; no native vendor binaries or real contest data.','Public synthetic rehearsal inputs/answers are included deliberately.','Review future changes; pattern scanning is not a universal secret detector.']}
 (output/'SOURCE-MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
 return manifest
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
 try:manifest=package(ROOT,args.output)
 except ValueError as e:raise SystemExit(str(e))
 print(json.dumps({'output':str(args.output),'files':len(manifest['files']),'bytes':sum(x['bytes'] for x in manifest['files']),'privateStateIncluded':False}))
