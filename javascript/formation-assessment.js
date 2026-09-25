(function(){
const qs=new URL(location.href).searchParams,courseId=qs.get('course'),type=qs.get('type')==='final'?'final':'mid';
const app=document.getElementById('assessmentApp');
function el(tag,text,cls){const n=document.createElement(tag);if(cls)n.className=cls;if(text!=null)n.textContent=text;return n}
async function load(){
 const cfg=await fetch('../data/formation-courses.json').then(r=>r.json()),course=cfg.courses.find(c=>c.id===courseId);if(!course)throw new Error('Unknown course');
 const src=await fetch(course.source,{cache:'no-store'}).then(r=>r.text()),doc=new DOMParser().parseFromString(src,'text/html'),root=doc.querySelector(course.courseSelector),units=root?[...root.querySelectorAll(course.unitSelector)]:[];
 const chosen=type==='mid'?units.slice(0,5):units.slice(5,10);
 document.title=(type==='mid'?'Mid-course assessment':'Final synthesis assessment')+' · '+course.title;
 app.innerHTML='<section class="lesson-head"><div class="eyebrow">'+course.title+'</div><h1>'+(type==='mid'?'Mid-course assessment':'Final synthesis assessment')+'</h1><p>Answer at least 4 of 5 questions correctly. This assessment checks whether you can identify the main themes of the course units.</p></section>';
 const form=el('form',null,'lesson-main lesson-quiz');form.id='assessmentForm';
 const allTitles=units.map(u=>(u.querySelector('h3')||{}).textContent||'Unit');
 chosen.forEach((u,i)=>{const title=(u.querySelector('h3')||{}).textContent||('Unit '+(i+1));const ps=[...u.querySelectorAll('p')].map(p=>p.textContent.trim()).filter(Boolean),desc=ps.find(p=>!/^Core reading:/i.test(p)&&!/^Study task:/i.test(p))||title;const wrong=allTitles.filter(x=>x!==title).slice(i%Math.max(1,allTitles.length-1)).slice(0,2);while(wrong.length<2)wrong.push('An unrelated topic');const q=el('div',null,'quiz-question');q.innerHTML='<strong>'+(i+1)+'. Which unit best matches this description?</strong><p>'+desc+'</p>'+[title,...wrong].map((o,j)=>'<label><input type="radio" name="q'+i+'" value="'+j+'" required> '+o+'</label>').join('');form.append(q)});
 form.innerHTML+='<button class="btn primary" type="submit">Submit assessment</button><p id="assessmentResult" class="lesson-status" hidden></p>';
 app.append(form);
 form.addEventListener('submit',e=>{e.preventDefault();const fd=new FormData(form);let score=0;chosen.forEach((_,i)=>{if(fd.get('q'+i)==='0')score++});const pass=score>=4;SaveOneSoulFormation.setAssessment(courseId,type,pass,score);const out=document.getElementById('assessmentResult');out.hidden=false;out.textContent='Score: '+score+'/5. '+(pass?'Assessment passed and recorded.':'Review the course and try again.');});
}
load().catch(e=>app.innerHTML='<p class="lesson-status">'+e.message+'</p>');
})();