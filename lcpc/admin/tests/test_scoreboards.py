import copy,http.client,json,sys,tempfile,threading,unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]));sys.path.insert(0,str(Path(__file__).resolve().parent))
from core import password_hash
from server import App,Server
from test_contests import Fake
class ScoreboardRoutes(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.temp=tempfile.TemporaryDirectory();cls.fake=Fake(Path(cls.temp.name));cls.fake.data['updatedAt']=datetime.now(timezone.utc).isoformat();cls.fake.data['standings']={'contestStandings':{'standingsHeader':{'title':'PRIVATE-FULL','totalSolved':2},'teamStanding':{'teamName':'Fixture','solved':2,'points':140}}};cls.app=App(cls.temp.name,0,cls.fake);cls.server=Server(('127.0.0.1',0),cls.app);cls.origin='http://127.0.0.1:'+str(cls.server.server_port);cls.app.origins={cls.origin};cls.password='Fixture-scoreboards-password-42'
  with cls.app.store.db() as db:db.execute('INSERT INTO users(username,password,role,must_change) VALUES(?,?,?,0)',('owner',password_hash(cls.password),'owner'))
  threading.Thread(target=cls.server.serve_forever,daemon=True).start()
  cls.path=Path(cls.temp.name)/'wti/WebContent/WTI-UI/standings/data.json';cls.path.parent.mkdir(parents=True)
 @classmethod
 def tearDownClass(cls):cls.server.shutdown();cls.server.server_close();cls.app.manager.close();cls.temp.cleanup()
 def setUp(self):
  self.public={'publishedAt':datetime.now(timezone.utc).isoformat(),'release':{'schema':1,'frozen':True,'preliminaryResultsCounted':False},'contestStandings':{'standingsHeader':{'title':'PUBLIC-FROZEN','totalSolved':1},'teamStanding':{'teamName':'Fixture','solved':1,'points':30,'problemSummaryInfo':[{'index':2,'isSolved':False,'isPending':True,'solutionTime':0}]}}};self.path.write_text(json.dumps(self.public))
 def request(self,path,data=None,cookie=None):
  headers={'Host':self.origin.split('//')[1],'Origin':self.origin,'Content-Type':'application/json'}
  if cookie:headers['Cookie']=cookie
  c=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=10);c.request('GET' if data is None else 'POST',path,None if data is None else json.dumps(data),headers);r=c.getresponse();result=(r.status,dict(r.getheaders()),r.read());c.close();return result
 def login(self):return self.request('/api/login',{'username':'owner','password':self.password})[1]['Set-Cookie'].split(';')[0]
 def url(self,mode):return '/api/scoreboards/'+mode+'?contestId='+self.app.manager.data['selected']
 def test_both_dashboard_views_require_login(self):
  for mode in ('public','live'):self.assertEqual(self.request(self.url(mode))[0],401)
 def test_public_reads_only_export_and_never_full_private_snapshot(self):
  with patch.object(self.app.bridge,'snapshot',side_effect=AssertionError('Private snapshot read')),patch('scoreboards.access',return_value={'origin':'http://192.168.10.3:8088'}):
   status,h,b=self.request(self.url('public'),cookie=self.login())
  self.assertEqual(status,200);self.assertNotIn(b'PRIVATE-FULL',b);out=json.loads(b);self.assertEqual(out['payload'],self.public);self.assertEqual(out['displayUrl'],'http://192.168.10.3:8088/standings/');self.assertIn('private',h['Cache-Control'])
 def test_live_has_native_final_standings_without_mutation(self):
  before=copy.deepcopy(self.fake.data)
  with patch('scoreboards.access',return_value={'origin':None}):status,h,b=self.request(self.url('live'),cookie=self.login())
  self.assertEqual(status,200);out=json.loads(b);self.assertEqual(out['payload']['contestStandings']['standingsHeader']['title'],'PRIVATE-FULL');self.assertEqual(before,self.fake.data);self.assertEqual(self.fake.calls,[])
 def test_live_color_and_clock_metadata_are_native_and_do_not_mutate_the_cached_snapshot(self):
  before=copy.deepcopy(self.fake.data)
  try:
   self.fake.data['standings']['contestStandings']['standingsHeader']['problem']=[{'id':1,'title':'Alpha'}]
   self.fake.data['problems'][0].update(colorName='Red',colorRGB='#E53935')
   expected=copy.deepcopy(self.fake.data)
   with patch('scoreboards.access',return_value={'origin':None}):status,h,b=self.request(self.url('live'),cookie=self.login())
   self.assertEqual(status,200);payload=json.loads(b)['payload'];column=payload['contestStandings']['standingsHeader']['problem'][0]
   self.assertEqual(column['colorRGB'],'#E53935');self.assertEqual(column['letter'],'A');self.assertEqual(payload['clock']['remainingSeconds'],3540)
   self.assertEqual(expected,self.fake.data)
  finally:self.fake.data.clear();self.fake.data.update(before)
 def test_missing_stale_bad_and_future_public_export_fail_closed(self):
  for kind in ('missing','stale','future','invalid'):
   if kind=='missing':self.path.unlink(missing_ok=True)
   elif kind=='invalid':self.path.write_text('{}')
   else:
    p=copy.deepcopy(self.public);p['publishedAt']=(datetime.now(timezone.utc)+timedelta(seconds=60 if kind=='future' else -60)).isoformat();self.path.write_text(json.dumps(p))
   with patch.object(self.app.bridge,'snapshot',side_effect=AssertionError('Fallback leaked private data')):
    status,h,b=self.request(self.url('public'),cookie=self.login())
   self.assertEqual(status,503);self.assertNotIn(b'PRIVATE-FULL',b)
 def test_workspace_scope_and_inactive_contests_rejected(self):
  cookie=self.login()
  for url in (self.url('public').replace('contestId=','contestId=stale-'),self.url('live')+'&contestId=other','/api/scoreboards/live'):self.assertEqual(self.request(url,cookie=cookie)[0],409)
  old=self.app.manager.data['active'];self.app.manager.data['active']=None
  try:self.assertEqual(self.request(self.url('public'),cookie=cookie)[0],409)
  finally:self.app.manager.data['active']=old
 def test_unsafe_provisional_scoring_cannot_appear_as_final_live_results(self):
  self.fake.data['judging']['preliminaryResultsCounted']=True
  try:self.assertEqual(self.request(self.url('live'),cookie=self.login())[0],409)
  finally:self.fake.data['judging'].pop('preliminaryResultsCounted')
if __name__=='__main__':unittest.main()
