(async () => {
  const [detailsResponse,profilesResponse]=await Promise.all([fetch('../data/saint-details.json'),fetch('../data/saint-profiles.json')]);
  if(!detailsResponse.ok||!profilesResponse.ok)return;
  const details=await detailsResponse.json(),profiles=await profilesResponse.json();
  const articles=[...document.querySelectorAll('.saint-list article.saint-item[id]')];
  const count=document.getElementById('saint-expanded-count');if(count)count.textContent=String(articles.filter(article=>profiles[article.id]?.sections?.length).length);
  for(const article of articles){
    const detail=details[article.id]||{},profile=profiles[article.id];
    if(profile?.image){const img=document.createElement('img');img.className='saint-thumb';img.src='https://commons.wikimedia.org/wiki/Special:FilePath/'+encodeURIComponent(profile.image)+'?width=360';img.alt='Historical image or artwork associated with '+article.querySelector('h3').textContent;img.loading='lazy';img.addEventListener('error',()=>img.remove());article.prepend(img)}
    if(detail.patronage||profile?.patronage){const p=document.createElement('p');p.textContent='Patronage: '+(profile?.patronage||detail.patronage);article.querySelector('.badge').after(p);article.dataset.saint+=' '+p.textContent.toLowerCase()}
    if(detail.rank){const rank=document.createElement('span');rank.className='badge';rank.textContent=detail.rank;article.querySelector('.badge').after(rank)}
  }
  let active='all';const search=document.querySelector('[data-saint-search]');
  const render=()=>{const q=search.value.trim().toLowerCase();articles.forEach(a=>{const matchesFilter=active==='all'||(active==='india'&&/india|kerala|goa|vasai|calcutta|kolkata|sri lanka/.test(a.dataset.saint+' '+a.textContent.toLowerCase()))||(active==='feast'&&/\b(feast|solemnity)\b/i.test(details[a.id]?.rank||''))||(active==='story'&&!!profiles[a.id]);a.hidden=!matchesFilter||!!q&&!a.dataset.saint.includes(q)&&!a.textContent.toLowerCase().includes(q)})};
  search.addEventListener('input',render);
  document.querySelectorAll('[data-saint-filter]').forEach(button=>button.addEventListener('click',()=>{active=button.dataset.saintFilter;document.querySelectorAll('[data-saint-filter]').forEach(b=>b.setAttribute('aria-pressed',String(b===button)));render()}));
})();
