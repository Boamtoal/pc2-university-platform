/* Public presentation only. Semantic verdict colors and balloon colors are independent. */
(function(root){
 'use strict';
 const names={headerColor:'team-navy',primaryColor:'team-primary',accentColor:'team-accent',activeColor:'team-active',hoverColor:'team-menu-hover',rowHoverColor:'team-hover',backgroundColor:'team-background',surfaceColor:'team-surface',textColor:'team-text',focusColor:'team-focus'};
 const defaults={headerColor:'#102b47',primaryColor:'#173f68',accentColor:'#eab746',activeColor:'#244664',hoverColor:'#244664',rowHoverColor:'#edf3f9',backgroundColor:'#f3f6fa',surfaceColor:'#ffffff',textColor:'#172d48',focusColor:'#eab746'};
 function validate(colors){if(!colors||Object.keys(colors).length!==Object.keys(names).length||Object.keys(names).some(k=>!/^#[0-9a-f]{6}$/i.test(colors[k]||'')))throw new Error('Invalid participant theme');return colors;}
 function foreground(color){const rgb=[1,3,5].map(i=>parseInt(color.slice(i,i+2),16)/255),lum=rgb.reduce((n,v,i)=>n+[.2126,.7152,.0722][i]*(v<=.04045?v/12.92:((v+.055)/1.055)**2.4),0);return lum<.179?'#ffffff':'#111827';}
 function apply(colors,element=document.documentElement){validate(colors);for(const [key,name] of Object.entries(names))element.style.setProperty('--'+name,colors[key]);for(const [name,key] of [['header','headerColor'],['primary','primaryColor'],['active','activeColor'],['menu-hover','hoverColor'],['hover','rowHoverColor']])element.style.setProperty('--team-on-'+name,foreground(colors[key]));element.style.setProperty('--team-muted',colors.textColor);}
 const api={validate,apply,defaults};if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.LCPCParticipantTheme=api;
})(typeof globalThis!=='undefined'?globalThis:this);
