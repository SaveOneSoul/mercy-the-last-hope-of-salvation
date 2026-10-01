(() => {
  'use strict';
  const grid=document.getElementById('bookBackgroundGrid'),search=document.getElementById('bookSearch'),testament=document.getElementById('bookTestament'),section=document.getElementById('bookSection');
  if(!grid)return;
  let books=[];
  function esc(v){return String(v??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));}
  function card(b){
    const themes=(b.majorThemes||[]).map(x=>'<span class="lesson-badge">'+esc(x)+'</span>').join(' ');
    const qs=(b.studyQuestions||[]).map(x=>'<li>'+esc(x)+'</li>').join('');
    return '<article class="book-card"><div class="book-meta">'+esc(b.testament)+' · '+esc(b.section)+'</div><h3>'+esc(b.name)+'</h3><p><strong>Genre:</strong> '+esc(b.genre)+'</p><p><strong>Original language:</strong> '+esc(b.originalLanguage)+'</p><p><strong>Audience:</strong> '+esc(b.audience)+'</p><p><strong>Purpose:</strong> '+esc(b.purpose)+'</p><div>'+themes+'</div><details><summary>Full background</summary><p><strong>Authorship / tradition:</strong> '+esc(b.authorship)+'</p><p><strong>Composition:</strong> '+esc(b.composition)+'</p><p><strong>Cultural-historical context:</strong> '+esc(b.culturalHistoricalContext)+'</p><h4>Study questions</h4><ul>'+qs+'</ul></details></article>';
  }
  function render(){
    const q=(search?.value||'').trim().toLowerCase(),t=testament?.value||'',s=section?.value||'';
    const filtered=books.filter(b=>{
      const hay=[b.name,b.section,b.authorship,b.audience,b.purpose,b.genre,b.originalLanguage,b.culturalHistoricalContext,...(b.majorThemes||[])].join(' ').toLowerCase();
      return (!q||hay.includes(q))&&(!t||b.testament===t)&&(!s||b.section===s);
    });
    grid.innerHTML=filtered.length?filtered.map(card).join(''):'<p>No matching books.</p>';
  }
  fetch('../data/scripture-book-backgrounds.json').then(r=>{if(!r.ok)throw new Error('Book backgrounds unavailable');return r.json();}).then(d=>{
    books=d.books||[];
    const sections=[...new Set(books.map(b=>b.section).filter(Boolean))].sort();
    sections.forEach(v=>{const o=document.createElement('option');o.value=v;o.textContent=v;section.append(o);});
    render();
  }).catch(e=>grid.innerHTML='<p>'+esc(e.message)+'</p>');
  [search,testament,section].forEach(el=>el&&el.addEventListener(el===search?'input':'change',render));
})();