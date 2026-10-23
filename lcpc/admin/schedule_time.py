"""Country-aware wall-clock scheduling. ZoneInfo validates DST gaps and folds."""
from pathlib import Path
from datetime import datetime,timezone
from zoneinfo import ZoneInfo,ZoneInfoNotFoundError
from functools import lru_cache
import json,re
from core import Error,require

@lru_cache(maxsize=1)
def countries():
 data=json.loads((Path(__file__).parent/'timezones.json').read_text())
 rows=[]
 for country in data['countries']:
  supported=[]
  for zone in country['zones']:
   try:ZoneInfo(zone['id']);supported.append(zone)
   except ZoneInfoNotFoundError:pass
  if supported:rows.append({**country,'zones':supported})
 return rows

def validate_zone(country,zone):
 require(isinstance(country,str) and isinstance(zone,str),'Choose a country and time zone')
 row=next((row for row in countries() if row['code']==country),None)
 require(row and any(z['id']==zone for z in row['zones']),'The time zone must belong to the selected country')
 return ZoneInfo(zone)

def iso_utc(instant):return instant.astimezone(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z')
def offset_label(delta):
 minutes=int(delta.total_seconds()//60);sign='+' if minutes>=0 else '-';minutes=abs(minutes)
 return 'UTC'+sign+str(minutes//60).zfill(2)+':'+str(minutes%60).zfill(2)

def readable(value):
 weekdays=('Mon','Tue','Wed','Thu','Fri','Sat','Sun');months=('Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec')
 return f'{weekdays[value.weekday()]}, {value.day:02d} {months[value.month-1]} {value.year:04d}, {value.hour:02d}:{value.minute:02d}:{value.second:02d}'

def preview(local,country,zone,instant=None):
 tz=validate_zone(country,zone);anchor=None
 if instant is not None:
  require(isinstance(instant,str) and len(instant)<=50,'Invalid scheduled instant')
  try:
   anchor=datetime.fromisoformat(instant.replace('Z','+00:00'));require(anchor.tzinfo is not None,'Use an instant with a UTC offset');local=anchor.astimezone(tz).strftime('%Y-%m-%dT%H:%M:%S')
  except (ValueError,OverflowError):raise Error(400,'Invalid scheduled instant')
 require(isinstance(local,str) and len(local)<=32,'Invalid date and time')
 if not local:return {'valid':True,'empty':True,'candidates':[],'ambiguous':False}
 require(re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2})?',local),'Choose a date and local time')
 try:wall=datetime.fromisoformat(local)
 except ValueError:raise Error(400,'Choose a valid calendar date and time')
 require(1900<=wall.year<=9999,'Use a year from 1900 to 9999')
 found={}
 for fold in (0,1):
  zoned=wall.replace(tzinfo=tz,fold=fold)
  try:
   instant=zoned.astimezone(timezone.utc)
   if instant.astimezone(tz).replace(tzinfo=None)==wall:found[iso_utc(instant)]={'utc':iso_utc(instant),'offset':offset_label(zoned.utcoffset()),'utcLabel':readable(instant)+' UTC'}
  except (OverflowError,ValueError):continue
 candidates=[found[key] for key in sorted(found)]
 if not candidates:return {'valid':False,'empty':False,'ambiguous':False,'candidates':[],'error':'This local time does not exist because the clocks move forward. Choose another time.'}
 selected=next((i for i,item in enumerate(candidates) if anchor is not None and datetime.fromisoformat(item['utc'].replace('Z','+00:00'))==anchor.astimezone(timezone.utc).replace(microsecond=0)),None)
 return {'valid':True,'empty':False,'local':wall.isoformat(timespec='seconds'),'display':readable(wall),'ambiguous':len(candidates)>1,'candidates':candidates,'selected':selected}

def normalize(args,current_start=None):
 """Return bridge arguments and optional preferences; never trust client UTC math."""
 data=dict(args)
 if 'scheduledLocal' not in data:
  return data,None
 country=data.pop('scheduleCountry',None);zone=data.get('scheduleTimeZone');local=data.pop('scheduledLocal');occurrence=data.pop('scheduleOccurrence',None)
 result=preview(local,country,zone);require(result['valid'],result.get('error','Invalid date and time'))
 if result['empty']:data['scheduledStart']=''
 else:
  if result['ambiguous']:require(type(occurrence) is int and occurrence in range(len(result['candidates'])),'This time occurs twice. Choose its UTC offset.')
  else:require(occurrence is None or occurrence==0,'Invalid time occurrence');occurrence=0
  chosen=result['candidates'][occurrence]['utc']
  # A calendar picker works to whole seconds. Preserve the original subsecond
  # precision when the organizer has not changed the scheduled instant.
  if current_start:
   try:
    old=datetime.fromisoformat(current_start.replace('Z','+00:00'));new=datetime.fromisoformat(chosen.replace('Z','+00:00'))
    if old.tzinfo and old.astimezone(timezone.utc).replace(microsecond=0)==new:data['scheduledStart']=current_start
    else:data['scheduledStart']=chosen
   except (ValueError,AttributeError):data['scheduledStart']=chosen
  else:data['scheduledStart']=chosen
 return data,{'country':country,'timeZone':zone}
