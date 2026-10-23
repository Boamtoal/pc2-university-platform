import sys,tempfile,unittest,zlib,struct,base64,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core import Store,Error
from dashboard_branding import public,save,image,theme,load

def png():
 def chunk(t,b):return struct.pack('>I',len(b))+t+b+struct.pack('>I',zlib.crc32(t+b)&0xffffffff)
 return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',1,1,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(b'\x00\xff\x00\x00'))+chunk(b'IEND',b'')
class Branding(unittest.TestCase):
 def setUp(self):self.temp=tempfile.TemporaryDirectory();self.store=Store(self.temp.name)
 def tearDown(self):self.temp.cleanup()
 def test_identity_logo_and_theme_persist_without_participant_changes(self):
  participant=Path(self.temp.name)/'participant-resources';participant.mkdir();sentinel=participant/'branding.txt';sentinel.write_text('unchanged');current=public(self.store);value=save(self.store,{'version':current['version'],'name':'University Fixture','subtitle':'Organizer','primaryColor':'#ffffff','sidebarColor':'#881133','logo':base64.b64encode(png()).decode()});self.assertTrue(value['customLogo']);self.assertNotIn('base64',str(value));self.assertIn('--identity-on-primary:#111827',theme(self.store));self.assertEqual(public(Store(self.temp.name))['name'],'University Fixture');self.assertEqual(sentinel.read_text(),'unchanged')
  with self.assertRaises(Error):save(self.store,{'version':current['version'],'reset':True})
  self.assertEqual(save(self.store,{'version':value['version'],'reset':True})['name'],'LCPC OMU')
 def test_active_images_css_and_corruption_are_rejected(self):
  for raw in [b'<svg onload="alert(1)"></svg>',png()+b'<script>',png()[:-1]]:
   with self.assertRaises(Error):image(base64.b64encode(raw).decode())
  args={**public(self.store),'primaryColor':'red;url(https://example.org)'};args={k:v for k,v in args.items() if k in ('version','name','subtitle','primaryColor','sidebarColor')}
  with self.assertRaises(Error):save(self.store,args)
 def test_active_indicator_persists_validates_and_resets_independently(self):
  current=public(self.store);args={k:current[k] for k in ('version','name','subtitle','primaryColor','sidebarColor')}
  value=save(self.store,{**args,'activeIndicatorColor':'#22CC88'})
  self.assertEqual(public(Store(self.temp.name))['activeIndicatorColor'],'#22cc88')
  self.assertEqual(value['primaryColor'],current['primaryColor']);self.assertEqual(value['sidebarColor'],current['sidebarColor'])
  self.assertIn('--identity-active-indicator:#22cc88',theme(self.store));self.assertIn('border-left-color:var(--identity-active-indicator)',theme(self.store))
  for bad in ('yellow','#abc','red;url(https://example.org)',None,123):
   with self.assertRaises(Error):save(self.store,{**args,'version':value['version'],'activeIndicatorColor':bad})
  self.assertEqual(save(self.store,{'version':value['version'],'reset':True})['activeIndicatorColor'],'#eab746')
 def test_previous_saved_identity_gets_indicator_default_without_losing_settings(self):
  previous={**load(self.store),'name':'Existing University','sidebarColor':'#223344'};previous.pop('activeIndicatorColor')
  with self.store.db() as db:db.execute("INSERT OR REPLACE INTO settings VALUES('dashboard.branding',?)",(json.dumps(previous),))
  value=public(self.store);self.assertEqual(value['activeIndicatorColor'],'#eab746');self.assertEqual(value['name'],'Existing University');self.assertEqual(value['sidebarColor'],'#223344')
 def test_identity_interaction_palette_does_not_override_semantic_colors(self):
  current=public(self.store);args={k:current[k] for k in ('version','name','subtitle','primaryColor','sidebarColor')}
  palette={'activeSectionColor':'#892233','menuHoverColor':'#446611','rowHoverColor':'#111122','focusColor':'#44bbdd'}
  value=save(self.store,{**args,**palette});css=theme(self.store)
  for key,color in palette.items():self.assertEqual(public(Store(self.temp.name))[key],color)
  for name,color in [('active-section','#892233'),('menu-hover','#446611'),('row-hover','#111122'),('focus','#44bbdd')]:self.assertIn('--identity-'+name+':'+color,css)
  self.assertIn('--identity-on-row-hover:#ffffff',css)
  for selector in ['.danger','.success','.accepted','.rejected','.pending','.error','.warning']:self.assertNotIn(selector,css)
  for key in palette:
   with self.assertRaises(Error):save(self.store,{**args,'version':value['version'],key:'red;url(https://example.org)'})
  reset=save(self.store,{'version':value['version'],'reset':True});self.assertEqual(reset['rowHoverColor'],'#eaf2fa')
if __name__=='__main__':unittest.main()
