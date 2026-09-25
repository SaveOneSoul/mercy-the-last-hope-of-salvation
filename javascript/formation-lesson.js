(function(){
const qs=new URL(location.href).searchParams,courseId=qs.get('course'),unitNo=parseInt(qs.get('unit')||'1',10);
const app=document.getElementById('lessonApp');
const doctrineLabels=['Dogma','Definitive teaching','Authoritative teaching','Common theological teaching','Patristic opinion','Private revelation','Devotional practice'];
function labelFor(id,n){
 if(id==='divine-mercy'){if(n===6)return ['Private revelation'];if([7,8,9].includes(n))return ['Devotional practice','Authoritative teaching'];return ['Authoritative teaching'];}
 if(id==='charis')return ['Common theological teaching','Authoritative teaching'];
 if(id==='trinity'&&[3,4,5].includes(n))return ['Dogma'];
 if(id==='christology'&&[2,3,4,5,6].includes(n))return ['Dogma'];
 if(id==='mariology'&&[2,3,4,5].includes(n))return ['Dogma'];
 if(id==='foundations'&&n===6)return ['Common theological teaching'];
 return ['Authoritative teaching'];
}
function fatherName(id){return id.split('-').map(x=>x.charAt(0).toUpperCase()+x.slice(1)).join(' ')}
function pickScripture(text){
 const m=String(text||'').match(/(?:Genesis|Exodus|Leviticus|Numbers|Deuteronomy|Joshua|Judges|Ruth|Samuel|Kings|Chronicles|Ezra|Nehemiah|Tobit|Judith|Esther|Maccabees|Job|Psalms?|Proverbs|Ecclesiastes|Song of Songs|Wisdom|Sirach|Isaiah|Jeremiah|Lamentations|Baruch|Ezekiel|Daniel|Hosea|Joel|Amos|Obadiah|Jonah|Micah|Nahum|Habakkuk|Zephaniah|Haggai|Zechariah|Malachi|Matthew|Mark|Luke|John|Acts|Romans|Corinthians|Galatians|Ephesians|Philippians|Colossians|Thessalonians|Timothy|Titus|Philemon|Hebrews|James|Peter|Jude|Revelation)\s+\d+(?::\d+(?:[-–]\d+)?)?/i);
 return m?m[0]:null;
}
function el(tag,text,cls){const n=document.createElement(tag);if(cls)n.className=cls;if(text!=null)n.textContent=text;return n;}
async function load(){
 if(!courseId){app.innerHTML='<div class="lesson-status">Choose a course from the formation dashboard.</div>';return;}
 const cfg=await fetch('../data/formation-courses.json').then(r=>r.json()),course=cfg.courses.find(c=>c.id===courseId);
 if(!course)throw new Error('Unknown course');
 const src=await fetch(course.source,{cache:'no-store'}).then(r=>r.text()),doc=new DOMParser().parseFromString(src,'text/html'),root=doc.querySelector(course.courseSelector),units=root?[...root.querySelectorAll(course.unitSelector)]:[];
 const unit=units[unitNo-1];if(!unit)throw new Error('Unit not found');
 const title=(unit.querySelector('h3')||{}).textContent||('Unit '+unitNo);
 const ps=[...unit.querySelectorAll('p')].map(p=>p.textContent.trim()).filter(Boolean);
 const core=(ps.find(p=>/^Core reading:/i.test(p))||'Core reading: Scripture, Fathers and Church teaching.').replace(/^Core reading:\s*/i,'');
 const body=ps.find(p=>!/^Core reading:/i.test(p)&&!/^Study task:/i.test(p))||'Study the topic through the primary and ecclesial sources listed in this lesson.';
 const labels=labelFor(courseId,unitNo),scripture=pickScripture(core);
 const state=SaveOneSoulFormation.courseState(courseId),saved=(state.units&&state.units[unitNo])||{};
 document.title=title+' · '+course.title+' · Save One Soul';
 app.innerHTML='';
 const head=el('section',null,'lesson-head');head.innerHTML='<div class="eyebrow">'+course.title+' · Unit '+unitNo+' of '+units.length+'</div><h1>'+title+'</h1><p>'+body+'</p><div class="lesson-badges">'+labels.map(x=>'<span class="lesson-badge '+(x==='Dogma'?'dogma':x==='Private revelation'?'private':x==='Devotional practice'?'devotion':'')+'">'+x+'</span>').join('')+'<span class="lesson-badge">2 formation credits</span></div>';
 app.append(head);
 const grid=el('div',null,'lesson-grid'),main=el('article',null,'lesson-main'),side=el('aside',null,'lesson-side');
 main.innerHTML='<section class="lesson-section"><h2>Learning objectives</h2><ul class="lesson-objectives"><li>Explain '+title.toLowerCase()+' in clear Catholic theological language.</li><li>Interpret the core sources in their biblical, historical and ecclesial context.</li><li>Distinguish defined teaching from theological opinion, private revelation or devotional practice where applicable.</li><li>Connect doctrine with prayer, pastoral life and mission without reducing theology to personal experience.</li></ul></section>'+
 '<section class="lesson-section"><h2>Lesson text</h2><p>'+body+'</p><p>This unit should be studied by moving from the primary text to the Church’s received interpretation. Begin with the biblical passages or ancient sources named below, identify the theological question being addressed, then compare the witness of the Fathers and the Magisterium. Where terminology developed over time, do not force later technical vocabulary into an earlier author; instead trace how the Church clarified language while preserving the substance of the apostolic faith.</p><p>The aim is not merely to memorize formulas. A sound theological account should be able to state the doctrine, explain why the Church teaches it, identify the sources on which it rests, distinguish it from common misunderstandings, and show how it belongs within the wider mystery of Christ and the Church.</p></section>'+
 '<section class="lesson-section"><h2>Scripture & primary sources</h2><ul class="lesson-sources"><li><strong>Core reading:</strong> '+core+'</li>'+(scripture?'<li><a href="logos.html#verse='+encodeURIComponent(scripture)+'">Open '+scripture+' in Logos Bible</a></li>':'<li><a href="logos.html">Open Logos Bible for textual study</a></li>')+'</ul></section>'+
 '<section class="lesson-section"><h2>Fathers & Doctors</h2><p>Use the patristic witnesses as historical and theological sources, while keeping each author’s period and authority distinct from the Magisterium.</p><div class="btns">'+course.fatherIds.map(id=>'<a class="btn secondary" href="fathers.html#father-'+id+'">Read '+fatherName(id)+'</a>').join('')+'<a class="btn secondary" href="patristic-library.html">Primary Text Library</a></div></section>'+
 '<section class="lesson-section"><h2>Councils & Magisterium</h2><ul class="lesson-sources">'+course.magisterial.map(x=>'<li>'+x+'</li>').join('')+'</ul><p><a class="btn secondary" href="theology-library.html">Open Catholic Theology Library</a></p></section>'+
 '<section class="lesson-section"><h2>Glossary</h2><p><a href="theology-glossary.html">Open the theological glossary</a> to review technical terms used across the curriculum.</p></section>'+
 '<section class="lesson-section"><h2>Study questions</h2><ol class="lesson-questions"><li>State the principal claim of this unit in your own words.</li><li>Which source carries the greatest authority for the claim, and why?</li><li>What historical controversy or pastoral need helped clarify this teaching?</li><li>What common misunderstanding should a catechist avoid?</li><li>How does this unit connect to another field of Catholic theology?</li></ol></section>';
 const allCore=units.map(u=>{const p=[...u.querySelectorAll('p')].map(p=>p.textContent.trim()).find(x=>/^Core reading:/i.test(x));return p?p.replace(/^Core reading:\s*/i,''):'Scripture and Church teaching'}).filter(Boolean);
 const distract=allCore.filter(x=>x!==core).slice(0,2);while(distract.length<2)distract.push('A source unrelated to this unit');
 const quiz=el('section',null,'lesson-section');quiz.innerHTML='<h2>Short quiz</h2><form id="lessonQuiz" class="lesson-quiz">'+
  qhtml(1,'Which statement best summarizes this lesson?',[body,'This topic has no relation to Scripture or Tradition.','The lesson is only a private devotional opinion.'],0)+
  qhtml(2,'Which core reading belongs to this unit?',[core,distract[0],distract[1]],0)+
  qhtml(3,'Which category is used on this lesson?',[labels[0],...doctrineLabels.filter(x=>x!==labels[0]).slice(0,2)],0)+
  '<button class="btn primary" type="submit">Check quiz</button><p id="quizResult" class="lesson-status" hidden></p></form>';
 main.append(quiz);
 const assignment=el('section',null,'lesson-section lesson-assignment');assignment.innerHTML='<h2>Assignment</h2><p>Write at least 80 characters summarizing the doctrine, its strongest source, and one pastoral application. Your work is saved privately in this browser.</p><textarea id="assignmentText" placeholder="Write your study synthesis here…"></textarea><div class="btns"><button class="btn secondary" id="saveAssignment" type="button">Save assignment</button><button class="btn primary" id="completeUnit" type="button">Complete unit</button></div><p id="completionStatus" class="lesson-status">'+(saved.complete?'This unit is complete. 2 credits have been recorded.':'Quiz score of at least 2/3 and an 80-character assignment are required.')+'</p>';
 main.append(assignment);
 side.innerHTML='<h2>Course progress</h2><div class="formation-progress"><span style="width:'+Math.min(100,SaveOneSoulFormation.credits(courseId)/course.credits*100)+'%"></span></div><p class="formation-progress-copy">'+SaveOneSoulFormation.credits(courseId)+' / '+course.credits+' credits completed</p><div class="btns"><a class="btn secondary" href="formation-dashboard.html">Dashboard</a><a class="btn secondary" href="'+course.source+'">Course overview</a></div><hr><h3>Source discipline</h3><p><strong>Primary sources</strong> are the biblical, patristic or conciliar texts themselves.</p><p><strong>Magisterial sources</strong> interpret or teach authoritatively.</p><p><strong>Secondary study</strong> explains and synthesizes; it should never be confused with the Magisterium.</p>';
 grid.append(main,side);app.append(grid);
 const assignmentText=document.getElementById('assignmentText');assignmentText.value=saved.assignment||'';
 let quizScore=typeof saved.quizScore==='number'?saved.quizScore:null;
 document.getElementById('lessonQuiz').addEventListener('submit',e=>{e.preventDefault();const fd=new FormData(e.currentTarget);let score=0;[1,2,3].forEach(n=>{if(fd.get('q'+n)==='0')score++});quizScore=score;const s=SaveOneSoulFormation.courseState(courseId);s.units=s.units||{};s.units[unitNo]=Object.assign({},s.units[unitNo],{quizScore:score});SaveOneSoulFormation.saveCourse(courseId,s);const r=document.getElementById('quizResult');r.hidden=false;r.textContent='Score: '+score+'/3. '+(score>=2?'Quiz requirement passed.':'Review the lesson and try again.');});
 document.getElementById('saveAssignment').addEventListener('click',()=>{SaveOneSoulFormation.saveDraft(courseId,unitNo,assignmentText.value.trim());document.getElementById('completionStatus').textContent='Assignment saved privately in this browser.';});
 document.getElementById('completeUnit').addEventListener('click',()=>{const text=assignmentText.value.trim();SaveOneSoulFormation.saveDraft(courseId,unitNo,text);const s=SaveOneSoulFormation.courseState(courseId),stored=(s.units&&s.units[unitNo])||{},score=quizScore==null?stored.quizScore:quizScore;if((score||0)<2){document.getElementById('completionStatus').textContent='Pass the quiz with at least 2/3 first.';return}if(text.length<80){document.getElementById('completionStatus').textContent='Your assignment needs at least 80 characters.';return}SaveOneSoulFormation.completeUnit(courseId,unitNo,{quizScore:score,assignment:text});document.getElementById('completionStatus').textContent='Unit complete. 2 formation credits recorded.';});
}
function qhtml(n,q,opts,correct){return '<div class="quiz-question"><strong>'+n+'. '+q+'</strong>'+opts.map((o,i)=>'<label><input type="radio" name="q'+n+'" value="'+i+'" required> '+o+'</label>').join('')+'</div>'}
load().catch(e=>{app.innerHTML='<div class="lesson-status"><strong>Lesson could not be loaded.</strong><br>'+e.message+'</div>'});
})();