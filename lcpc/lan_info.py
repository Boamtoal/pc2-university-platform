#!/usr/bin/env python3
"""Read local Mac LAN addresses without Internet access or network changes."""
import subprocess,re,ipaddress,json
from pathlib import Path
def addresses(text):
 interface=None;rows=[]
 allowed=[ipaddress.ip_network(x) for x in ['10.0.0.0/8','172.16.0.0/12','192.168.0.0/16']]
 for line in text.splitlines():
  if line and not line[0].isspace():interface=line.split(':',1)[0]
  match=re.search(r'\binet\s+(\d+\.\d+\.\d+\.\d+)\s+netmask\s+(0x[0-9a-fA-F]+|[\d.]+)',line)
  if not match or not interface or interface.startswith(('lo','utun','ipsec')):continue
  ip=ipaddress.ip_address(match[1])
  if not any(ip in n for n in allowed):continue
  mask=match[2];mask=str(ipaddress.IPv4Address(int(mask,16))) if mask.startswith('0x') else mask
  net=ipaddress.ip_network(str(ip)+'/'+mask,strict=False)
  rows.append({'interface':interface,'ip':str(ip),'cidr':str(net)})
 return rows
if __name__=='__main__':
 result=subprocess.run(['/sbin/ifconfig'],check=True,capture_output=True,text=True)
 rows=addresses(result.stdout)
 if not rows:raise SystemExit('لم أجد عنوان LAN خاصًا. اتصل براوتر القاعة عبر Wi-Fi أو Ethernet ثم أعد الأمر؛ لا يلزم إنترنت.')
 print('عناوين الشبكة المحلية الحالية — لا يحتاج هذا الفحص إنترنت:\n')
 from workspace_state import managed_state
 try:profile_path=managed_state()/'network/profile.json'
 except RuntimeError:profile_path=Path('/nonexistent-contest-profile.json')
 profile=json.loads(profile_path.read_text()) if profile_path.exists() else {}
 for row in rows:
  origin=profile.get('origin') if profile.get('bind')==row['ip'] else 'http://'+row['ip']+':8088'
  print(f"المنفذ: {row['interface']}   IP: {row['ip']}   CIDR: {row['cidr']}")
  print(f"رابط الفرق المقترح بعد اعتماد المسابقة وتهيئة LAN: {origin}/#/login")
  print(f"لوحة النتائج بعد تسجيل الدخول: {origin}/#/scoreboard\n")
 print('هذه روابط مقترحة؛ الفحص لا يفتح الشبكة. اختر منفذ القاعة نفسه، وقد يتغير IP عند تغيير الراوتر.')
 print('127.0.0.1 يخص جهازك وحده ولا يُرسل للفرق.')
