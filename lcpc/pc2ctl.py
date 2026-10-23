#!/usr/bin/env python3
"""Local PC2 lifecycle; no passwords in process arguments or public output."""
from pathlib import Path
import os, subprocess, sys, time, signal, json, shutil, tarfile, hashlib, zipfile, secrets, re, fcntl
ROOT=Path(__file__).resolve().parents[1]
LOCAL=Path(os.environ.get('LCPC_STATE_DIR',str(ROOT/'.local'))).resolve()
DEFAULT=ROOT/'.local'
os.umask(0o077)
from runtime_paths import java_executable
JAVA=java_executable()
CP=str(ROOT/'lcpc/build')+':'+str(ROOT/'lib/*')
ROLES=['server','judge','admin','team1','judge2','board','wti']
def cmd(role,extra=()):
    mode_file=LOCAL/'mode.json'
    mode=json.loads(mode_file.read_text()).get('mode') if mode_file.exists() else 'local'
    if role in ['judge','judge2'] and mode in ['isolated-trial','competition']:
        raise RuntimeError('macOS judging is forbidden in isolated/competition mode; use linux-judge')
    headless=role not in ['admin','team1','judge2','board']
    cp=CP if role!='wti' else str(ROOT/'lcpc/build')+':'+str(LOCAL/'wti/WebTeamInterface-1.1.jar')+':'+str(ROOT/'lib/*')
    return [JAVA,'-Djdk.crypto.KeyAgreement.legacyKDF=true','-Djava.awt.headless='+str(headless).lower(),'-Dlcpc.denyExecution='+str(mode in ['isolated-trial','competition']).lower(),'-Dlcpc.branding='+str(ROOT/'lcpc/branding/assets'),'-Dlcpc.secrets='+str(LOCAL/'credentials.properties'),'-Dlcpc.cdp='+str(LOCAL/'cdp'),'-javaagent:'+str(ROOT/'lcpc/build/local-only-agent.jar'),'-Xmx'+('1024m' if role=='server' else '512m'),'-cp',cp,'LCPCLaunch',role,*extra]
def alive(pid):
    try:os.kill(pid,0)
    except ProcessLookupError:return False
    except PermissionError:return True
    # kill(0) also succeeds for zombies; do not treat these as running.
    st=subprocess.run(['ps','-o','stat=','-p',str(pid)],capture_output=True,text=True).stdout.strip()
    return bool(st) and not st.startswith('Z')
def pid_for(role):
    pf=LOCAL/(role+'.pid')
    if not pf.exists():return None
    pid=int(pf.read_text())
    if not alive(pid):return None
    args=subprocess.run(['ps','-o','command=','-p',str(pid)],capture_output=True,text=True).stdout
    if 'LCPCLaunch '+role not in args or str(LOCAL/'credentials.properties') not in args:
        # A clean shutdown can exit between the liveness and command probes.
        # A still-live mismatched PID remains an error; never signal it.
        if not alive(pid):return None
        raise RuntimeError('PID identity could not be verified for '+role)
    return pid
def ports():
    return json.loads((LOCAL/'settings.json').read_text()) if (LOCAL/'settings.json').exists() else {'port':50002,'web_port':8080}
def api(args,capture=False):
    c=cmd('api');c[-2:]=['LCPCAdmin',*args]
    with (LOCAL/'api-client.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise RuntimeError('Read-only scoreboard client is already active; use the public standings page')
        return subprocess.run(c,cwd=LOCAL/'api',capture_output=capture,text=True,timeout=120)
def listener_check(role,pid,enforce=False):
    result=subprocess.run(['lsof','-nP','-a','-p',str(pid),'-iTCP','-sTCP:LISTEN'],capture_output=True,text=True)
    lines=[l for l in result.stdout.splitlines() if '(LISTEN)' in l]
    expected=ports()['port' if role=='server' else 'web_port']
    if not lines or any('127.0.0.1:'+str(expected)+' ' not in l for l in lines):
        if enforce:os.kill(pid,signal.SIGTERM)
        raise RuntimeError(role+' did not listen exclusively on expected loopback port'+('; stopped' if enforce else ''))
def start(role,extra=()):
    if role!='server':return _start_unlocked(role,extra)
    with (DEFAULT/'contest-server-start.lock').open('a') as handle:
        try:fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise RuntimeError('Another contest server is being started. Wait for it to finish.')
        from infra.runtime_guard import ensure_single
        ensure_single(ROOT,LOCAL)
        return _start_unlocked(role,extra)
def _start_unlocked(role,extra=()):
    if pid_for(role):print(role+': already running');return
    if role=='server' and not (LOCAL/'server/profiles.properties').exists() and 'bootstrap' not in extra:
        raise RuntimeError('No initialized contest. Use init-test then bootstrap.')
    d=LOCAL/role;d.mkdir(exist_ok=True)
    with (LOCAL/(role+'.log')).open('ab') as log:
        p=subprocess.Popen(cmd(role,extra),cwd=d,stdout=log,stderr=log,start_new_session=True)
    (LOCAL/(role+'.pid')).write_text(str(p.pid))
    deadline=time.monotonic()+20
    while time.monotonic()<deadline:
        if p.poll() is not None:raise RuntimeError(role+' failed; inspect private '+str(LOCAL/(role+'.log')))
        if role not in ['server','wti']:
            time.sleep(2);break
        probe=subprocess.run(['lsof','-nP','-a','-p',str(p.pid),'-iTCP','-sTCP:LISTEN'],capture_output=True,text=True)
        if '(LISTEN)' in probe.stdout:listener_check(role,p.pid,enforce=True);break
        time.sleep(.25)
    else:
        os.kill(p.pid,signal.SIGTERM);raise RuntimeError(role+' startup timeout; stopped')
    print(role+': started (PID '+str(p.pid)+')')
def terminate(role):
    pid=pid_for(role)
    if not pid:return
    os.kill(pid,signal.SIGTERM)
    until=time.monotonic()+12
    while alive(pid) and time.monotonic()<until:time.sleep(.1)
    if alive(pid):raise RuntimeError(role+' did not exit; not forcibly killing it')
    print(role+': stopped')
def stop():
    dashboard=ROOT/'lcpc/admin/manage.py'
    if (LOCAL/'admin-dashboard/dashboard.pid').exists():subprocess.run([sys.executable,str(dashboard),'stop','--state',str(LOCAL)],check=True)
    from infra.network import stop as proxy_stop
    proxy_stop(sys.modules[__name__])
    if pid_for('server'):
        q=api(['quiesce'],capture=True)
        if q.returncode:raise RuntimeError('Cannot safely stop: private API quiesce failed; check pending runs.')
    active=DEFAULT/'linux-active-state'
    if active.exists() and active.read_text().strip()==str(LOCAL):
        from infra.vm import judge_stop
        judge_stop(sys.modules[__name__])
    for role in ['wti','judge','judge2','team1','board','admin']:terminate(role)
    if pid_for('server'):
        q=api(['shutdown'],capture=True)
        if q.returncode:raise RuntimeError('PC2 server shutdown request failed')
        until=time.monotonic()+15
        while pid_for('server') and time.monotonic()<until:time.sleep(.2)
        if pid_for('server'):raise RuntimeError('Server did not exit after PC2 shutdown; preserving state')
        print('server: clean PC2 shutdown')
    from infra.operations import awake_stop
    awake_stop(sys.modules[__name__])
def backup():
    ensure_stopped()
    dest=DEFAULT/'backups';dest.mkdir(exist_ok=True)
    target=dest/(time.strftime('%Y%m%d-%H%M%S')+'.tar.gz')
    if target.exists():raise RuntimeError('Backup already exists for this second')
    with tarfile.open(target,'x:gz') as tar:
        for name in ['credentials.properties','settings.json','secured','cdp','server','wti']:
            path=LOCAL/name
            if path.exists():tar.add(path,arcname=name)
        for role in ['api','judge','judge2','admin','team1','board']:
            tar.add(LOCAL/role/'pc2v9.ini',arcname=role+'/pc2v9.ini')
    digest=hashlib.sha256(target.read_bytes()).hexdigest()
    target.with_suffix(target.suffix+'.sha256').write_text(digest+'  '+target.name+'\n')
    print(target)
def ensure_stopped():
    if (LOCAL/'admin-dashboard/dashboard.pid').exists():
        sys.path.insert(0,str(ROOT/'lcpc/admin'))
        from manage import pid as dashboard_pid
        if dashboard_pid(LOCAL):raise RuntimeError('Stop the dashboard before taking a consistent backup.')
    if any(pid_for(r) for r in ROLES):raise RuntimeError('Stop all components before taking a consistent backup.')
    active=DEFAULT/'linux-active-state'
    if active.exists() and active.read_text().strip()==str(LOCAL):raise RuntimeError('Stop Linux Judge before backup.')
def restore(archive):
    archive=Path(archive).resolve();check=archive.with_suffix(archive.suffix+'.sha256')
    if not check.exists() or hashlib.sha256(archive.read_bytes()).hexdigest()!=check.read_text().split()[0]:raise RuntimeError('Backup checksum mismatch')
    target=DEFAULT/'instances'/('restored-'+time.strftime('%Y%m%d-%H%M%S'))
    target.mkdir(parents=True,exist_ok=False)
    with tarfile.open(archive) as tar:tar.extractall(target,filter='data')
    for folder,dirs,files in os.walk(target):
        os.chmod(folder,0o700)
        for f in files:os.chmod(Path(folder)/f,0o600)
    print(target)
def init_test(slug):
    if not re.fullmatch('[a-z0-9][a-z0-9-]{0,45}',slug):raise RuntimeError('Use a lowercase slug')
    dest=DEFAULT/'instances'/slug
    if dest.exists():raise RuntimeError('Instance exists; refusing to overwrite')
    dest.mkdir(parents=True,mode=0o700)
    creds={u:secrets.token_urlsafe(24) for u in ['contest','site1','administrator1','judge1','judge2','scoreboard1','scoreboard2','team1','team2']}
    (dest/'credentials.properties').write_text(''.join(k+'='+v+'\n' for k,v in creds.items()))
    (dest/'settings.json').write_text(json.dumps({'port':50002,'web_port':8080}))
    shutil.copytree(ROOT/'lcpc/templates/practice',dest/'cdp')
    with (dest/'cdp/config/contest.yaml').open('a') as f:f.write("\nsites:\n  - number: 1\n    name: 'OMU LOCAL TEST'\n    IP: 127.0.0.1\n    port: 50002\n    password: '"+creds['site1']+"'\n")
    rows=['site\taccount\tdisplayname\tpassword\tpermdisplay\tpermlogin']
    for user,label in [('team1','OMU Test Alpha'),('team2','OMU Test Beta')]:rows.append('1\t'+user+'\t'+label+'\t'+creds[user]+'\ttrue\ttrue')
    (dest/'cdp/config/accounts_load.tsv').write_text('\n'.join(rows)+'\n')
    for role in ['server','judge','judge2','admin','team1','board','api']:
        d=dest/role;d.mkdir();(d/'pc2v9.ini').write_text('[client]\nserver=127.0.0.1:50002\n[server]\nport=50002\n')
    with zipfile.ZipFile(ROOT/'projects/WebTeamInterface-1.1-7065.zip') as z:z.extractall(dest/'unpack')
    (dest/'unpack/WebTeamInterface-1.1').rename(dest/'wti');(dest/'unpack').rmdir()
    if (ROOT/'lcpc/branding/assets').is_dir():
        from infra.branding import install
        install(dest)
    (dest/'wti/pc2v9.ini').write_text('[client]\nserver=127.0.0.1:50002\n[server]\nwtiport=8080\nwtiwsName=/websocket\nwtiscoreboardaccount=scoreboard2\nwtiscoreboardpassword='+creds['scoreboard2']+'\nwtiOverridePublicIP=127.0.0.1\nallowedOSName1=Mac OS X\n')
    for folder,dirs,files in os.walk(dest):
        os.chmod(folder,0o700)
        for name in files:os.chmod(Path(folder)/name,0o600)
    print(dest)
def main():
    action=sys.argv[1] if len(sys.argv)>1 else 'status'
    if action in ['dashboard-init','dashboard','dashboard-stop','dashboard-status']:
        operation={'dashboard-init':'init','dashboard':'start','dashboard-stop':'stop','dashboard-status':'status'}[action]
        raise SystemExit(subprocess.run([sys.executable,str(ROOT/'lcpc/admin/manage.py'),operation,'--state',str(LOCAL)]).returncode)
    if action in ['help','--help','-h']:
        print('Local trusted training: up | training | start | admin | status | stop')
        print('Isolated test (use trialctl.py): isolated-up | linux-judge | linux-stop | linux-status')
        print('Participant proxy: network-auto | network-auto-status | network-prepare [IP CIDR] | network-http-prepare IP CIDR | network-confirm IP CIDR | network-trial | network-stop')
        print('Organizer dashboard: dashboard-init | dashboard | dashboard-stop | dashboard-status')
        print('Operations: health [local|isolated-trial|production] | monitor [COUNT INTERVAL] | logs [ROLE] | awake')
        print('Recovery: backup-encrypted | restore-encrypted FILE | backup | restore FILE')
        print('Fresh drafts: init-test NAME | init-isolated-test NAME | event-draft NAME')
        print('Production: competition (locked until actual production acceptance). Startup never starts the clock.')
    elif action=='bootstrap':
        if (LOCAL/'server/profiles.properties').exists():raise RuntimeError('Bootstrap is only for new instances; use start for existing contests.')
        start('server',('bootstrap',))
        q=api(['secure-bootstrap'],capture=True)
        if q.returncode:raise RuntimeError('Credential bootstrap failed; stop and inspect private state')
        (LOCAL/'secured').write_text('Credential initialization completed\n');print('credentials: secured')
    elif action=='start':start('server')
    elif action=='up':
        if (LOCAL/'mode.json').exists() and json.loads((LOCAL/'mode.json').read_text()).get('mode') in ['isolated-trial','competition']:
            raise RuntimeError('Use isolated-up for this contest; macOS AutoJudge will not be started')
        if not (LOCAL/'secured').exists():raise RuntimeError('Credential bootstrap not marked complete')
        for role in ['server','judge','wti']:start(role)
    elif action in ROLES[1:]:start(action)
    elif action=='api':raise SystemExit(api(sys.argv[2:]).returncode)
    elif action=='stop':stop()
    elif action=='backup':backup()
    elif action=='backup-encrypted':
        from infra.secure_backup import encrypted_backup
        encrypted_backup(sys.modules[__name__])
    elif action=='restore-encrypted':
        from infra.secure_backup import encrypted_restore
        encrypted_restore(sys.modules[__name__],sys.argv[2])
    elif action=='restore':restore(sys.argv[2])
    elif action=='init-test':init_test(sys.argv[2])
    elif action=='init-isolated-test':
        from infra.templates import isolated_test
        isolated_test(sys.modules[__name__],sys.argv[2])
    elif action=='event-draft':
        from infra.templates import event_draft
        event_draft(sys.modules[__name__],sys.argv[2])
    elif action=='network-prepare':
        from infra.network import prepare
        prepare(sys.modules[__name__],*sys.argv[2:])
    elif action=='network-http-prepare':
        from infra.network import prepare
        prepare(sys.modules[__name__],*sys.argv[2:],transport='http')
    elif action=='network-trial':
        from infra.network import start as proxy_start
        proxy_start(sys.modules[__name__])
    elif action=='network-auto':
        from infra.network import enable_auto
        enable_auto(sys.modules[__name__])
    elif action=='network-auto-status':
        from infra.network import role_running
        path=LOCAL/'network/auto-status.json'
        result=json.loads(path.read_text()) if path.exists() else {'available':False}
        result['monitor_running']=role_running(sys.modules[__name__],'network-watch',str(ROOT/'lcpc/infra/network_watch.py'))
        print(json.dumps(result,indent=2))
    elif action=='network-confirm':
        from infra.network import confirm
        confirm(sys.modules[__name__],*sys.argv[2:])
    elif action=='network-stop':
        from infra.network import stop as proxy_stop
        proxy_stop(sys.modules[__name__])
    elif action=='isolated-up':
        if not (LOCAL/'mode.json').exists() or json.loads((LOCAL/'mode.json').read_text()).get('mode')!='isolated-trial':
            raise RuntimeError('isolated-up requires an explicitly configured isolated-trial state')
        start('server')
        from infra.operations import awake
        awake(sys.modules[__name__])
        start('wti')
        from infra.vm import judge_start
        judge_start(sys.modules[__name__])
    elif action=='linux-install':
        from infra.vm import install_guest
        install_guest(sys.modules[__name__])
    elif action=='linux-judge':
        from infra.vm import judge_start
        judge_start(sys.modules[__name__])
    elif action=='linux-stop':
        from infra.vm import judge_stop
        judge_stop(sys.modules[__name__])
    elif action=='linux-status':
        from infra.vm import vm_health
        print(json.dumps(vm_health(sys.modules[__name__]),indent=2))
    elif action=='awake':
        from infra.operations import awake
        awake(sys.modules[__name__])
    elif action=='logs':
        from infra.operations import logs
        logs(sys.modules[__name__],sys.argv[2] if len(sys.argv)>2 else 'server')
    elif action=='monitor':
        raise SystemExit(subprocess.run([sys.executable,str(ROOT/'lcpc/infra/monitor.py'),*sys.argv[2:]]).returncode)
    elif action=='health':
        from infra.health import inspect
        default_mode=json.loads((LOCAL/'mode.json').read_text()).get('mode','local') if (LOCAL/'mode.json').exists() else 'local'
        result=inspect(sys.modules[__name__],sys.argv[2] if len(sys.argv)>2 else default_mode)
        if not result['ready']:raise SystemExit(2)
    elif action=='training':
        if (LOCAL/'mode.json').exists() and json.loads((LOCAL/'mode.json').read_text()).get('mode') in ['isolated-trial','competition']:
            raise RuntimeError('This state requires isolated-up; training is only for the local trusted-sample environment')
        for role in ['server','judge','wti']:start(role)
    elif action=='competition':
        from infra.health import inspect
        result=inspect(sys.modules[__name__],'production')
        if not result['ready']:raise RuntimeError('Competition mode is locked: production acceptance checks have not passed. No service changed.')
    elif action=='status':
        for role in ROLES:
            pid=pid_for(role);print(role+': '+('running PID '+str(pid) if pid else 'stopped'))
            if pid and role in ['server','wti']:listener_check(role,pid)
    else:raise RuntimeError('Usage: pc2ctl.py up|start|bootstrap|admin|judge|judge2|team1|board|wti|status|stop|backup|restore FILE|init-test NAME|api OP')
if __name__=='__main__':
    try:main()
    except (OSError,RuntimeError,subprocess.TimeoutExpired,subprocess.CalledProcessError) as e:raise SystemExit(str(e))
