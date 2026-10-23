#!/usr/bin/python3 -I
"""Coordinator only: every compilation/execution goes through the installed sandbox."""
from pathlib import Path
import json,subprocess,sys,time

def main():
 root=Path(sys.argv[1]).resolve()
 if not root.is_relative_to(Path('/var/lib/pc2judge')):raise ValueError('Invalid replay directory')
 manifest=json.loads((root/'tasks.json').read_text());done=0
 for task in manifest['tasks']:
  folder=root/task['directory'];mode=task['compiler'];language='python' if mode=='compilepython' else 'cpp'
  if mode not in ('compile17','compile20','compilepython'):raise ValueError('Unsupported compiler')
  memory=int(task['memory']);seconds=int(task['seconds'])
  if not 32<=memory<=1024 or not 1<=seconds<=10:raise ValueError('Invalid limits')
  results=folder/'results';results.mkdir();started=time.monotonic()
  with (results/'compiler.out').open('wb') as out,(results/'compiler.err').open('wb') as err:
   compile=subprocess.run(['/opt/lcpc/bin/'+mode,'source.'+language,'program'],cwd=folder,stdout=out,stderr=err,timeout=50)
  compilation={'exit':compile.returncode,'seconds':round(time.monotonic()-started,4)};rows=[]
  if compile.returncode==246:raise RuntimeError('Sandbox refused compilation')
  for case in task['tests']:
   number=int(case['number']);outpath=results/(str(number)+'.out');errpath=results/(str(number)+'.err');elapsed=0;exitcode=None
   if compile.returncode==0:
    command=['/opt/lcpc/scripts/pc2sandbox.sh',str(memory),str(seconds)]
    command+=['/opt/lcpc/bin/runpython','program'] if language=='python' else ['./program']
    started=time.monotonic()
    with (folder/case['input']).open('rb') as input,outpath.open('wb') as out,errpath.open('wb') as err:
     run=subprocess.run(command,cwd=folder,stdin=input,stdout=out,stderr=err,timeout=seconds+20)
    exitcode=run.returncode;elapsed=round((time.monotonic()-started)*1000,3)
    if exitcode==246:raise RuntimeError('Sandbox refused execution')
   rows.append({'number':number,'executed':compile.returncode==0,'exit':exitcode,'elapsedMS':elapsed})
   done+=1;print(json.dumps({'completed':done,'run':task['label'],'case':number}),flush=True)
  (results/'manifest.json').write_text(json.dumps({'compilation':compilation,'tests':rows,'capturedAt':time.time(),'provenance':'Current-data isolated Linux replay; not the historic contest judgement'}))
 return 0
if __name__=='__main__':sys.exit(main())
