(function(){
'use strict';
var script=document.currentScript;
var scriptUrl=script&&script.src?script.src:'';
var configUrl=scriptUrl?scriptUrl.replace(/media-studio\.js(?:\?.*)?$/,'analytics-config.json'):'';
var apiBase='';
function esc(v){return String(v==null?'':v).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
function loadConfig(){if(window.MERCY_API_BASE){apiBase=String(window.MERCY_API_BASE).replace(/\/$/,'');return Promise.resolve();}return fetch(configUrl,{cache:'no-store'}).then(function(r){if(!r.ok)throw new Error('config_failed');return r.json();}).then(function(c){apiBase=String(c.mercy_api_base||'').replace(/\/$/,'');if(!apiBase)throw new Error('api_missing');});}
function get(path){return fetch(apiBase+path,{cache:'no-store'}).then(function(r){if(!r.ok)throw new Error('request_failed');return r.json();});}
function youtubeId(v){if(!v)return '';var m=String(v).match(/(?:youtu\.be\/|[?&]v=|\/embed\/|\/live\/)([A-Za-z0-9_-]{6,})/);if(m)return m[1];if(/^[A-Za-z0-9_-]{6,}$/.test(v))return v;return '';}
function player(item){var id=item.youtube_id||youtubeId(item.video_url||item.youtube_video_url);if(id)return '<div class="media-player"><iframe loading="lazy" src="https://www.youtube-nocookie.com/embed/'+esc(id)+'?rel=0" title="'+esc(item.title||'Video')+'" allow="accelerometer;autoplay;clipboard-write;encrypted-media;gyroscope;picture-in-picture;web-share" allowfullscreen></iframe></div>';if(item.video_url)return '<div class="media-player"><video controls preload="metadata" src="'+esc(item.video_url)+'"></video></div>';return '';}
function formatDate(v){if(!v)return '';try{return new Date(v).toLocaleString();}catch(e){return v;}}

function renderCourse(){
 var root=document.querySelector('[data-course-video-library]');if(!root)return Promise.resolve();
 var params=new URLSearchParams(location.search),initial=params.get('course')||'mariology';
 var select=document.querySelector('[data-course-filter]');
 var names={'theology':'Theology','philosophy':'Philosophy','logos':'Sacred Scripture — Logos','pneumatology':'Pneumatology','charismatic-renewal':'Catholic Charismatic Renewal','angelology-demonology':'Angelology & Demonology','patristics':'Patristics','church-fathers':'Church Fathers','magisterium':'Councils & Magisterium','canon-law':'Canon Law','spiritual-theology':'Spiritual Theology','apologetics':'Apologetics','mariology':'Mariology','church-history':'Church History','formation':'Formation'};
 if(select&&!select.options.length){Object.keys(names).forEach(function(k){var o=document.createElement('option');o.value=k;o.textContent=names[k];select.appendChild(o);});select.value=names[initial]?initial:'mariology';select.addEventListener('change',function(){history.replaceState(null,'','?course='+encodeURIComponent(select.value));loadCourse(select.value);});}
 function loadCourse(key){root.innerHTML='<p class="media-empty">Loading course videos…</p>';get('/api/content/course-videos?course='+encodeURIComponent(key)).then(function(d){var items=d.items||[];root.innerHTML='';if(!items.length){root.innerHTML='<p class="media-empty">No admin-published videos have been added to this course yet.</p>';return;}items.forEach(function(v){var a=document.createElement('article');a.className='media-card';a.innerHTML=player(v)+'<div class="media-card-body"><div class="media-meta">'+esc(v.topic||names[key]||key)+(v.lesson?' · '+esc(v.lesson):'')+'</div><h2>'+esc(v.title)+'</h2><p>'+esc(v.description||'')+'</p><div class="media-details">'+(v.speaker?'<span><strong>Speaker:</strong> '+esc(v.speaker)+'</span>':'')+(v.source_name?'<span><strong>Source:</strong> '+esc(v.source_name)+'</span>':'')+(v.doctrinal_classification?'<span><strong>Classification:</strong> '+esc(v.doctrinal_classification)+'</span>':'')+'</div></div>';root.appendChild(a);});}).catch(function(){root.innerHTML='<p class="media-empty">Course videos are temporarily unavailable.</p>';});}
 loadCourse(select?select.value:initial);
 return Promise.resolve();
}

function renderHomiletics(){
 var root=document.querySelector('[data-homiletics-library]');if(!root)return Promise.resolve();
 root.innerHTML='<p class="media-empty">Loading homiletics…</p>';
 return get('/api/content/homiletics').then(function(d){var items=d.items||[];root.innerHTML='';if(!items.length){root.innerHTML='<p class="media-empty">No homiletic videos have been published yet.</p>';return;}items.forEach(function(v){var a=document.createElement('article');a.className='media-card';a.innerHTML=player(v)+'<div class="media-card-body"><div class="media-meta">'+esc(v.occasion||'Homiletics')+(v.preached_at?' · '+esc(formatDate(v.preached_at)):'')+'</div><h2>'+esc(v.title)+'</h2>'+(v.speaker?'<p><strong>'+esc(v.speaker)+'</strong></p>':'')+(v.scripture_reference?'<p class="scripture-ref">'+esc(v.scripture_reference)+'</p>':'')+'<p>'+esc(v.summary||'')+'</p>'+(v.body?'<details><summary>Teaching / preaching notes</summary><div class="homiletic-notes">'+esc(v.body).replace(/\n/g,'<br>')+'</div></details>':'')+'</div>';root.appendChild(a);});}).catch(function(){root.innerHTML='<p class="media-empty">Homiletics are temporarily unavailable.</p>';});
}

function renderLive(){
 var root=document.querySelector('[data-live-page]');var home=document.querySelector('[data-live-home]');if(!root&&!home)return Promise.resolve();
 return get('/api/content/live').then(function(d){var current=d.current;
   function liveHtml(compact){if(!current)return compact?'':'<div class="media-empty">There is no scheduled live broadcast at the moment.</div>';var status=String(current.status||'scheduled').toUpperCase();var id=current.youtube_id||youtubeId(current.youtube_video_url);var video=id?'<div class="media-player"><iframe src="https://www.youtube-nocookie.com/embed/'+esc(id)+'?autoplay=0&rel=0" title="'+esc(current.title)+'" allow="accelerometer;autoplay;clipboard-write;encrypted-media;gyroscope;picture-in-picture;web-share" allowfullscreen></iframe></div>':'';return '<div class="live-card"><div class="live-badge '+(current.status==='live'?'is-live':'')+'">'+(current.status==='live'?'● LIVE':esc(status))+'</div>'+video+'<div class="media-card-body"><h2>'+esc(current.title)+'</h2><p>'+esc(current.description||'')+'</p><div class="media-details">'+(current.speaker?'<span><strong>Speaker:</strong> '+esc(current.speaker)+'</span>':'')+(current.scheduled_start?'<span><strong>Scheduled:</strong> '+esc(formatDate(current.scheduled_start))+'</span>':'')+'</div></div></div>';}
   if(root){root.innerHTML=liveHtml(false);var recent=document.querySelector('[data-live-recent]');if(recent){recent.innerHTML='';(d.recent||[]).forEach(function(v){var x=document.createElement('article');x.className='media-card';x.innerHTML=player(v)+'<div class="media-card-body"><h3>'+esc(v.title)+'</h3><div class="media-meta">'+esc(formatDate(v.scheduled_start||v.created_at))+'</div></div>';recent.appendChild(x);});}}
   if(home){if(current){home.hidden=false;home.innerHTML=liveHtml(true);}else home.hidden=true;}
 }).catch(function(){if(root)root.innerHTML='<p class="media-empty">Live status is temporarily unavailable.</p>';if(home)home.hidden=true;});
}

loadConfig().then(function(){renderCourse();renderHomiletics();renderLive();setInterval(function(){if(!document.hidden)renderLive();},30000);}).catch(function(){document.querySelectorAll('[data-course-video-library],[data-homiletics-library],[data-live-page]').forEach(function(x){x.innerHTML='<p class="media-empty">The media service is not configured.</p>';});});
})();