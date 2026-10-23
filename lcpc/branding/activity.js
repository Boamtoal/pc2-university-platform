/* Local contest diagnostics: structured events only, never form values or source contents. */
(() => {
 'use strict';
 if(globalThis.LCPCActivity)return;
 const originalFetch=globalThis.fetch?.bind(globalThis),NativeSocket=globalThis.WebSocket;
 if(!originalFetch)return;
 const tokenPattern=/^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i;
 const sessionKey='lcpc.team-session.v1',clientKey='lcpc.activity-tab.v1';
 const makeClient=()=>Array.from(crypto.getRandomValues(new Uint8Array(16)),v=>v.toString(16).padStart(2,'0')).join('');
 let client;try{client=sessionStorage.getItem(clientKey);if(!/^[a-f0-9]{32}$/.test(client||'')){client=makeClient();sessionStorage.setItem(clientKey,client);}}catch(_){client=makeClient();}

 let queue=[],sending=false,lastBeat=0,timer,lastPage='',offline=false,cookieSession=false;
 const recent=new Map();let submissionAttempt=null;
 function submissionKey(body){const identity=auth()?.token||'';if(!submissionAttempt||submissionAttempt.body!==body||submissionAttempt.identity!==identity)submissionAttempt={body,identity,key:makeClient()};return submissionAttempt.key;}
 function submissionFinished(key,status){if(submissionAttempt?.key===key&&status>=200&&status<500)submissionAttempt=null;}
 const platform=/Android/.test(navigator.userAgent)?'Android':/iPhone|iPad/.test(navigator.userAgent)?'iOS':/Windows/.test(navigator.userAgent)?'Windows':/Mac/.test(navigator.userAgent)?'macOS':/Linux/.test(navigator.userAgent)?'Linux':'Other';
 const browser=/Edg\//.test(navigator.userAgent)?'Edge':/Firefox\//.test(navigator.userAgent)?'Firefox':/Chrome\//.test(navigator.userAgent)?'Chrome':/Safari\//.test(navigator.userAgent)?'Safari':'Other';
 function auth(){try{const s=JSON.parse(sessionStorage.getItem(sessionKey));return s&&tokenPattern.test(s.token)&&/^team[1-9][0-9]*$/.test(s.username)?s:null;}catch(_){return null;}}
 function page(){if(location.pathname.startsWith('/instructions'))return 'instructions';if(location.pathname.startsWith('/problems'))return 'resources';const m=location.hash.match(/^#\/(login|runs|clarifications|options|scoreboard)(?:[/?]|$)/);return m?m[1]:'unknown';}
 function endpoint(url){try{const u=new URL(typeof url==='string'?url:url.url,location.href);if(u.origin!==location.origin)return null;const p=u.pathname.replace(/\/$/,'');if(!p.startsWith('/api/'))return null;const known={'/api/teams/activity':'activity','/api/teams/login':'login','/api/teams/logout':'logout','/api/teams/run':'runs','/api/teams/clarification':'clarifications','/api/teams/options':'options','/api/teams/resources':'resources','/api/teams/resources-session':'resource_session','/api/teams/result-notifications':'result_notifications'};if(known[p])return known[p];for(const n of ['problems','languages','judgements','clarifications'])if(p==='/api/contest/'+n||p==='/api/contests/'+n)return n;if(/clock|isContestRunning/i.test(p))return 'clock';return 'other';}catch(_){return null;}}
 const errorType=value=>['Error','TypeError','ReferenceError','SyntaxError','RangeError','URIError','EvalError'].includes(value?.name)?value.name:'Unknown';
 function emit(event,details={},dedupe=false){
  if(dedupe){const key=event+':'+details.endpoint+':'+details.status+':'+details.closeCode;if(Date.now()-(recent.get(key)||0)<10000)return;recent.set(key,Date.now());if(recent.size>100)recent.delete(recent.keys().next().value);}
  queue.push({session:auth()?.token||(cookieSession?'cookie':''),event,details:{...details,page:page(),platform,browser,clientAt:Date.now()/1000}});if(queue.length>100)queue.shift();if(!timer)timer=setTimeout(()=>{timer=null;flush();},1500);
 }
 async function flush(keepalive=false){
  if(sending||!queue.length||navigator.onLine===false)return;
  const session=auth(),identity=session?.token||(cookieSession?'cookie':''),prelogin=new Set(['page.open','page.navigate','browser.error','browser.rejection','request.failed','action.clicked','form.submitted']);
  queue=queue.filter(e=>!e.session?prelogin.has(e.event):e.session===identity);if(!queue.length)return;
  const batch=queue.splice(0,20);sending=true;
  try{const response=await originalFetch('/api/teams/activity',{method:'POST',credentials:'same-origin',cache:'no-store',keepalive,headers:{'Content-Type':'application/json',...(session?{team_id:session.token}:{})},body:JSON.stringify({client,reportedTeam:session?.username||'',events:batch.map(({event,details})=>({event,details}))})});
   if(response.status===401)cookieSession=false;
   if(response.status>=500||response.status===429)queue=[...batch,...queue].slice(-100);
  }catch(_){queue=[...batch,...queue].slice(-100);}finally{sending=false;}
 }
 function completed(target,method,status,started,rid){if(!target||target==='activity')return;if((status===401||status===403)&&!auth()&&!cookieSession&&['resource_session','result_notifications'].includes(target))return;emit(status>=200&&status<400?'request.completed':'request.failed',{endpoint:target,method:String(method||'GET').toUpperCase(),status,durationMs:Math.round(performance.now()-started),requestId:/^[a-f0-9]{16,32}$/.test(rid||'')?rid:''},status===0);}
 globalThis.fetch=function(input,options){const target=endpoint(input);let retryKey='';if(target==='runs'&&String(options?.method).toUpperCase()==='POST'&&typeof options.body==='string'){retryKey=submissionKey(options.body);options={...options,headers:{...options.headers,'Idempotency-Key':retryKey}};}const started=performance.now(),method=options?.method||input?.method||'GET';return originalFetch(input,options).then(response=>{if(retryKey)submissionFinished(retryKey,response.status);completed(target,method,response.status,started,response.headers.get('X-LCPC-Request-ID'));return response;},error=>{completed(target,method,0,started,'');throw error;});};
 const open=XMLHttpRequest.prototype.open,send=XMLHttpRequest.prototype.send;
 XMLHttpRequest.prototype.open=function(method,url,...rest){this._lcpcActivity={endpoint:endpoint(url),method};return open.call(this,method,url,...rest);};
 XMLHttpRequest.prototype.send=function(body){const request=this._lcpcActivity;if(request?.endpoint&&request.endpoint!=='activity'){const started=performance.now();let retryKey='';if(request.endpoint==='runs'&&String(request.method).toUpperCase()==='POST'&&typeof body==='string'){retryKey=submissionKey(body);this.setRequestHeader('Idempotency-Key',retryKey);}this.addEventListener('loadend',()=>{if(retryKey)submissionFinished(retryKey,this.status);let rid='';try{rid=this.getResponseHeader('X-LCPC-Request-ID')||'';}catch(_){}completed(request.endpoint,request.method,this.status,started,rid);},{once:true});}return send.call(this,body);};
 if(NativeSocket){
  const ObservedSocket=new Proxy(NativeSocket,{construct(Target,args,newTarget){const socket=Reflect.construct(Target,args,newTarget===ObservedSocket?Target:newTarget);try{const u=new URL(String(args[0]),location.href);if(u.host===location.host&&/^\/websocket\/WTISocket\/[0-9a-f-]{36}$/i.test(u.pathname)){socket.addEventListener('open',()=>emit('socket.open'));socket.addEventListener('error',()=>emit('socket.error',{},true));socket.addEventListener('close',e=>emit('socket.close',{closeCode:e.code,normalClose:e.code===1000},e.code!==1000));}}catch(_){}return socket;}});globalThis.WebSocket=ObservedSocket;
 }
 addEventListener('error',e=>{let script='';try{script=new URL(e.filename).pathname.split('/').pop();}catch(_){}emit('browser.error',{errorType:e.error?errorType(e.error):'ResourceError',script:/^[A-Za-z0-9_.-]{1,100}\.js$/.test(script)?script:'',line:e.lineno||0,column:e.colno||0},true);},true);
 addEventListener('unhandledrejection',e=>emit('browser.rejection',{errorType:errorType(e.reason)},true));
 addEventListener('offline',()=>{offline=true;emit('network.offline',{},true);});
 addEventListener('online',()=>{emit('network.online');offline=false;flush();});
 addEventListener('hashchange',()=>{const next=page();if(next!==lastPage){lastPage=next;emit('page.navigate');}});
 document.addEventListener('visibilitychange',()=>emit('page.visibility',{visibility:document.visibilityState}));
 addEventListener('pagehide',()=>{emit('page.close');flush(true);});
 document.addEventListener('lcpc-auth-change',()=>{if(auth())emit('session.restored');flush();});
 document.addEventListener('change',e=>{if(e.target instanceof HTMLInputElement&&e.target.type==='file'){const files=Array.from(e.target.files||[]);const ext=files[0]?.name.match(/\.[^.]+$/)?.[0]?.toLowerCase()||'other';emit('file.selected',{fileCount:files.length,bytes:files.reduce((n,f)=>n+f.size,0),extension:['.cpp','.cc','.c','.py','.java'].includes(ext)?ext:'other'});}},true);
 document.addEventListener('submit',()=>emit('form.submitted'),true);
 document.addEventListener('click',e=>{const button=e.target instanceof Element?e.target.closest('button,a,[role="button"]'):null;if(!button)return;const actions={'login':'login','log in':'login','logout':'logout','sign out':'logout','submit':'submit','submit problem':'submit_problem','send':'clarification','save':'save','clear filters':'clear_filters','download':'download'};const action=actions[(button.textContent||'').trim().toLowerCase()];if(action)emit('action.clicked',{action});},true);
 if(location.pathname.startsWith('/problems')||location.pathname.startsWith('/instructions'))originalFetch('/api/teams/resources-session',{credentials:'same-origin',cache:'no-store'}).then(r=>{cookieSession=r.ok;if(cookieSession)emit('session.restored');}).catch(()=>{});
 lastPage=page();emit('page.open');
 setInterval(()=>{if((auth()||cookieSession)&&Date.now()-lastBeat>=10000){lastBeat=Date.now();emit('heartbeat');}if(!offline)flush();},5000);
 globalThis.LCPCActivity={flush,get authenticated(){return !!(auth()||cookieSession);}};
})();
