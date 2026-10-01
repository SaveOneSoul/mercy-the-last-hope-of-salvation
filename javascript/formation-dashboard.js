(function(){
const app=document.getElementById('dashboardApp');
function el(tag,text,cls){const n=document.createElement(tag);if(cls)n.className=cls;if(text!=null)n.textContent=text;return n}
async function load(){
 const cfg=await fetch('../data/formation-courses.json').then(r=>r.json());app.textContent='';
 const intro=el('section',null,'lesson-head');intro.innerHTML='<div class="eyebrow">Save One Soul Formation</div><h1>Formation Dashboard</h1><p>Track unit completion, internal credits, assessments and certificate eligibility. Progress is stored on this device and is visible to other users of this browser.</p><div class="btns"><a class="btn secondary" href="theology-professional.html">Theology Professional</a><a class="btn secondary" href="philosophy.html">Philosophy</a><a class="btn secondary" href="scripture-course.html">Scripture</a><a class="btn secondary" href="psychology-professional.html">Psychology Professional</a><a class="btn secondary" href="counselling-courses.html">Counselling courses</a><a class="btn secondary" href="study-tracks.html">Guided study tracks</a><a class="btn secondary" href="theology-library.html">Theology Library</a><a class="btn secondary" href="theology-glossary.html">Glossary</a></div>';app.append(intro);
 const grid=el('div',null,'dashboard-grid');
 for(const c of cfg.courses){
  const s=SaveOneSoulFormation.courseState(c.id),earned=SaveOneSoulFormation.credits(c.id),card=el('article',null,'dashboard-card'); const rich=c.contentFile?await fetch(c.contentFile).then(r=>r.ok?r.json():null).catch(()=>null):null, unitCount=rich?.units?.length||10;
  card.innerHTML='<span class="lesson-badge">'+c.credits+' credits</span><h2>'+c.title+'</h2><div class="formation-progress"><span style="width:'+Math.min(100,earned/c.credits*100)+'%"></span></div><p class="formation-progress-copy">'+earned+' / '+c.credits+' credits completed</p>';
  const units=el('div',null,'course-units');for(let i=1;i<=unitCount;i++){const done=!!(s.units&&s.units[i]&&s.units[i].complete);const row=el('div',null,'course-unit-row');row.innerHTML='<a href="formation-lesson.html?course='+encodeURIComponent(c.id)+'&unit='+i+'">Unit '+i+'</a><span class="complete-mark">'+(done?'✓ Complete':'Not complete')+'</span>';units.append(row)}card.append(units);
  const actions=el('div',null,'btns');actions.innerHTML='<a class="btn secondary" href="formation-assessment.html?course='+encodeURIComponent(c.id)+'&type=mid">Mid-course '+(s.mid?'✓':'')+'</a><a class="btn secondary" href="formation-assessment.html?course='+encodeURIComponent(c.id)+'&type=final">Final '+(s.final?'✓':'')+'</a>'+(SaveOneSoulFormation.eligible(c.id,c.credits)?'<a class="btn primary" href="formation-certificate.html?course='+encodeURIComponent(c.id)+'">Certificate</a>':'');card.append(actions);grid.append(card);
 }
 app.append(grid);
}
load().catch(e=>app.innerHTML='<p class="lesson-status">'+e.message+'</p>');
})();