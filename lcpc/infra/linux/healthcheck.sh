#!/bin/sh
set -eu
python3 - <<'PY'
import subprocess,json,os,pathlib
q=lambda a:subprocess.run(a,capture_output=True,text=True)
cgroups=pathlib.Path('/sys/fs/cgroup/cgroup.controllers').exists()
active=q(['systemctl','is-active','pc2judge.service']).stdout.strip()=='active'
cpp=q(['/usr/bin/g++','--version']).stdout.splitlines()[0]
mounts=q(['findmnt','-rn','-t','virtiofs,9p']).stdout.strip()
listener=q(['ss','-lnt']).stdout
pid=q(['systemctl','show','pc2judge.service','--property=MainPID','--value']).stdout.strip()
connections=q(['ss','-ntp','state','established']).stdout.splitlines()
connected=bool(pid and pid!='0' and any('127.0.0.1' in l and ':50002' in l and 'pid='+pid+',' in l for l in connections))
ready=cgroups and active and not mounts and connected and '127.0.0.1:50002' in listener
print(json.dumps({'ready':ready,'cgroup_v2':cgroups,'coordinator_active':active,'coordinator_connected':connected,'shared_host_mounts':mounts,'private_tunnel': '127.0.0.1:50002' in listener,'compiler':cpp,'arch':os.uname().machine}))
PY
