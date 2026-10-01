/* Authored lessons supplement the existing formation engine and reuse its progress API. */
(() => {
  'use strict';
  const F = () => window.SaveOneSoulFormation;
  function node(tag, text, cls) { const n = document.createElement(tag); if (text != null) n.textContent = text; if (cls) n.className = cls; return n; }
  function link(text, href) { const a = node('a', text, 'btn secondary'); a.href = href; return a; }
  function section(parent, title) { const s = node('section', null, 'lesson-section'); s.append(node('h2', title)); parent.append(s); return s; }
  function list(parent, values) { const ul = node('ul'); values.forEach(x => ul.append(node('li', x))); parent.append(ul); }
  function creditValue(course,total){ const n=Number(course.credits||0)/(total||1); return Number.isInteger(n)?n:Number(n.toFixed(2)); }
  function richSections(parent, unit){
    (unit.lectureSections||[]).forEach(block=>{ const sec=section(parent,block.title); (block.paragraphs||[]).forEach(p=>sec.append(node('p',p))); if(block.points?.length) list(sec,block.points); });
    if(unit.keyTerms?.length){ const sec=section(parent,'Key terms'); list(sec,unit.keyTerms.map(x=>typeof x==='string'?x:(x.term+': '+x.definition))); }
    if(unit.primaryTexts?.length){ const sec=section(parent,'Primary texts & close reading'); list(sec,unit.primaryTexts.map(x=>typeof x==='string'?x:(x.title+(x.note?' — '+x.note:'')))); }
    if(unit.methodNotes?.length){ const sec=section(parent,'Method notes'); list(sec,unit.methodNotes); }
    if(unit.researchTask){ const sec=section(parent,'Research task'); sec.append(node('p',unit.researchTask)); }
    if(unit.furtherReading?.length){ const sec=section(parent,'Further reading'); const ul=node('ul'); unit.furtherReading.forEach(s=>{const li=node('li'),a=node('a',s.title||s.url);a.href=s.url;if(String(s.url||'').startsWith('https://')){a.target='_blank';a.rel='noopener';}li.append(a);ul.append(li);});sec.append(ul); }
  }
  async function data(course) {
    const response = await fetch(course.contentFile);
    if (!response.ok) throw new Error('Course reading is unavailable. Try again when connected.');
    return response.json();
  }
  function questions(form, items) {
    items.forEach((q, i) => {
      const box = node('div', null, 'quiz-question'), field = node('fieldset');
      field.append(node('legend', `${i + 1}. ${q.question}`));
      q.options.forEach((choice, j) => {
        const label = node('label'), input = node('input');
        input.type = 'radio'; input.name = 'q' + i; input.value = j; input.required = true;
        label.append(input, document.createTextNode(' ' + choice)); field.append(label);
      });
      const feedback = node('p', null, 'quiz-feedback'); feedback.hidden = true; feedback.dataset.feedback = i;
      box.append(field, feedback); form.append(box);
    });
  }
  function grade(form, items) {
    const answers = new FormData(form); let score = 0;
    items.forEach((q, i) => {
      const correct = answers.get('q' + i) === String(q.correct); if (correct) score++;
      const feedback = form.querySelector(`[data-feedback="${i}"]`); feedback.hidden = false;
      feedback.textContent = (correct ? 'Correct. ' : 'Review: ') + q.explanation;
    });
    return score;
  }
  function save(action, status, success) {
    try { action(); status.textContent = success; return true; }
    catch (_) { status.textContent = 'This browser could not save progress. Enable site storage and try again. You can still read the lesson.'; return false; }
  }
  async function lesson(app, course, unitNo) {
    const content = await data(course), unit = content.units[unitNo - 1];
    if (!Number.isInteger(unitNo) || !unit) throw new Error('Choose a valid unit from the course overview.');
    const saved = F().courseState(course.id).units?.[unitNo] || {}, perUnit = creditValue(course, content.units.length);
    document.title = unit.title + ' · ' + course.title + ' · Mercy'; app.replaceChildren();
    const head = node('section', null, 'lesson-head');
    head.append(node('div', course.title + ' · Unit ' + unitNo + ' of ' + content.units.length, 'eyebrow'), node('h1', unit.title), node('span', unit.label, 'lesson-badge'), node('p', perUnit+' internal formation credit'+(perUnit===1?'':'s')+' · Structured self-study'));
    const main = node('article', null, 'lesson-main'); app.append(head, main);
    list(section(main, 'Learning objectives'), unit.objectives);
    const reading = section(main, 'Lesson'); unit.paragraphs.forEach(p => reading.append(node('p', p))); richSections(main,unit);
    const sources = section(main, 'Read the sources');
    const ul = node('ul'); unit.sources.forEach(s => { const li = node('li'), a = node('a', s.title); a.href = s.url; if (s.url.startsWith('https://')) { a.target = '_blank'; a.rel = 'noopener'; } li.append(a); ul.append(li); }); sources.append(ul);
    const quiz = section(main, 'Knowledge check'), form = node('form', null, 'lesson-quiz'); questions(form, unit.quiz);
    const check = node('button', 'Check answers', 'btn primary'); check.type = 'submit';
    const quizStatus = node('p', null, 'lesson-status'); quizStatus.setAttribute('role', 'status'); form.append(check, quizStatus); quiz.append(form);
    let quizScore = saved.quizScore ?? 0;
    form.addEventListener('submit', e => {
      e.preventDefault(); quizScore = grade(form, unit.quiz);
      save(() => { const state = F().courseState(course.id); state.units ||= {}; state.units[unitNo] = {...state.units[unitNo], quizScore, quizTotal: unit.quiz.length}; F().saveCourse(course.id, state); }, quizStatus, `Score: ${quizScore}/${unit.quiz.length}. ${quizScore === unit.quiz.length ? 'Knowledge check passed.' : 'Read the explanations and try again.'}`);
    });
    const assignment = section(main, 'Case exercise'); assignment.append(node('p', unit.assignment), node('p', 'Use a fictional case. Do not enter real names, client details or private health information. Your optional draft is stored only in this browser, where other users of this device may see it.'));
    const label = node('label', 'Your response (at least 120 characters)'); label.htmlFor = 'richAssignment';
    const text = node('textarea'); text.id = 'richAssignment'; text.rows = 7; text.maxLength = 6000; text.value = saved.assignment || ''; text.style.width = '100%';
    const actions = node('div', null, 'btns'), draft = node('button', 'Save draft', 'btn secondary'), complete = node('button', 'Complete unit', 'btn primary'), clear = node('button', 'Delete saved draft', 'btn secondary');
    [draft, complete, clear].forEach(b => b.type = 'button'); actions.append(draft, complete, clear);
    const status = node('p', saved.complete ? 'Unit completed. Your existing progress is retained.' : 'Answer both questions correctly and write your case response to complete this unit.', 'lesson-status'); status.setAttribute('role', 'status');
    assignment.append(label, text, actions, status);
    draft.addEventListener('click', () => save(() => F().saveDraft(course.id, unitNo, text.value.trim()), status, 'Draft saved on this device.'));
    clear.addEventListener('click', () => { if (save(() => F().saveDraft(course.id, unitNo, ''), status, 'Draft deleted. Completion progress is retained.')) text.value = ''; });
    complete.addEventListener('click', () => {
      if (quizScore < unit.quiz.length) { status.textContent = 'Answer both knowledge-check questions correctly first.'; return; }
      if (text.value.trim().length < 120) { status.textContent = 'Write at least 120 characters responding to the case exercise.'; return; }
      save(() => F().completeUnit(course.id, unitNo, {quizScore, quizTotal:unit.quiz.length, assignment:text.value.trim(), creditValue:perUnit}), status, 'Unit completed. '+perUnit+' internal formation credit'+(perUnit===1?'':'s')+' recorded. The response is self-directed practice, not a professionally marked assessment.');
    });
    const nav = node('div', null, 'btns');
    if (unitNo > 1) nav.append(link('Previous unit', `formation-lesson.html?course=${course.id}&unit=${unitNo-1}`));
    if (unitNo < content.units.length) nav.append(link('Next unit', `formation-lesson.html?course=${course.id}&unit=${unitNo+1}`));
    nav.append(link('Course overview', course.overview || course.source), link('My learning', 'formation-dashboard.html'));
    app.append(nav, node('p', content.creditNote, 'lesson-status'));
  }
  async function assessment(app, course, type) {
    const content = await data(course), items = content.assessments[type], passMark=Math.ceil(items.length*0.8); app.replaceChildren();
    const head = node('section', null, 'lesson-head'); head.append(node('div', course.title, 'eyebrow'), node('h1', type === 'mid' ? 'Mid-course review' : 'Final review'), node('p', 'Answer at least '+passMark+' of '+items.length+' questions correctly. This self-study check records learning, not professional competence.')); app.append(head);
    const form = node('form', null, 'lesson-main lesson-quiz'); questions(form, items);
    const submit = node('button', 'Check assessment', 'btn primary'); submit.type = 'submit';
    const status = node('p', null, 'lesson-status'); status.setAttribute('role', 'status'); form.append(submit, status); app.append(form);
    form.addEventListener('submit', e => { e.preventDefault(); const score = grade(form, items); save(() => F().setAssessment(course.id, type, score >= passMark, score), status, `Score: ${score}/${items.length}. ${score >= passMark ? 'Assessment passed and recorded.' : 'Review the explanations and try again.'}`); });
    app.append(link('My learning', 'formation-dashboard.html'), node('p', content.creditNote, 'lesson-status'));
  }
  window.MercyRichFormation = {lesson, assessment};
})();
