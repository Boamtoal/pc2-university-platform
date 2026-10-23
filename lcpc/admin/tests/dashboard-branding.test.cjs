const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
test('identity palette previews every interaction color and submits all colors without semantic settings',async()=>{
 const palette={primaryColor:'#173f68',sidebarColor:'#102b47',activeSectionColor:'#892233',activeIndicatorColor:'#22cc88',menuHoverColor:'#446611',rowHoverColor:'#111122',focusColor:'#44bbdd'};
 const data={name:'Fixture University',subtitle:'Organizer',...palette,customLogo:false,logoUrl:'/fixture.png',version:'fixture'};
 const styles={},listeners={},logo={},text={},theme={};let posted,html='';
 const preview={style:{setProperty(k,v){styles[k]=v;}},querySelector(s){return s==='img'?logo:text;}};
 const elements=Object.fromEntries(Object.entries(data).map(([k,v])=>[k,{value:v}]));elements.logo={files:[],addEventListener(){}};elements.resetLogo={checked:false};
 const form={elements,querySelector(s){return s==='.identity-preview'?preview:{addEventListener(){}};},addEventListener(t,fn){listeners[t]=fn;}};
 const editor={set innerHTML(v){html=v;}};const root={isConnected:true,querySelector(s){return s==='form'?form:editor;}};
 const document={querySelectorAll:()=>[],querySelector:()=>theme};const sandbox={window:{},document,URL:{}};
 vm.runInNewContext(fs.readFileSync('lcpc/admin-ui/dashboard-branding.js','utf8'),sandbox);
 const ctx={api:async(path,args)=>{assert.equal(path,'dashboard-branding');if(args)posted=args;return data;},notice(){}};
 await sandbox.window.LCPCDashboardBranding.mount(root,ctx);
 for(const [key,value] of Object.entries(palette)){assert.match(html,new RegExp('name="'+key+'"'));assert.equal(styles['--preview-'+key],value);}
 assert.equal(styles['--preview-on-rowHoverColor'],'#ffffff');assert.match(html,/Success, error, warning and destructive action colors stay fixed/);
 await listeners.submit({preventDefault(){}});
 for(const [key,value] of Object.entries(palette))assert.equal(posted[key],value);
 assert.ok(!Object.keys(posted).some(k=>/success|danger|error|warning/i.test(k)));
});
