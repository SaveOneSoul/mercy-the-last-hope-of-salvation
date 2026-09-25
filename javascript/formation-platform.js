(function(){
const KEY='sosFormationProgressV1';
function read(){try{return JSON.parse(localStorage.getItem(KEY)||'{}')}catch(e){return {}}}
function write(v){localStorage.setItem(KEY,JSON.stringify(v))}
function courseState(id){const all=read();return all[id]||{units:{},mid:false,final:false}}
function saveCourse(id,state){const all=read();all[id]=state;write(all)}
function credits(id){const s=courseState(id);return Object.values(s.units||{}).filter(x=>x&&x.complete).length*2}
function completeUnit(id,n,payload){const s=courseState(id);s.units=s.units||{};s.units[n]=Object.assign({},s.units[n],payload,{complete:true,completedAt:new Date().toISOString()});saveCourse(id,s)}
function saveDraft(id,n,text){const s=courseState(id);s.units=s.units||{};s.units[n]=Object.assign({},s.units[n],{assignment:text});saveCourse(id,s)}
function setAssessment(id,type,passed,score){const s=courseState(id);s[type]=!!passed;s[type+'Score']=score;s[type+'At']=passed?new Date().toISOString():null;saveCourse(id,s)}
function eligible(id,total){const s=courseState(id);return credits(id)>=total&&s.mid&&s.final}
window.SaveOneSoulFormation={KEY,read,write,courseState,saveCourse,credits,completeUnit,saveDraft,setAssessment,eligible};

document.addEventListener('DOMContentLoaded',function(){
 const page=document.body;
 const map={
  'theology.html':['foundations','trinity','christology','pneumatology','ecclesiology','mariology','sacraments','moral','spiritual','eschatology'],
  'divine-mercy.html':['divine-mercy'],
  'charis.html':['charis']
 };
 const file=location.pathname.split('/').pop(),ids=map[file];if(!ids)return;
 function labelFor(id,n){
  if(id==='divine-mercy'){if(n===6)return 'Private revelation';if([7,8,9].includes(n))return 'Devotional practice';return 'Authoritative teaching';}
  if(id==='charis')return 'Common theological teaching';
  if(id==='trinity'&&[3,4,5].includes(n))return 'Dogma';
  if(id==='christology'&&[2,3,4,5,6].includes(n))return 'Dogma';
  if(id==='mariology'&&[2,3,4,5].includes(n))return 'Dogma';
  if(id==='foundations'&&n===6)return 'Common theological teaching';
  return 'Authoritative teaching';
 }
 fetch('../data/formation-courses.json').then(r=>r.json()).then(cfg=>{
  const courses=cfg.courses.filter(c=>ids.includes(c.id));
  const shell=document.querySelector('.formation-shell')||document.querySelector('main');if(!shell)return;
  const bar=document.createElement('div');bar.className='formation-platform-bar';
  const total=courses.reduce((n,c)=>n+c.credits,0),earned=courses.reduce((n,c)=>n+credits(c.id),0);
  bar.innerHTML='<div class="formation-progress-row"><strong>Formation progress</strong><div class="formation-progress"><span style="width:'+Math.min(100,earned/total*100)+'%"></span></div><span class="formation-progress-copy">'+earned+' / '+total+' credits completed</span><a class="btn secondary" href="formation-dashboard.html">Dashboard</a></div>';
  shell.insertBefore(bar,shell.firstChild);
  courses.forEach(c=>{
   const course=document.querySelector(c.courseSelector);if(!course)return;
   const units=[...course.querySelectorAll(c.unitSelector)];
   units.forEach((u,i)=>{
    if(!u.querySelector('.lesson-badge[data-doctrine-label]')){
      const badge=document.createElement('span');badge.className='lesson-badge';badge.dataset.doctrineLabel='true';badge.textContent=labelFor(c.id,i+1);const head=u.querySelector('.theology-unit-head,.credit-unit-head');if(head)head.appendChild(badge);else u.insertBefore(badge,u.firstChild);
    }
    if(u.querySelector('.formation-lesson-link'))return;
    const a=document.createElement('a');a.className='btn secondary formation-lesson-link';a.href='formation-lesson.html?course='+encodeURIComponent(c.id)+'&unit='+(i+1);a.textContent='Open full lesson →';u.appendChild(a);
   });
  });
 }).catch(()=>{});
});
})();