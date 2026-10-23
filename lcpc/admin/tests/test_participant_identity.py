import base64,copy,json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]));sys.path.insert(0,str(Path(__file__).resolve().parent))
from core import Store,Error
from participant_identity import load,save,version,public,publish,inherit
from dashboard_branding import public as dashboard_public
from participant_theme import DEFAULT as THEME_DEFAULT
from test_dashboard_branding import png
class Identity(unittest.TestCase):
 def setUp(self):self.temp=tempfile.TemporaryDirectory();(Path(self.temp.name)/'active').mkdir();self.store=Store(Path(self.temp.name)/'active');web=self.store.state/'wti/WebContent/WTI-UI';web.mkdir(parents=True);(web/'index.html').write_text('<html></html>')
 def tearDown(self):self.temp.cleanup()
 def args(self):
  current=load(self.store);return {'version':version(current),**{k:v for k,v in current.items() if k!='logos'},'logos':[{k:v for k,v in logo.items() if k!='image'} for logo in current['logos']]}
 def test_identity_publishes_only_allowlisted_public_data_and_original_or_validated_image_bytes(self):
  dashboard=dashboard_public(self.store);args=self.args();args.update(name='University Fixture',universityName='Fixture University');args['logos'][2].update(upload=base64.b64encode(png()).decode(),label='University logo');value=save(self.store,args)
  self.assertEqual(load(Store(self.store.state))['name'],'University Fixture');self.assertEqual(dashboard_public(self.store),dashboard)
  m=json.loads((self.store.state/'wti/WebContent/WTI-UI/assets/lcpc-branding/participant-identity.json').read_text());self.assertEqual(m['name'],'University Fixture');self.assertNotIn('base64',str(m));self.assertNotIn(str(self.store.state),str(m));self.assertNotIn('password',str(m));self.assertNotIn('image',m['logos'][2]);self.assertTrue(m['logos'][2]['custom'])
  file=self.store.state/'wti/WebContent/WTI-UI'/m['logos'][2]['url'].lstrip('/');self.assertEqual(file.read_bytes(),png());self.assertNotIn('base64',str(public(self.store,'active')))
 def test_invalid_second_logo_cannot_partially_save_and_stale_saves_are_rejected(self):
  before=load(self.store);args=self.args();args['name']='Should not save';args['logos'][0]['upload']=base64.b64encode(png()).decode();args['logos'][1]['upload']=base64.b64encode(b'<svg onload="bad()"/>').decode()
  with self.assertRaises(Error):save(self.store,args)
  self.assertEqual(load(self.store),before);self.assertFalse((self.store.state/'participant-resources/identity.json').exists())
  args=self.args();args['name']='First edit';save(self.store,args)
  with self.assertRaises(Error):save(self.store,args)
 def test_reordering_visibility_and_image_restore_work_independently(self):
  args=self.args();args['logos'].reverse();args['logos'][0].update(header=False,resources=True,scoreboard=False,upload=base64.b64encode(png()).decode());save(self.store,args)
  current=load(self.store);self.assertEqual(current['logos'][0]['id'],'contest');self.assertFalse(current['logos'][0]['header']);self.assertTrue(current['logos'][0]['image'])
  args=self.args();args['logos'][0]['resetImage']=True;save(self.store,args);current=load(self.store);self.assertIsNone(current['logos'][0]['image']);self.assertFalse(current['logos'][0]['header'])
 def test_draft_and_active_identity_are_independent_and_new_contest_inherits(self):
  args=self.args();args['name']='Organization';save(self.store,args);old=(self.store.state/'wti/WebContent/WTI-UI/assets/lcpc-branding/participant-identity.json').read_bytes();(Path(self.temp.name)/'draft').mkdir();draft=Store(Path(self.temp.name)/'draft');inherit(self.store,draft);self.assertEqual(load(draft)['name'],'Organization');args=copy.deepcopy(load(draft));args['version']=version(args);args['name']='Next contest';args['logos']=[{k:v for k,v in logo.items() if k!='image'} for logo in args['logos']];save(draft,args);self.assertEqual(load(self.store)['name'],'Organization');self.assertEqual((self.store.state/'wti/WebContent/WTI-UI/assets/lcpc-branding/participant-identity.json').read_bytes(),old)
 def test_unexpected_fields_and_invalid_text_or_slots_rejected(self):
  for change in [{'name':'bad\nname'},{'externalUrl':'https://evil.test'},{'name':''}]:
   args=self.args();args.update(change)
   with self.assertRaises(Error):save(self.store,args)
  args=self.args();args['logos'][1]['id']='pc2'
  with self.assertRaises(Error):save(self.store,args)
 def test_colors_are_scoped_inherited_and_cannot_change_semantic_colors(self):
  dashboard=dashboard_public(self.store);args=self.args();args['colors']={**THEME_DEFAULT,'primaryColor':'#405060','headerColor':'#243647'};save(self.store,args)
  data=json.loads((self.store.state/'participant-resources/identity.json').read_text());self.assertEqual(data['colors']['primaryColor'],'#405060');self.assertEqual(dashboard_public(self.store),dashboard)
  css=(self.store.state/'wti/WebContent/WTI-UI/assets/lcpc-branding/participant-theme-values.css').read_text();self.assertIn('--team-primary:#405060;',css);self.assertNotIn('accepted',css);self.assertNotIn('balloon',css)
  for value in ['red','url(javascript:bad)','#000000;display:none']:
   args=self.args();args['colors']['headerColor']=value
   with self.assertRaises(Error):save(self.store,args)
  args=self.args();args['colors']['textColor']=args['colors']['surfaceColor']
  with self.assertRaises(Error):save(self.store,args)
 def test_existing_identity_without_colors_receives_safe_defaults(self):
  old=load(self.store);del old['colors']
  with self.store.db() as db:db.execute("INSERT OR REPLACE INTO settings VALUES('participant.identity',?)",(json.dumps(old),))
  self.assertEqual(load(self.store)['colors'],THEME_DEFAULT)
if __name__=='__main__':unittest.main()
