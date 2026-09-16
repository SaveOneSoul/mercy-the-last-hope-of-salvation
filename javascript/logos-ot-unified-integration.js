(function(){
'use strict';

var script=document.currentScript,scriptUrl=script&&script.src?script.src:'';
var configUrl=scriptUrl?scriptUrl.replace(/logos-ot-unified-integration\.js(?:\?.*)?$/,'analytics-config.json'):'';
var apiBase='',metadataLoaded=false,inFlight='';
var readiness={semitic:false,septuagint:false,catholicGreek:false,vulgate:false};
var passageHeading=document.getElementById('passageHeading');
var tabPanel=document.getElementById('logosTabPanel');
var statusEl=document.getElementById('logosStatus');

function el(tag,className,text){var node=document.createElement(tag);if(className)node.className=className;if(text!=null)node.textContent=String(text);return node;}
function clear(node){while(node&&node.firstChild)node.removeChild(node.firstChild);}
function setStatus(text,error){if(!statusEl)return;statusEl.textContent=text;statusEl.style.color=error?'#9a1729':'';}
function loadConfig(){if(window.MERCY_API_BASE){apiBase=String(window.MERCY_API_BASE).replace(/\/$/,'');return Promise.resolve();}if(!configUrl)return Promise.reject(new Error('config_missing'));return fetch(configUrl,{cache:'no-store'}).then(function(r){if(!r.ok)throw new Error('config_failed');return r.json();}).then(function(c){apiBase=String(c.mercy_api_base||'').replace(/\/$/,'');if(!apiBase)throw new Error('api_missing');});}
function optionalGet(path){return fetch(apiBase+path,{cache:'no-store'}).then(function(r){return r.json().catch(function(){return {};}).then(function(data){if(r.ok)return {ok:true,status:r.status,data:data};return {ok:false,status:r.status,detail:data.detail||'request_failed',data:data};});}).catch(function(error){return {ok:false,status:0,detail:error&&error.message||'network_error'};});}
function interlinearActive(){var button=document.querySelector('[data-logos-tab="interlinear"]');return !!(button&&button.classList.contains('active'));}
function currentReference(){return String((passageHeading&&passageHeading.textContent)||'').trim();}
function detailCode(result){var d=result&&result.detail;if(d&&typeof d==='object')return String(d.code||'');return String(d||'');}
function mappingMessage(result,label){if(!result)return label+' unavailable.';if(result.ok)return '';
  var code=detailCode(result);if(result.status===409||code.indexOf('mapping_required')>=0)return label+' is source-locked, but this chapter has a verified versification difference and is blocked until an explicit mapping is reviewed.';
  if(result.status===404)return label+' is not available for this canonical locus.';
  return label+' production endpoint is currently unavailable.';
}
function sourceBadge(text){return el('span','logos-source-badge',text);}
function addPolicy(root,title,text){var box=el('div','logos-policy');box.appendChild(el('strong','',title));box.appendChild(el('p','',text));root.appendChild(box);}

function renderEnglish(root,passage){var lane=passage&&passage.languages&&passage.languages.en||{},card=el('article','logos-language-card logos-primary-scripture');var h=el('h3','','English — Douay-Rheims 1899');h.appendChild(el('span','logos-primary-badge','Primary Catholic Bible layer'));card.appendChild(h);card.appendChild(el('p','',lane.text||'English Douay-Rheims text is unavailable for this reference.'));if(lane.source)card.appendChild(sourceBadge((lane.source.title||lane.source.id||'Douay-Rheims 1899')+(lane.source.rights?' · '+lane.source.rights:'')));root.appendChild(card);}

function renderSemitic(root,data){var section=el('section','logos-ot-source-section');section.appendChild(el('h3','','Hebrew / Aramaic — Westminster Leningrad Codex + OSHB'));section.appendChild(el('p','logos-note','Source-script text is preserved verbatim. Lemma and morphology are pinned OSHB annotations. No transliteration or English gloss is fabricated.'));var wrap=el('div','logos-interlinear-wrap'),table=el('table','logos-interlinear'),head=el('thead'),tr=el('tr');['Verse','Hebrew / Aramaic','Lemma','Morphology','Language'].forEach(function(x){tr.appendChild(el('th','',x));});head.appendChild(tr);table.appendChild(head);var body=el('tbody');(data.verses||[]).forEach(function(v){(v.tokens||[]).forEach(function(t,index){var r=el('tr');r.appendChild(el('td','',index===0?String(v.verse):''));var td=el('td','logos-script-token',t.surface||'');td.dir='rtl';r.appendChild(td);r.appendChild(el('td','',t.lemma||''));r.appendChild(el('td','',t.morphology||''));r.appendChild(el('td','',t.language==='arc'?'Aramaic':'Hebrew'));body.appendChild(r);});});table.appendChild(body);wrap.appendChild(table);section.appendChild(wrap);section.appendChild(sourceBadge('WLC surface · Public Domain; OSHB linguistic annotations · CC BY 4.0'));root.appendChild(section);}

function renderSeptuagintWitness(root,data,title){var witness=data.primary_witness||{},section=el('section','logos-ot-source-section');section.appendChild(el('h3','',title||'Greek — Septuagint (Swete)'));section.appendChild(el('p','logos-note','Greek source verse boundaries are preserved under CC BY-SA 4.0. No Greek gloss, lemma, morphology or transliteration is invented for this OT source lane.'));var wrap=el('div','logos-interlinear-wrap'),table=el('table','logos-interlinear'),head=el('thead'),tr=el('tr');['Verse / source reference','Greek source surface'].forEach(function(x){tr.appendChild(el('th','',x));});head.appendChild(tr);table.appendChild(head);var body=el('tbody');(witness.verses||[]).forEach(function(v){var r=el('tr');r.appendChild(el('td','',v.verse!=null?String(v.verse):(v.source_reference||'')));r.appendChild(el('td','logos-script-token',v.surface||''));body.appendChild(r);});table.appendChild(body);wrap.appendChild(table);section.appendChild(wrap);section.appendChild(sourceBadge((witness.witness_id||'Swete witness')+' · '+(witness.license||'CC BY-SA 4.0')));root.appendChild(section);
  if((data.parallel_witnesses||[]).length){var parallels=el('div','logos-commentary-grid');(data.parallel_witnesses||[]).forEach(function(p){var details=el('details','logos-study-card');details.appendChild(el('summary','',(p.name||p.witness_id)+' · preserved parallel witness'));var pwrap=el('div','logos-interlinear-wrap'),ptable=el('table','logos-interlinear'),pbody=el('tbody');(p.verses||[]).forEach(function(v){var rr=el('tr');rr.appendChild(el('td','',v.source_reference||''));rr.appendChild(el('td','logos-script-token',v.surface||''));pbody.appendChild(rr);});ptable.appendChild(pbody);pwrap.appendChild(ptable);details.appendChild(pwrap);parallels.appendChild(details);});root.appendChild(parallels);}
}

function renderVulgate(root,data){var section=el('section','logos-ot-source-section');section.appendChild(el('h3','','Latin — Sixto-Clementine Vulgate'));section.appendChild(el('p','logos-note','The public-domain Clementine Latin text is displayed only where its chapter/verse identities match the installed Douay-Rheims citation exactly.'));var wrap=el('div','logos-interlinear-wrap'),table=el('table','logos-interlinear'),head=el('thead'),tr=el('tr');['Verse','Latin source surface'].forEach(function(x){tr.appendChild(el('th','',x));});head.appendChild(tr);table.appendChild(head);var body=el('tbody');(data.verses||[]).forEach(function(v){var r=el('tr');r.appendChild(el('td','',String(v.verse)));r.appendChild(el('td','logos-script-token',v.surface||''));body.appendChild(r);});table.appendChild(body);wrap.appendChild(table);section.appendChild(wrap);section.appendChild(sourceBadge('Biblia Sacra juxta Vulgatam Clementinam · Public Domain'));root.appendChild(section);}

function renderResult(reference,passageResult,semitic,septuagint,catholicGreek,vulgate){if(!tabPanel)return;var passage=passageResult.data||{};if(passage.testament!=='OT')return;clear(tabPanel);var root=el('div','logos-ot-unified-root');root.setAttribute('data-ot-unified-reference',reference);root.appendChild(el('h2','','Old Testament interlinear — English + original-language witnesses'));root.appendChild(el('p','logos-note','Douay-Rheims remains the primary Catholic Bible text. Available Hebrew/Aramaic, Septuagint Greek and Latin witnesses are loaded from separate source-locked corpora. A source lane is blocked rather than silently renumbered when versification differs.'));renderEnglish(root,passage);
  var available=0;
  if(semitic&&semitic.ok){renderSemitic(root,semitic.data);available++;}else addPolicy(root,'Hebrew / Aramaic',mappingMessage(semitic,'Hebrew/Aramaic WLC/OSHB'));
  if(septuagint&&septuagint.ok){renderSeptuagintWitness(root,septuagint.data,'Greek — Septuagint (Swete)');available++;}
  else if(catholicGreek&&catholicGreek.ok){renderSeptuagintWitness(root,catholicGreek.data,'Greek — Catholic OT Swete witness');available++;}
  else addPolicy(root,'Septuagint Greek',mappingMessage((septuagint&&septuagint.status!==404)?septuagint:catholicGreek,'Septuagint Greek'));
  if(vulgate&&vulgate.ok){renderVulgate(root,vulgate.data);available++;}else addPolicy(root,'Latin Vulgate',mappingMessage(vulgate,'Clementine Latin Vulgate'));
  tabPanel.appendChild(root);setStatus('Live · '+reference+' · English + '+available+' original-language OT layer'+(available===1?'':'s'));
}

function loadMetadata(){var paths=[
  '/api/logos/ot-semitic/catalog','/api/logos/ot-semitic/source-rights',
  '/api/logos/ot-septuagint/catalog','/api/logos/ot-septuagint/source-rights',
  '/api/logos/ot-greek/catalog','/api/logos/ot-greek/source-rights',
  '/api/logos/vulgate/catalog','/api/logos/vulgate/source-rights'
];return Promise.all(paths.map(optionalGet)).then(function(rows){
  var sc=rows[0],sr=rows[1],gc=rows[2],gr=rows[3],dc=rows[4],dr=rows[5],vc=rows[6],vr=rows[7];
  readiness.semitic=!!(sc.ok&&sr.ok&&sc.data.production_enabled===true&&sc.data.corpus_id==='heb_arc_oshb_wlc'&&Number(sc.data.book_count)===39);
  readiness.septuagint=!!(gc.ok&&gr.ok&&gc.data.production_enabled===true&&gc.data.corpus_id==='grc_ot_swete_protocanonical'&&Number(gc.data.book_count)===37&&gr.data.partition&&gr.data.partition.license==='CC BY-SA 4.0');
  readiness.catholicGreek=!!(dc.ok&&dr.ok&&dc.data.production_enabled===true&&dc.data.corpus_id==='grc_ot_catholic_swete'&&Number(dc.data.witness_count)===15);
  readiness.vulgate=!!(vc.ok&&vr.ok&&vc.data.production_enabled===true&&vc.data.corpus_id==='lat_clementine_vulgate'&&Number(vc.data.book_count)===73&&vr.data.source&&vr.data.source.rights==='Public Domain');
  metadataLoaded=true;tryRender(true);return true;
});}

function tryRender(force){if(!metadataLoaded||!interlinearActive()||!tabPanel)return;var reference=currentReference();if(!reference)return;var marker=tabPanel.querySelector('[data-ot-unified-reference]');if(marker&&marker.getAttribute('data-ot-unified-reference')===reference&&!force)return;if(inFlight===reference&&!force)return;inFlight=reference;
  var passage=optionalGet('/api/logos/passage?reference='+encodeURIComponent(reference));
  var semitic=readiness.semitic?optionalGet('/api/logos/ot-semitic/interlinear?reference='+encodeURIComponent(reference)):Promise.resolve({ok:false,status:0,detail:'not_ready'});
  var sept=readiness.septuagint?optionalGet('/api/logos/ot-septuagint/interlinear?reference='+encodeURIComponent(reference)):Promise.resolve({ok:false,status:0,detail:'not_ready'});
  var cath=readiness.catholicGreek?optionalGet('/api/logos/ot-greek/interlinear?reference='+encodeURIComponent(reference)):Promise.resolve({ok:false,status:0,detail:'not_ready'});
  var vulg=readiness.vulgate?optionalGet('/api/logos/vulgate/interlinear?reference='+encodeURIComponent(reference)):Promise.resolve({ok:false,status:0,detail:'not_ready'});
  Promise.all([passage,semitic,sept,cath,vulg]).then(function(rows){if(currentReference()!==reference||!interlinearActive())return;if(!rows[0].ok||rows[0].data.testament!=='OT')return;renderResult(reference,rows[0],rows[1],rows[2],rows[3],rows[4]);}).finally(function(){if(inFlight===reference)inFlight='';});
}

function bind(){document.addEventListener('click',function(event){var tab=event.target.closest&&event.target.closest('[data-logos-tab]');if(tab&&tab.dataset.logosTab==='interlinear')setTimeout(function(){tryRender(true);},0);var ref=event.target.closest&&event.target.closest('[data-reference]');if(ref)setTimeout(function(){tryRender(true);},120);if(event.target&&event.target.id==='reloadLogos')setTimeout(function(){tryRender(true);},120);},true);var form=document.getElementById('logosReferenceForm');if(form)form.addEventListener('submit',function(){setTimeout(function(){tryRender(true);},120);},true);var observer=new MutationObserver(function(){if(metadataLoaded&&interlinearActive())tryRender(false);});if(passageHeading)observer.observe(passageHeading,{childList:true,characterData:true,subtree:true});if(tabPanel)observer.observe(tabPanel,{childList:true,subtree:false});}

if(!passageHeading||!tabPanel)return;
bind();loadConfig().then(loadMetadata).catch(function(err){console.warn('Logos unified OT integration configuration failed:',err&&err.message||err);});
})();
