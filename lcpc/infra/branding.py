"""Deploy standalone branding assets into an extracted WTI; vendor ZIP/JAR unchanged."""
from pathlib import Path
import shutil,re,hashlib
ROOT=Path(__file__).resolve().parents[2]
def install(state):
 source=ROOT/'lcpc/branding'
 web=Path(state)/'wti/WebContent/WTI-UI'
 if not (web/'index.html').is_file():raise RuntimeError('WTI UI missing')
 target=web/'assets/lcpc-branding';target.mkdir(parents=True,exist_ok=True)
 for f in (source/'assets').glob('*.png'):shutil.copyfile(f,target/f.name)
 for f in ['standings.css','scoreboard-model.js','standings.js','run-results.js','resources.css','resources.js','session.js','header.css','header.js','problem-resources.js','activity.js']:shutil.copyfile(source/f,target/f)
 for folder,route in [('public-problems','problems'),('public-instructions','instructions')]:
  if route=='problems' and (Path(state)/'admin-dashboard/draft.json').exists():
   destination=Path(state)/'participant-resources'/route;destination.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/'lcpc'/folder/'index.html',destination/'index.html')
  else:shutil.copytree(ROOT/'lcpc'/folder,Path(state)/'participant-resources'/route,dirs_exist_ok=True)
  if (web/route).exists():shutil.rmtree(web/route)
 install_scoreboard(state)
 from infra.frontend_session import install as install_session
 install_session(web)
 index=web/'index.html';text=index.read_text()
 if 'assets/lcpc-branding/standings.css' not in text:text=text.replace('</head>','<link rel="stylesheet" href="assets/lcpc-branding/standings.css?v=2"></head>')
 if 'assets/lcpc-branding/standings.js' not in text:text=text.replace('</body>','<script src="assets/lcpc-branding/standings.js?v=2" defer></script></body>')
 for version in ['1','2','3','4']:
  for asset in ['standings.css','standings.js','scoreboard-model.js','run-results.js']:text=text.replace(asset+'?v='+version,asset+'?v=5')
 if 'assets/lcpc-branding/scoreboard-model.js' not in text:text=text.replace('<script src="assets/lcpc-branding/standings.js','<script src="assets/lcpc-branding/scoreboard-model.js?v=5" defer></script><script src="assets/lcpc-branding/standings.js')
 if 'assets/lcpc-branding/run-results.js' not in text:text=text.replace('</body>','<script src="assets/lcpc-branding/run-results.js?v=5" defer></script></body>')
 for asset in ['standings.css','run-results.js']:text=text.replace(asset+'?v=5',asset+'?v=6')
 if 'assets/lcpc-branding/resources.css' not in text:text=text.replace('</head>','<link rel="stylesheet" href="assets/lcpc-branding/resources.css?v=1"></head>')
 if 'assets/lcpc-branding/resources.js' not in text:text=text.replace('</body>','<script src="assets/lcpc-branding/resources.js?v=1" defer></script></body>')
 for version in ['1','2','3','4']:text=text.replace('resources.js?v='+version,'resources.js?v=5')
 text=text.replace('resources.css?v=1','resources.css?v=2')
 if 'assets/lcpc-branding/session.js' not in text:text=text.replace('<script src="runtime.js"','<script src="assets/lcpc-branding/session.js?v=1"></script><script src="runtime.js"')
 text=text.replace('src="main.js"','src="main.js?v=lcpc-session-1"')
 if 'assets/lcpc-branding/header.css' not in text:text=text.replace('</head>','<link rel="stylesheet" href="assets/lcpc-branding/header.css?v=1"></head>')
 for version in ['1','2','3']:text=text.replace('header.css?v='+version,'header.css?v=4')
 if 'assets/lcpc-branding/header.js' not in text:text=text.replace('</body>','<script src="assets/lcpc-branding/header.js?v=1" defer></script></body>')
 for version in ['1','2']:text=text.replace('header.js?v='+version,'header.js?v=3')
 if 'assets/lcpc-branding/activity.js' not in text:text=text.replace('<script src="runtime.js"','<script src="assets/lcpc-branding/activity.js?v=1"></script><script src="runtime.js"')
 index.write_text(text)
 install_result_notifications(state,hook=True)
 install_participant_ui(state)
 print('Standings branding installed')

def install_activity(state):
 """Targeted instrumentation install; preserves custom pages, PDFs and vendor bundles."""
 state=Path(state);web=state/'wti/WebContent/WTI-UI';target=web/'assets/lcpc-branding';target.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/'lcpc/branding/activity.js',target/'activity.js')
 index=web/'index.html';text=index.read_text()
 if 'assets/lcpc-branding/activity.js' not in text:
  if '<script src="runtime.js"' not in text:raise RuntimeError('Unexpected WTI script layout')
  text=text.replace('<script src="runtime.js"','<script src="assets/lcpc-branding/activity.js?v=1"></script><script src="runtime.js"',1)
 index.write_text(text)
 for route in ('problems','instructions'):
  path=state/'participant-resources'/route/'index.html'
  if path.exists():
   text=path.read_text()
   if '/assets/lcpc-branding/activity.js' not in text:
    if '</body>' not in text:raise RuntimeError('Unexpected standalone page layout')
    path.write_text(text.replace('</body>','<script src="/assets/lcpc-branding/activity.js?v=1" defer></script></body>'))


def install_scoreboard(state):
 """Install the public display shell without overwriting released data.json."""
 web=Path(state)/'wti/WebContent/WTI-UI';target=web/'standings';target.mkdir(parents=True,exist_ok=True)
 for name in ('index.html','scoreboards.js','scoreboards.css'):
  shutil.copyfile(ROOT/'lcpc/public-standings'/name,target/name)
 assets=web/'assets/lcpc-branding';assets.mkdir(parents=True,exist_ok=True)
 for name in ('scoreboard-model.js','standings.css'):
  shutil.copyfile(ROOT/'lcpc/branding'/name,assets/name)


def install_participant_ui(state):
 """Apply presentation assets while retaining sessions, bundles and custom resource content."""
 state=Path(state);web=state/'wti/WebContent/WTI-UI';index=web/'index.html'
 if not index.is_file():raise RuntimeError('WTI UI missing')
 assets=web/'assets/lcpc-branding';assets.mkdir(parents=True,exist_ok=True)
 for name in ('participant-ui.css','participant-ui.js','resource-ui.css','resource-pages.css','session.js','activity.js','download-feedback.js','download-feedback.css'):
  shutil.copyfile(ROOT/'lcpc/branding'/name,assets/name)
 text=index.read_text()
 for closing,tag,marker in [
  ('</head>','<link rel="stylesheet" href="assets/lcpc-branding/participant-ui.css?v=1">','assets/lcpc-branding/participant-ui.css'),
  ('</body>','<script src="assets/lcpc-branding/participant-ui.js?v=1" defer></script>','assets/lcpc-branding/participant-ui.js')]:
  if marker not in text:
   if closing not in text:raise RuntimeError('Unexpected WTI page layout')
   text=text.replace(closing,tag+closing,1)
 index.write_text(text)
 for route in ('instructions','problems'):
  style_resource_page(state/'participant-resources'/route/'index.html',route)
 file=web/'standings/index.html'
 if file.is_file():
  # The audience display owns its layout; generic resource-page rules distort its header/table.
  text=file.read_text()
  text=re.sub(r'<link\b[^>]*href=[\"\']/assets/lcpc-branding/resource-ui\.css(?:\?[^\"\']*)?[\"\'][^>]*>','',text)
  file.write_text(text)
 install_participant_identity(state)
 install_result_notifications(state)
 refresh_asset_versions(state)


def install_result_notifications(state,hook=False):
 """Global final-verdict alerts; retain custom resource content and vendor archives."""
 state=Path(state);web=state/'wti/WebContent/WTI-UI';assets=web/'assets/lcpc-branding';assets.mkdir(parents=True,exist_ok=True)
 if hook and (web/'main.js').exists():
  from infra.frontend_results import install as install_hook
  install_hook(web)
 for name in ('result-notifications.js','result-notifications.css'):shutil.copyfile(ROOT/'lcpc/branding'/name,assets/name)
 for file in (web/'index.html',state/'participant-resources/instructions/index.html',state/'participant-resources/problems/index.html',web/'standings/index.html'):
  if not file.is_file():continue
  text=file.read_text()
  if hook and file==web/'index.html':text=re.sub(r'(src=["\x27]main\.js)(?:\?[^"\x27]*)?(["\x27])',r'\1?v=lcpc-results-1\2',text)
  for name,tag in [('result-notifications.css','<link rel="stylesheet" href="/assets/lcpc-branding/result-notifications.css?v=1">'),('result-notifications.js','<script src="/assets/lcpc-branding/result-notifications.js?v=1"></script>')]:
   if '/assets/lcpc-branding/'+name not in text:
    if '</head>' not in text:raise RuntimeError('Unexpected participant result notification page layout')
    text=text.replace('</head>',tag+'</head>',1)
  file.write_text(text)


def style_resource_page(file,route):
 """Replace the known legacy theme, retaining customized text/scripts and custom styles."""
 if not file.is_file():return
 text=file.read_text()
 legacy={'instructions': 'bcb5a0e17c2a5b15d663545381285c28d006b114f0af9bc1a2d25bae387c7a75', 'problems': '0d630f50b1b75cfcdda544821ba9f9f50d3902517452b69ed8f2beaf12da6dde'}
 text=re.sub(r'<style>.*?</style>',lambda match:'' if hashlib.sha256(match[0].encode()).hexdigest()==legacy.get(route) else match[0],text,flags=re.S)
 text=re.sub(r'<link\b[^>]*href=[\"\']/assets/lcpc-branding/resource-ui\.css(?:\?[^\"\']*)?[\"\'][^>]*>','',text)
 classes='lcpc-resource-page lcpc-'+route+'-page'
 def body(match):
  tag=match[0];current=re.search(r'\bclass=([\"\'])(.*?)\1',tag)
  if current:
   names=current[2].split()
   for name in classes.split():
    if name not in names:names.append(name)
   return tag[:current.start(2)]+' '.join(names)+tag[current.end(2):]
  return tag[:-1]+' class="'+classes+'">'
 text=re.sub(r'<body\b[^>]*>',body,text,count=1)
 if '/assets/lcpc-branding/resource-pages.css' not in text:
  if '</head>' not in text:raise RuntimeError('Unexpected resource page layout')
  text=text.replace('</head>','<link rel="stylesheet" href="/assets/lcpc-branding/resource-pages.css?v=1"></head>',1)
 file.write_text(text)


def install_participant_identity(state):
 """Install public identity readers; never publish settings, credentials or private resources."""
 state=Path(state);web=state/'wti/WebContent/WTI-UI';assets=web/'assets/lcpc-branding';assets.mkdir(parents=True,exist_ok=True)
 for name in ('participant-identity.js','participant-identity.css','header.js','standings.js','scoreboard-model.js','standings.css','contest-clock.js','contest-clock.css'):
  shutil.copyfile(ROOT/'lcpc/branding'/name,assets/name)
 if (web/'standings').is_dir():shutil.copyfile(ROOT/'lcpc/public-standings/scoreboards.js',web/'standings/scoreboards.js')
 pages=[web/'index.html',state/'participant-resources/instructions/index.html',state/'participant-resources/problems/index.html',web/'standings/index.html']
 for file in pages:
  if not file.exists():continue
  text=file.read_text()
  for marker,closing,tag in [
   ('/assets/lcpc-branding/participant-identity.css','</head>','<link rel="stylesheet" href="/assets/lcpc-branding/participant-identity.css?v=1">'),
   ('/assets/lcpc-branding/participant-identity.js','</body>','<script src="/assets/lcpc-branding/participant-identity.js?v=1" defer></script>'),
   ('/assets/lcpc-branding/contest-clock.css','</head>','<link rel="stylesheet" href="/assets/lcpc-branding/contest-clock.css?v=1">'),
   ('/assets/lcpc-branding/contest-clock.js','</body>','<script src="/assets/lcpc-branding/contest-clock.js?v=1" defer></script>')]:
   if marker not in text:
    if closing not in text:raise RuntimeError('Unexpected participant page layout')
    text=text.replace(closing,tag+closing,1)
  for name in ('download-feedback.js','download-feedback.css'):
   shutil.copyfile(ROOT/'lcpc/branding'/name,assets/name)
  if '/assets/lcpc-branding/download-feedback.js' not in text:
   text=text.replace('</head>','<link rel="stylesheet" href="/assets/lcpc-branding/download-feedback.css?v=1"><script src="/assets/lcpc-branding/download-feedback.js?v=1" defer></script></head>',1)
  for name in ('participant-theme.js','participant-theme.css'):
   shutil.copyfile(ROOT/'lcpc/branding'/name,assets/name)
  theme_tags='<link rel="stylesheet" href="/assets/lcpc-branding/participant-theme.css?v=1"><link rel="stylesheet" href="/assets/lcpc-branding/participant-theme-values.css?v=1"><script src="/assets/lcpc-branding/participant-theme.js?v=1"></script>'
  if '/assets/lcpc-branding/participant-theme.js' not in text:text=text.replace('</head>',theme_tags+'</head>',1)
  if not (assets/'participant-theme-values.css').exists():
   import sys
   sys.path.insert(0,str(ROOT/'lcpc/admin'))
   from participant_theme import css,DEFAULT
   (assets/'participant-theme-values.css').write_text(css(DEFAULT))
  text=re.sub(r'(lcpc-branding/contest-clock\.(?:js|css))(?:\?v=[^"\s]+)?',r'\1?v=audience-2',text)
  if file==web/'index.html':text=re.sub(r'(lcpc-branding/header\.js)\?v=[^"\s]+',r'\1?v=identity-1',text)
  text=re.sub(r'(lcpc-branding/(?:standings|scoreboard-model)\.(?:js|css))(?:\?v=[^"\s]+)?',r'\1?v=clock-colors-1',text)
  file.write_text(text)
 manifest=state/'participant-resources/identity.json'
 if manifest.exists():
  import json
  value=json.loads(manifest.read_text())
  for logo in value.get('logos',[]):
   name=Path(logo['url']).name
   if not re.fullmatch(r'[a-f0-9]{64}\.(png|jpg)',name):raise RuntimeError('Invalid public identity asset')
   source=state/'participant-resources/identity-assets'/name;target=assets/'identity'/name;target.parent.mkdir(exist_ok=True);shutil.copyfile(source,target)
  target=assets/'participant-identity.json';temporary=target.with_suffix('.tmp');temporary.write_bytes(manifest.read_bytes());temporary.replace(target)


def refresh_asset_versions(state):
 """Content-address changed assets so existing browsers receive fixes after a restart."""
 state=Path(state);web=state/'wti/WebContent/WTI-UI';assets=web/'assets/lcpc-branding'
 for file in (web/'index.html',web/'standings/index.html',state/'participant-resources/instructions/index.html',state/'participant-resources/problems/index.html'):
  if not file.exists():continue
  def replace(match):
   target=assets/match.group(2)
   return match.group(1)+match.group(2)+'?v='+hashlib.sha256(target.read_bytes()).hexdigest()[:12] if target.is_file() else match.group(0)
  text=re.sub(r"((?:/)?assets/lcpc-branding/)([A-Za-z0-9_.-]+)(?:\?[^\"'\s>]*)?",replace,file.read_text())
  file.write_text(text)
