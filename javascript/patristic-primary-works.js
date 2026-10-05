(function(){
'use strict';
const DATA='../data/patristic-primary-works.json';
function esc(v){return String(v==null?'':v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function label(status){
 return {
  'local':'Local full/primary text',
  'public-domain-online':'Public-domain text online',
  'partial-public-domain':'Partial reusable text',
  'source-review':'Source/rights review'
 }[status]||status;
}
fetch(DATA,{cache:'no-store'}).then(r=>{if(!r.ok)throw new Error('HTTP '+r.status);return r.json();}).then(data=>{
 (data.profiles||[]).forEach(row=>{
  const card=document.getElementById(row.card_id);
  if(!card||card.querySelector('.all-primary-works'))return;
  const body=card.querySelector('.father-body')||card;
  const box=document.createElement('section');
  box.className='all-primary-works';
  const sourceLinks=(row.sources||[]).map(s=>{
   const external=/^https?:/i.test(s.url);
   return '<a class="btn '+(external?'secondary':'primary')+'" '+(external?'target="_blank" rel="noopener noreferrer" ':'')+'href="'+esc(s.url)+'">'+esc(s.label)+'</a>';
  }).join('');
  box.innerHTML='<div class="all-primary-head"><h3>Original Works / Homilies / Primary Texts</h3><span class="all-primary-status '+esc(row.source_status)+'">'+esc(label(row.source_status))+'</span></div>'+
    '<p><strong>Works:</strong> '+esc(row.major_works||'Primary works listed in the profile.')+'</p>'+
    (sourceLinks?'<div class="primary-source-links">'+sourceLinks+'</div>':'')+
    '<p class="primary-source-meta">'+esc(row.note||'')+'</p>';
  const details=body.querySelector('.father-deep-study');
  if(details) body.insertBefore(box,details);
  else body.appendChild(box);
 });
}).catch(err=>{
 console.warn('Patristic primary works catalog unavailable',err);
});
})();