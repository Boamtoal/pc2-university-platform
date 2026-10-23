"""Participant-only result DTOs. Never forward preliminary judgements or judge evidence."""
import hashlib,re
from pathlib import Path

def payload(state,token,rows):
 if not isinstance(rows,list) or len(rows)>10000:raise ValueError('Invalid participant runs')
 results=[]
 for row in rows:
  if not isinstance(row,dict):raise ValueError('Invalid participant run')
  if row.get('deleted') is True or row.get('isDeleted') is True:continue
  identifier=str(row.get('id',''))
  if not re.fullmatch(r'[1-9][0-9]{0,9}(?:-[1-9][0-9]{0,9})?',identifier):raise ValueError('Invalid submission identifier')
  final=row.get('isFinal') is True and row.get('isPreliminary',False) is False
  label=row.get('judgement','') if final else ''
  if not isinstance(label,str) or not label.strip():final=False;label=''
  text=lambda value,limit:''.join(c for c in (value if isinstance(value,str) else '') if ord(c)>=32 and ord(c)!=127)[:limit]
  results.append({'id':identifier,'problem':text(row.get('problem',''),200),'language':text(row.get('language',''),120),'final':final,'verdict':text(label,160) if final else ''})
 # The browser can coordinate tabs without storing an authentication token.
 scope=hashlib.sha256((str(Path(state).resolve())+'\0'+token).encode()).hexdigest()
 return {'schema':1,'scope':scope,'runs':results}
