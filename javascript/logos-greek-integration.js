(function(){
'use strict';

var script=document.currentScript,scriptUrl=script&&script.src?script.src:'';
var configUrl=scriptUrl?scriptUrl.replace(/logos-greek-integration\.js(?:\?.*)?$/,'analytics-config.json'):'';
var apiBase='',greekMode=false,greekCatalog=null,greekRights=null;
var greekTab=document.getElementById('logosGreekNtTab');
var form=document.getElementById('logosReferenceForm');
var referenceInput=document.getElementById('logosReference');
var parallelRoot=document.getElementById('logosParallel');
var tabPanel=document.getElementById('logosTabPanel');
var statusEl=document.getElementById('logosStatus');
var passageHeading=document.getElementById('passageHeading');
var reloadButton=document.getElementById('reloadLogos');

if(!greekTab||!form||!referenceInput||!parallelRoot||!tabPanel)return;

function el(tag,className,text){var node=document.createElement(tag);if(className)node.className=className;if(text!=null)node.textContent=String(text);return node;}
function clear(node){while(node&&node.firstChild)node.removeChild(node.firstChild);}
function setStatus(text,error){if(!statusEl)return;statusEl.textContent=text;statusEl.style.color=error?'#9a1729':'';}
function loadConfig(){if(window.MERCY_API_BASE){apiBase=String(window.MERCY_API_BASE).replace(/\/$/,'');return Promise.resolve();}if(!configUrl)return Promise.reject(new Error('config_missing'));return fetch(configUrl,{cache:'no-store'}).then(function(r){if(!r.ok)throw new Error('config_failed');return r.json();}).then(function(c){apiBase=String(c.mercy_api_base||'').replace(/\/$/,'');if(!apiBase)throw new Error('api_missing');});}
function getJson(path){return fetch(apiBase+path,{cache:'no-store'}).then(function(r){if(!r.ok)return r.json().catch(function(){return {};}).then(function(d){var e=new Error(d.detail||'request_failed');e.status=r.status;throw e;});return r.json();});}
function sourceLabel(source,fallback){if(!source)return fallback;return (source.id||source.title||fallback)+(source.license?' · '+source.license:'');}
function englishLane(passage){return passage&&passage.languages&&passage.languages.en?passage.languages.en:null;}
function greekText(greek){return ((greek&&greek.surface&&greek.surface.verses)||[]).map(function(v){return v.text||'';}).filter(Boolean).join(' ');}

function renderEnglishCard(passage){var row=englishLane(passage),card=el('article','logos-language-card logos-primary-scripture');card.dataset.code='en';var h=el('h3','','English — Douay-Rheims 1899');h.appendChild(el('span','logos-primary-badge','Primary Catholic Bible layer'));card.appendChild(h);if(row&&row.text)card.appendChild(el('p','',row.text));else card.appendChild(el('p','','English Douay-Rheims text is unavailable for this reference.'));if(row&&row.source)card.appendChild(el('span','logos-source-badge',sourceLabel(row.source,'Douay-Rheims 1899')));return card;}
function renderGreekCard(greek){var card=el('article','logos-language-card');card.dataset.code='grc';var h=el('h3','','Greek — SBLGNT');h.appendChild(el('span','logos-status-pill','study layer'));card.appendChild(h);var text=greekText(greek);card.appendChild(el('p','logos-greek-script',text||'Greek surface text is unavailable for this reference.'));var source=greek&&greek.surface&&greek.surface.source;card.appendChild(el('span','logos-source-badge',sourceLabel(source,'SBLGNT')));card.appendChild(el('small','','Greek is a licensed original-language study layer and does not replace the primary English Catholic Bible text.'));return card;}
function renderCombined(passage,greek){clear(parallelRoot);if(passageHeading)passageHeading.textContent=(passage&&passage.reference)||greek.reference||referenceInput.value;parallelRoot.appendChild(renderEnglishCard(passage));parallelRoot.appendChild(renderGreekCard(greek));}
function renderEnglishOnly(passage,message){clear(parallelRoot);if(passageHeading)passageHeading.textContent=(passage&&passage.reference)||referenceInput.value;parallelRoot.appendChild(renderEnglishCard(passage));var card=el('article','logos-language-card');card.dataset.code='grc';card.appendChild(el('h3','','Greek New Testament'));card.appendChild(el('p','',message));parallelRoot.appendChild(card);}

function licenseCard(title,source,partition){var card=el('article','logos-study-card');card.appendChild(el('h3','',title));card.appendChild(el('p','',sourceLabel(source,'Source record unavailable')));if(source&&source.repository)card.appendChild(el('small','',source.repository+(source.commit?' @ '+source.commit:'')));if(partition&&partition.share_alike)card.appendChild(el('p','logos-greek-license-note','ShareAlike partition preserved.'));return card;}
function renderGreekInterlinear(greek){clear(tabPanel);var intro=el('div','');intro.appendChild(el('h2','','Greek New Testament interlinear study'));intro.appendChild(el('p','logos-note','English Douay-Rheims remains the primary Catholic Bible layer. Greek surface text, transliteration, lemma, part of speech and morphology are presented as a separate licensed study layer.'));tabPanel.appendChild(intro);

var summary=el('div','logos-greek-summary');summary.appendChild(el('span','logos-status-pill',(greek.tokens||[]).length+' tokens'));summary.appendChild(el('span','logos-status-pill','SBLGNT surface'));summary.appendChild(el('span','logos-status-pill','MorphGNT morphology'));tabPanel.appendChild(summary);

var wrap=el('div','logos-interlinear-wrap'),table=el('table','logos-interlinear'),thead=el('thead'),tr=el('tr');['Greek','Transliteration','Lemma','POS','Morphology'].forEach(function(x){tr.appendChild(el('th','',x));});thead.appendChild(tr);table.appendChild(thead);var tbody=el('tbody');(greek.tokens||[]).forEach(function(t){var r=el('tr');r.appendChild(el('td','logos-script-token',t.surface||''));r.appendChild(el('td','',t.transliteration||''));r.appendChild(el('td','',t.lemma||''));r.appendChild(el('td','',t.part_of_speech_code||''));r.appendChild(el('td','',t.morphology||((t.annotation_status&&t.annotation_status!=='available')?'Unavailable':'')));tbody.appendChild(r);});table.appendChild(tbody);wrap.appendChild(table);tabPanel.appendChild(wrap);
if(!(greek.tokens||[]).length)tabPanel.appendChild(el('div','logos-error','No Greek tokens were returned for this reference.'));

var gapVerses=((greek.linguistics&&greek.linguistics.verses)||[]).filter(function(v){return v.annotation_status&&v.annotation_status!=='available';});if(gapVerses.length){var gap=el('div','logos-policy');gap.appendChild(el('strong','','Morphology annotation gap'));gap.appendChild(el('p','',gapVerses.map(function(v){return greek.book+' '+greek.chapter+':'+v.verse;}).join(', ')+' has SBLGNT surface text but no MorphGNT annotation in the pinned source. No morphology is fabricated.'));tabPanel.appendChild(gap);}

var rightsGrid=el('div','logos-greek-license-grid'),surfaceSource=greek.surface&&greek.surface.source,lingSource=greek.linguistics&&greek.linguistics.source;rightsGrid.appendChild(licenseCard('Greek surface & transliteration',surfaceSource,greek.surface&&greek.surface.license_partition));rightsGrid.appendChild(licenseCard('Lemma, POS & morphology',lingSource,greek.linguistics&&greek.linguistics.license_partition));tabPanel.appendChild(rightsGrid);

var gloss=el('div','logos-policy');gloss.appendChild(el('strong','','English gloss layer'));gloss.appendChild(el('p','',(greek.gloss_layer&&greek.gloss_layer.installed)?'A licensed gloss layer is installed.':'Not installed. No English word gloss is displayed because no separately approved gloss source has been licensed and source-locked.'));tabPanel.appendChild(gloss);
}

function renderGreekNotApplicable(passage){clear(tabPanel);tabPanel.appendChild(el('h2','','Greek New Testament study layer'));tabPanel.appendChild(el('div','logos-error','This reference is outside the New Testament. The complete 73-book Douay-Rheims English Catholic corpus remains available as the primary Bible layer.'));renderEnglishOnly(passage,'The production Greek corpus covers the 27 New Testament books only.');}
function greekErrorMessage(err){var code=err&&err.message||'';if(code==='logos_greek_nt_reference_required')return 'This reference is outside the New Testament.';if(code==='logos_greek_verse_not_found')return 'That verse is not available in the installed Greek New Testament corpus.';if(code==='logos_greek_chapter_not_found')return 'That chapter is not available in the installed Greek New Testament corpus.';if(code==='logos_greek_book_not_installed')return 'That New Testament book is not installed in the Greek corpus.';return 'The production Greek New Testament study layer could not be loaded.';}

function studyGreek(reference){reference=String(reference||'').trim();if(!reference)return;referenceInput.value=reference;setStatus('Loading English + Greek · '+reference+'…');var passagePromise=getJson('/api/logos/passage?reference='+encodeURIComponent(reference));var greekPromise=getJson('/api/logos/greek/interlinear?reference='+encodeURIComponent(reference));Promise.all([passagePromise,greekPromise]).then(function(rows){var passage=rows[0],greek=rows[1];referenceInput.value=greek.reference||passage.reference||reference;if(passageHeading)passageHeading.textContent=greek.reference||passage.reference||reference;renderCombined(passage,greek);renderGreekInterlinear(greek);setStatus('Greek NT live · '+(greek.reference||reference));}).catch(function(err){passagePromise.then(function(passage){if(err&&err.message==='logos_greek_nt_reference_required'){renderGreekNotApplicable(passage);setStatus('English Catholic corpus live · Greek NT not applicable');return;}clear(tabPanel);tabPanel.appendChild(el('div','logos-error',greekErrorMessage(err)));renderEnglishOnly(passage,greekErrorMessage(err));setStatus('Greek NT layer unavailable · '+reference,true);}).catch(function(){clear(tabPanel);tabPanel.appendChild(el('div','logos-error','Could not load this Bible reference.'));setStatus('Could not load '+reference,true);});});}

function activateGreek(){greekMode=true;document.querySelectorAll('[data-logos-tab]').forEach(function(x){x.classList.remove('active');});greekTab.classList.add('active');studyGreek(referenceInput.value);}
function deactivateGreek(){greekMode=false;greekTab.classList.remove('active');}

greekTab.addEventListener('click',activateGreek);
form.addEventListener('submit',function(e){if(!greekMode)return;e.preventDefault();e.stopImmediatePropagation();studyGreek(referenceInput.value);},true);
document.addEventListener('click',function(e){var quick=e.target.closest&&e.target.closest('[data-reference]');if(greekMode&&quick){e.preventDefault();e.stopImmediatePropagation();studyGreek(quick.dataset.reference);return;}if(greekMode&&reloadButton&&(e.target===reloadButton||reloadButton.contains(e.target))){e.preventDefault();e.stopImmediatePropagation();studyGreek(referenceInput.value);return;}var normal=e.target.closest&&e.target.closest('[data-logos-tab]');if(normal)deactivateGreek();},true);

loadConfig().then(function(){return Promise.all([getJson('/api/logos/greek/catalog'),getJson('/api/logos/greek/source-rights')]);}).then(function(rows){greekCatalog=rows[0];greekRights=rows[1];if(!greekCatalog.production_enabled||Number(greekCatalog.book_count)!==27)throw new Error('greek_catalog_not_ready');greekTab.disabled=false;greekTab.title='Production Greek NT: '+greekCatalog.book_count+' books · '+greekCatalog.verse_count+' verses';greekTab.dataset.productionReady='true';}).catch(function(){greekTab.disabled=true;greekTab.title='Greek NT production layer is not currently available.';});
})();