(function(){
'use strict';
var script=document.currentScript;
var scriptUrl=script&&script.src?script.src:'';
var configUrl=scriptUrl?scriptUrl.replace(/live-site\.js(?:\?.*)?$/,'analytics-config.json'):'';
var apiBase='';
var REFRESH_MS=30000;
var inFlight=false;
var lastRun=0;
var baselines=new Map();
var appliedKeys=new Set();

function pagePath(){var p=location.pathname;var prefix='/mercy-the-last-hope-of-salvation';if(p.indexOf(prefix)===0)p=p.slice(prefix.length)||'/';if(p==='/'||/\/$/.test(p))p=(p==='/'?'':p)+'index.html';if(p.charAt(0)!=='/')p='/'+p;return p;}
function loadConfig(){if(window.MERCY_API_BASE){apiBase=String(window.MERCY_API_BASE).replace(/\/$/,'');return Promise.resolve();}if(!configUrl)return Promise.reject(new Error('config_missing'));return fetch(configUrl,{cache:'no-store'}).then(function(r){if(!r.ok)throw new Error('config_failed');return r.json();}).then(function(c){apiBase=String(c.mercy_api_base||'').replace(/\/$/,'');if(!apiBase)throw new Error('api_missing');});}
function keyFor(item){return String(item.selector||'')+'|'+String(item.field||'');}
function readValue(el,field){if(field==='html')return el.innerHTML;if(field==='href'&&el.tagName==='A')return el.getAttribute('href')||'';if(field==='src'&&el.tagName==='IMG')return el.getAttribute('src')||'';if(field==='alt'&&el.tagName==='IMG')return el.getAttribute('alt')||'';return null;}
function writeValue(el,field,value){if(field==='html')el.innerHTML=value;else if(field==='href'&&el.tagName==='A')el.setAttribute('href',value);else if(field==='src'&&el.tagName==='IMG')el.setAttribute('src',value);else if(field==='alt'&&el.tagName==='IMG')el.setAttribute('alt',value);}
function applyOverrides(items){var order={html:0,href:1,src:1,alt:1};items=(items||[]).slice().sort(function(a,b){return (order[a.field]??9)-(order[b.field]??9)||String(a.selector).length-String(b.selector).length;});var currentKeys=new Set();items.forEach(function(item){try{var el=document.querySelector(item.selector);if(!el)return;var key=keyFor(item);currentKeys.add(key);if(!baselines.has(key)){var initial=readValue(el,item.field);if(initial!==null)baselines.set(key,{selector:item.selector,field:item.field,value:initial});}writeValue(el,item.field,item.value);}catch(e){}});appliedKeys.forEach(function(key){if(currentKeys.has(key))return;var base=baselines.get(key);if(!base)return;try{var el=document.querySelector(base.selector);if(el)writeValue(el,base.field,base.value);}catch(e){}});appliedKeys=currentKeys;}
function refreshOverrides(){return fetch(apiBase+'/api/content/blocks?path='+encodeURIComponent(pagePath()),{cache:'no-store'}).then(function(r){if(!r.ok)throw new Error('blocks_failed');return r.json();}).then(function(j){applyOverrides(Array.isArray(j.overrides)?j.overrides:[]);});}
function refreshCampaignStats(){var joined=document.querySelector('[data-campaign-joined-count]'),completed=document.querySelector('[data-campaign-completed-count]');if(!joined&&!completed)return Promise.resolve();return fetch(apiBase+'/api/save-one-soul/stats',{cache:'no-store'}).then(function(r){if(!r.ok)throw new Error('stats_failed');return r.json();}).then(function(s){if(joined)joined.textContent=Number(s.joined||0).toLocaleString();if(completed)completed.textContent=Number(s.completed||0).toLocaleString();});}
function refresh(force){var now=Date.now();if(inFlight)return;if(!force&&now-lastRun<2500)return;lastRun=now;inFlight=true;Promise.allSettled([refreshOverrides(),refreshCampaignStats()]).then(function(){document.dispatchEvent(new CustomEvent('mercy:live-refresh'));}).finally(function(){inFlight=false;});}
function start(){refresh(true);setInterval(function(){if(!document.hidden)refresh(false);},REFRESH_MS);window.addEventListener('focus',function(){refresh(true);});document.addEventListener('visibilitychange',function(){if(!document.hidden)refresh(true);});window.addEventListener('online',function(){refresh(true);});}

loadConfig().then(start).catch(function(){});
})();
