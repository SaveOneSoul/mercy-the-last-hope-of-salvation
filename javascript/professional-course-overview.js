(() => {
  'use strict';
  async function loadBlock(block){
    const id=block.dataset.courseId, start=Math.max(1,Number(block.dataset.startUnit||1)), endRaw=Number(block.dataset.endUnit||0);
    const cfg=await fetch('../data/formation-courses.json').then(r=>r.json());
    const course=cfg.courses.find(c=>c.id===id);
    if(!course||!course.contentFile) throw new Error('Course configuration unavailable.');
    const data=await fetch(course.contentFile).then(r=>r.json());
    const end=endRaw>0?Math.min(endRaw,data.units.length):data.units.length;
    if(!block.querySelector('h2')){
      const h=document.createElement('h2');h.textContent=course.title;block.append(h);
      const p=document.createElement('p');p.textContent=data.description||'';block.append(p);
    }
    const meta=document.createElement('p');meta.className='learning-note';
    meta.textContent=data.units.length+' units · '+course.credits+' internal formation credits · '+(data.creditNote||'Non-accredited self-study.');
    block.append(meta);
    const ol=document.createElement('ol');ol.className='unit-list';
    for(let n=start;n<=end;n++){
      const u=data.units[n-1],li=document.createElement('li'),a=document.createElement('a'),small=document.createElement('small');
      a.href='formation-lesson.html?course='+encodeURIComponent(id)+'&unit='+n;a.textContent=n+'. '+u.title;
      small.textContent=(u.objectives&&u.objectives[0])||'Open the full lesson.';
      li.append(a,small);ol.append(li);
    }
    block.append(ol);
    const actions=document.createElement('div');actions.className='learning-actions';
    actions.innerHTML='<a class="btn primary" href="formation-lesson.html?course='+encodeURIComponent(id)+'&unit='+start+'">Begin this section</a><a class="btn secondary" href="formation-assessment.html?course='+encodeURIComponent(id)+'&type=mid">Mid-course review</a><a class="btn secondary" href="formation-assessment.html?course='+encodeURIComponent(id)+'&type=final">Final review</a><a class="btn secondary" href="formation-dashboard.html">My learning</a>';
    block.append(actions);
  }
  document.addEventListener('DOMContentLoaded',()=>document.querySelectorAll('[data-course-id]').forEach(b=>loadBlock(b).catch(e=>{b.innerHTML='<p class="learning-note">'+e.message+'</p>';})));
})();