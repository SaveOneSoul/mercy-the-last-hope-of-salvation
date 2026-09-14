(function(){
'use strict';

var dataUrl='../data/logos-interlinear/JHN-1-1.json';
var sourcesUrl='../data/logos-interlinear/sources-manifest.json';
var statusEl=document.getElementById('interlinearV1Status');
var greekEl=document.getElementById('interlinearV1Greek');
var tokensEl=document.getElementById('interlinearV1Tokens');
var provenanceEl=document.getElementById('interlinearV1Provenance');
var sourcesEl=document.getElementById('interlinearV1Sources');
var gateEl=document.getElementById('interlinearV1Gate');

function el(tag,className,text){
  var node=document.createElement(tag);
  if(className)node.className=className;
  if(text!==undefined&&text!==null)node.textContent=String(text);
  return node;
}

function safeGithubLink(url,label){
  var a=el('a','',label);
  if(/^https:\/\/github\.com\//i.test(String(url||''))){
    a.href=url;
    a.target='_blank';
    a.rel='noopener noreferrer';
  }
  return a;
}

function fetchJson(url){
  return fetch(url,{cache:'no-store'}).then(function(response){
    if(!response.ok)throw new Error('HTTP '+response.status);
    return response.json();
  });
}

function renderToken(token){
  var card=el('article','interlinear-v1-token');
  card.setAttribute('aria-label','Greek token '+token.position+': '+token.normalized);

  var position=el('span','interlinear-v1-position',token.position);
  var surface=el('div','interlinear-v1-surface',token.surface);
  surface.lang='grc';
  var transliteration=el('div','interlinear-v1-transliteration',token.transliteration);
  var gloss=el('div','interlinear-v1-gloss',token.gloss);

  var details=el('dl','interlinear-v1-details');
  [
    ['Lemma',token.lemma],
    ['POS',token.part_of_speech],
    ['Morph',token.morphology]
  ].forEach(function(row){
    var dt=el('dt','',row[0]);
    var dd=el('dd','',row[1]);
    details.appendChild(dt);
    details.appendChild(dd);
  });

  card.appendChild(position);
  card.appendChild(surface);
  card.appendChild(transliteration);
  card.appendChild(gloss);
  card.appendChild(details);
  return card;
}

function renderProvenance(provenance){
  provenanceEl.textContent='';
  Object.keys(provenance||{}).forEach(function(field){
    var row=provenance[field]||{};
    var tr=el('tr');
    tr.appendChild(el('th','',field));
    tr.appendChild(el('td','',(row.source||'')+(row.method?' — '+row.method:'')));
    provenanceEl.appendChild(tr);
  });
}

function renderSources(manifest){
  sourcesEl.textContent='';
  (manifest.sources||[]).forEach(function(source){
    var card=el('article','interlinear-v1-source');
    card.appendChild(el('h3','',source.title||source.id));
    card.appendChild(el('p','interlinear-v1-license',source.license||'Licence not recorded'));
    var pin=el('code','',String(source.commit||'').slice(0,12));
    var pinLine=el('p');
    pinLine.appendChild(document.createTextNode('Pinned commit: '));
    pinLine.appendChild(pin);
    card.appendChild(pinLine);
    card.appendChild(el('p','',source.attribution||''));
    if(source.upstream_repository){
      card.appendChild(safeGithubLink(source.upstream_repository,'Open upstream repository'));
    }
    sourcesEl.appendChild(card);
  });
}

Promise.all([fetchJson(dataUrl),fetchJson(sourcesUrl)]).then(function(results){
  var data=results[0],manifest=results[1];
  if(data.reference!=='John 1:1'||data.language!=='grc')throw new Error('prototype_scope_invalid');
  if(!Array.isArray(data.tokens)||data.tokens.length!==17)throw new Error('prototype_token_count_invalid');
  data.tokens.forEach(function(token,index){
    if(token.position!==index+1)throw new Error('prototype_position_invalid');
  });

  greekEl.textContent=data.greek_text||'';
  tokensEl.textContent='';
  data.tokens.forEach(function(token){tokensEl.appendChild(renderToken(token));});
  renderProvenance(data.field_provenance);
  renderSources(manifest);

  var gate=data.scale_gate||{};
  if(gate.full_nt_scaling_allowed===false){
    gateEl.textContent='Locked: '+(gate.unlock_requires||[]).join(' · ');
  }
  statusEl.textContent='Loaded source-locked prototype · '+data.tokens.length+' Greek tokens';
}).catch(function(error){
  statusEl.textContent='Prototype failed to load';
  statusEl.classList.add('error');
  tokensEl.textContent='';
  tokensEl.appendChild(el('div','interlinear-v1-error','The John 1:1 interlinear prototype could not be verified in the browser. '+error.message));
});
})();
