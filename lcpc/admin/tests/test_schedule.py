import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core import Store,Error
from schedule_time import preview,normalize,countries
class ScheduleTime(unittest.TestCase):
 def test_libya_calendar_to_utc(self):
  value=preview('2026-10-20T14:30','LY','Africa/Tripoli');self.assertEqual(value['candidates'][0]['utc'],'2026-10-20T12:30:00Z');self.assertEqual(value['candidates'][0]['offset'],'UTC+02:00')
 def test_fractional_hour_offsets(self):
  self.assertEqual(preview('2026-10-20T14:30','IN','Asia/Kolkata')['candidates'][0]['utc'],'2026-10-20T09:00:00Z')
  self.assertEqual(preview('2026-10-20T14:30','NP','Asia/Kathmandu')['candidates'][0]['utc'],'2026-10-20T08:45:00Z')
 def test_dst_gaps_are_not_silently_shifted(self):
  self.assertFalse(preview('2026-03-08T02:30','US','America/New_York')['valid'])
  self.assertFalse(preview('2026-10-04T02:30','AU','Australia/Sydney')['valid'])
 def test_repeated_hour_requires_explicit_occurrence(self):
  value=preview('2026-11-01T01:30','US','America/New_York');self.assertTrue(value['ambiguous']);self.assertEqual([c['utc'] for c in value['candidates']],['2026-11-01T05:30:00Z','2026-11-01T06:30:00Z'])
  args={'scheduledLocal':'2026-11-01T01:30','scheduleCountry':'US','scheduleTimeZone':'America/New_York'}
  with self.assertRaises(Error):normalize(args)
  self.assertEqual(normalize({**args,'scheduleOccurrence':1})[0]['scheduledStart'],'2026-11-01T06:30:00Z')
 def test_country_change_preserves_instant_across_date_boundary(self):
  value=preview('', 'US','America/Los_Angeles',instant='2026-01-01T02:00:00Z');self.assertEqual(value['local'],'2025-12-31T18:00:00');self.assertEqual(value['candidates'][value['selected']]['utc'],'2026-01-01T02:00:00Z')
 def test_existing_subseconds_and_second_dst_occurrence_preserved(self):
  value=preview('','US','America/New_York',instant='2026-11-01T06:30:00.918Z');self.assertEqual(value['selected'],1)
  result,prefs=normalize({'scheduledLocal':value['local'],'scheduleCountry':'US','scheduleTimeZone':'America/New_York','scheduleOccurrence':value['selected']},'2026-11-01T06:30:00.918Z')
  self.assertEqual(result['scheduledStart'],'2026-11-01T06:30:00.918Z');self.assertNotIn('scheduledLocal',result);self.assertEqual(prefs['country'],'US')
 def test_country_and_calendar_validation(self):
  for local,country,zone in [('2026-02-30T12:00','LY','Africa/Tripoli'),('2026-10-20T14:30','LY','America/New_York'),('2026-10-20T14:30','ZZ','../../etc/passwd'),('not a date','LY','Africa/Tripoli')]:
   with self.assertRaises(Error):preview(local,country,zone)
 def test_clear_start_and_persist_zone(self):
  result,prefs=normalize({'scheduledLocal':'','scheduleCountry':'LY','scheduleTimeZone':'Africa/Tripoli'});self.assertEqual(result['scheduledStart'],'')
  with tempfile.TemporaryDirectory() as folder:
   store=Store(folder);store.save_schedule_preferences({'country':'NP','timeZone':'Asia/Kathmandu'});self.assertEqual(Store(folder).schedule_preferences()['timeZone'],'Asia/Kathmandu')
 def test_offline_catalog_covers_multiple_zones(self):
  self.assertGreater(len(countries()),200);self.assertGreater(len(next(c for c in countries() if c['code']=='US')['zones']),1)
if __name__=='__main__':unittest.main(verbosity=2)
