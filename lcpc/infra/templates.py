"""Fresh isolated technical contests and inactive event drafts; never copies run DBs."""
from pathlib import Path
import json,secrets,re
LANGUAGES="""languages:
  - name: 'GNU C++17 (Isolated Linux ARM64)'
    active: true
    compilerCmd: '/opt/lcpc/bin/compile17 {:mainfile} {:basename}'
    exemask: '{:basename}'
    execCmd: './{:basename}'
  - name: 'GNU C++20 (Isolated Linux ARM64)'
    active: true
    compilerCmd: '/opt/lcpc/bin/compile20 {:mainfile} {:basename}'
    exemask: '{:basename}'
    execCmd: './{:basename}'
  - name: 'Python 3.12 (Isolated Linux ARM64)'
    active: true
    compilerCmd: '/opt/lcpc/bin/compilepython {:mainfile} {:basename}.lcpcpy'
    exemask: '{:basename}.lcpcpy'
    execCmd: '/opt/lcpc/bin/runpython {:basename}.lcpcpy'
"""
REJECT='Compilation Error|CE\nRun-time Error|RTE\nTime Limit Exceeded|TLE\nMemory Limit Exceeded|MLE\nWrong Answer|WA\nExcessive Output|EE\nOutput Format Error|EFE\nOther - Contact Staff|CS\n'
def isolated_test(ctl,slug):
 ctl.init_test(slug);dest=ctl.DEFAULT/'instances'/slug
 c=dest/'cdp/config/contest.yaml';text=c.read_text()
 text=re.sub(r'languages:\n.*?(?=accounts:)',LANGUAGES,text,flags=re.S)
 text=re.sub(r'^name: .*$',"name: 'LCPC OMU - ISOLATED INFRASTRUCTURE TEST'",text,count=1,flags=re.M)
 text=text.replace('count: 2\n  - account: JUDGE','count: 5\n  - account: JUDGE')
 c.write_text(text)
 creds=dest/'credentials.properties';p=dict(l.split('=',1) for l in creds.read_text().splitlines())
 rows=(dest/'cdp/config/accounts_load.tsv').read_text()
 for n in range(3,6):
  user='team'+str(n);p[user]=secrets.token_urlsafe(24);rows+='1\t'+user+'\tOMU Technical Test '+str(n)+'\t'+p[user]+'\ttrue\ttrue\n'
 creds.write_text(''.join(k+'='+v+'\n' for k,v in p.items()))
 (dest/'cdp/reject.ini').write_text(REJECT)
 for problem in ['sum','maximum']:
  f=dest/'cdp/config'/problem/'problem.yaml';s=f.read_text()
  if 'sandbox-type:' not in s:s='sandbox-type: PC2_INTERNAL_SANDBOX\n'+s
  if 'memory:' not in s:s=s.replace('limits:\n','limits:\n  memory: 128\n',1)
  f.write_text(s)
 (dest/'mode.json').write_text(json.dumps({'mode':'isolated-trial','purpose':'technical acceptance only; no official contest'})+'\n')
 # Browser OS identifies the client, not the Linux compiler platform.
 ini=dest/'wti/pc2v9.ini';ini.write_text(ini.read_text()+'allowedOSName2=Windows\nallowedOSName3=Linux\n')
 print('Fresh isolated test configured; database absent, clock not started')

def event_draft(ctl,slug):
 if not re.fullmatch('[a-z0-9][a-z0-9-]{0,45}',slug):raise RuntimeError('Use a lowercase slug')
 dest=ctl.DEFAULT/'event-drafts'/slug;dest.mkdir(parents=True,exist_ok=False)
 (dest/'NOT_READY.json').write_text(json.dumps({'status':'DRAFT — NOT RUNNABLE','organizer_decisions_needed':['title','problems and judge data','teams and names','date and duration','penalty and ranking rules','network IP and CIDR'],'technical_profile':'Linux ARM64 C++17/C++20; isolated compile/run; private Mac backend; HTTPS proxy'},indent=2)+'\n')
 (dest/'languages.yaml').write_text(LANGUAGES)
 (dest/'reject.ini').write_text(REJECT)
 (dest/'problem-limits.template.yaml').write_text('# Choose tested limits for each approved problem. Do not load this draft directly.\nsandbox-type: PC2_INTERNAL_SANDBOX\nlimits:\n  timeout: <1..10 seconds>\n  memory: <32..1024 MiB>\n')
 (dest/'README.md').write_text('مسودة غير قابلة للتشغيل. لا تحتوي حسابات أو كلمات مرور أو مسائل أو إرسالات.\nبعد اعتماد بيانات المنظم، تُنشأ قاعدة جديدة وتُختبر على نسخة تدريب مستقلة. لا تنقل server/ أو إرسالات الاختبار إلى المسابقة الرسمية.\n')
 print(dest)
