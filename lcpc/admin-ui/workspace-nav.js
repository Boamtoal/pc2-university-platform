(() => {
 'use strict';
 const sections=[
  ['overview','overview','Overview','Workspace'],['contests','contests','Contests','Workspace'],
  ['problems','problems','Problems','Competition'],['resources','resources','Resources','Competition'],['teams','teams','Teams & Accounts','Competition'],['runs','runs','Submissions','Competition'],['clarifications','clarifications','Clarifications','Competition'],
  ['scoreboard','scoreboard','Scoreboard & Awards','Results'],
  ['judging','judging','Judging','Administration'],['controls','controls','Contest Controls','Administration'],['exports','exports','Exports & Backups','Administration'],['system','system','System','Administration'],['security','security','Security & Logs','Administration'],['account','account','My Account','Administration'],['guide','guide','User Guide','Help & Credits'],['about','about','About','Help & Credits']
 ];
 // A native capability has one home. Problem configuration opens from its problem row.
 const views={
  contests:[['main','Contests'],['profiles','Profile metadata'],['playback','Playback'],['reset','Reset & recovery']],
  problems:[['main','Problems'],['languages','Languages'],['tests','Private judge data'],['inputValidation','Validation results']],
  teams:[['main','Teams'],['activity','Participant activity','local'],['team-connections','Team connections','local'],['accounts','PC² accounts & permissions'],['groups','Groups & divisions'],['imports','Generate & import']],
  runs:[['main','Submissions'],['runs','Manage submissions'],['compare','Compare source'],['submit','Submit for a team']],
  clarifications:[['main','Questions & announcements'],['categories','Categories'],['clarifications','Manage clarifications']],
  scoreboard:[['main','Live Scoreboard'],['public-scoreboard','Public Scoreboard','local'],['scoring','Scoring rules'],['finalization','Medals & certification'],['deliveries','Balloon delivery'],['balloons','Balloon services']],
  judging:[['main','Judging workflow'],['autojudges','Judge clients'],['judgements','Verdict definitions'],['notifications','Verdict notifications']],
  controls:[['main','Clock & schedule'],['contest','Display & advanced settings'],['clocks','Site clocks']],
  exports:[['main','Reports & backups'],['learning-reports','Team Learning Reports','local'],['reports','Native reports']],
  system:[['participant-test','Participant test & access','local'],['remote-access','Remote dashboard access','local'],['dashboard-branding','Dashboard identity','local'],['participant-identity','Participant identity','local'],['sites','Sites'],['connections','Connections'],['eventfeeds','Event feeds'],['shadow','Shadow CCS'],['plugins','Java plugins'],['logs','Service logs'],['coverage','Supported features']]
 };
 const home={problems:'problems'};
 for(const [page,items] of Object.entries(views))for(const [view,,kind] of items)if(view!=='main'&&kind!=='local')home[view]=page;
 function available(page,owner){return (views[page]||[]).filter(([view])=>view==='main'||owner);}
 function current(page,remembered,owner){const items=available(page,owner);return items.some(([view])=>view===remembered)?remembered:items[0]?.[0]||'main';}
 const icons={
  overview:'<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
  contests:'<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M7 3v4m10-4v4M3 11h18m-13 4h2m4 0h2m-8 3h2"/>',
  problems:'<path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9Zm0 0v6h6M9 12l-3 3 3 3m6-6 3 3-3 3"/>',
  resources:'<path d="M3 7V5a2 2 0 0 1 2-2h5l2 3h7a2 2 0 0 1 2 2v1M3 7h16a2 2 0 0 1 2 2l-2 10H3Z"/>',
  teams:'<circle cx="9" cy="7" r="3"/><path d="M3 21v-3a6 6 0 0 1 12 0v3m2-17a3 3 0 0 1 0 6m2 11v-3a6 6 0 0 0-2-4"/>',
  runs:'<path d="m22 2-7 20-4-9L2 9Zm0 0L11 13"/>',
  clarifications:'<path d="M21 11a7 7 0 0 1-7 7H7l-5 4V9a7 7 0 0 1 7-7h5a7 7 0 0 1 7 7Z"/><path d="M7 8h9M7 12h6"/>',
  scoreboard:'<path d="M7 3h10v6a5 5 0 0 1-10 0Zm0 2H3v2a4 4 0 0 0 4 4m10-6h4v2a4 4 0 0 1-4 4m-5 3v5m-5 2h10m-8-2h6"/>',
  judging:'<path d="m13 3 8 8-3 3-8-8Zm-9 9 8 8-3 3-8-8Zm4 4 7-7M4 21h16"/>',
  controls:'<circle cx="12" cy="13" r="8"/><path d="M12 9v4l3 2M9 2h6m-3 0v3m6 2 2-2"/>',
  exports:'<path d="M12 3v12m-5-5 5 5 5-5M4 16v4a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-4"/>',
  system:'<rect x="3" y="3" width="18" height="7" rx="2"/><rect x="3" y="14" width="18" height="7" rx="2"/><path d="M7 6.5h.01M7 17.5h.01M11 6.5h6M11 17.5h6"/>',
  security:'<path d="m12 2 8 4v6c0 5-8 10-8 10S4 17 4 12V6Zm-4 9 3 3 5-5"/>',
  guide:'<path d="M12 5c-3-2-7-2-10-1v15c3-1 7-1 10 1 3-2 7-2 10-1V4c-3-1-7-1-10 1Zm0 0v15"/>',
  about:'<circle cx="12" cy="12" r="9"/><path d="M12 11v6m0-10h.01"/>',
  account:'<circle cx="12" cy="8" r="4"/><path d="M4 22v-2a8 8 0 0 1 16 0v2"/>'
 };
 function icon(name){return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">'+(icons[name]||icons.overview)+'</svg>';}
 const api={sections,views,home,available,current,icon};
 if(typeof module!=='undefined'&&module.exports)module.exports=api;else window.LCPCNavigation=api;
})();
