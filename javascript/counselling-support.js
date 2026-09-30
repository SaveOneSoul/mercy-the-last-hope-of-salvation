(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const personal = document.body.dataset.supportMode === 'personal';
  const base = String(window.MERCY_SITE_CONFIG?.apiBaseUrl || '').replace(/\/$/, '');
  const history = []; let controller = null, generation = 0, available = false, busy = false;
  const status = $('supportStatus'), messages = $('supportMessages'), input = $('supportInput'), send = $('supportSend');
  const goalKey = 'mercyCompanionGoalV1';
  const goals = new Set(['study', 'stress', 'connection', 'routine']);
  const urgent = 'If you or someone else is in immediate danger, may act on thoughts of self-harm or harm to others, or needs urgent medical help, contact local emergency services now. In India call 112; for mental-health support call Tele-MANAS on 14416. If safe, ask a trusted person nearby to stay with you. Outside India use local emergency or crisis services. This website cannot monitor your safety or contact emergency help.';
  function message(label, text, kind) {
    const item = document.createElement('div'); item.className = 'care-message ' + (kind || '');
    const heading = document.createElement('strong'); heading.textContent = label;
    item.append(heading, document.createTextNode(text)); messages.append(item); messages.scrollTop = messages.scrollHeight;
  }
  function updateButton() { send.disabled = busy || !available; }
  function clearSession(clearGoal = false) {
    generation++; controller?.abort(); controller = null; busy = false;
    history.splice(0); messages.replaceChildren(); input.value = '';
    $('supportConsent').checked = false; $('supportAdult').checked = false; $('supportFaith').checked = false;
    if ($('checkIn')) $('checkIn').value = '';
    if (clearGoal && $('personalGoal')) { $('personalGoal').value = ''; $('rememberGoal').checked = false; try { localStorage.removeItem(goalKey); } catch (_) {} }
    status.textContent = 'Conversation cleared from this page. Clearing cannot retract information already sent to the provider. ' + (available ? 'You can start again after giving consent.' : 'Guided exercises remain available.'); updateButton();
  }
  $('clearSupport').addEventListener('click', () => clearSession(true));
  // Do not preserve a transcript in back/forward cache or hidden form restoration.
  window.addEventListener('pagehide', () => clearSession(false));
  window.addEventListener('pageshow', event => { if (event.persisted) clearSession(false); });
  $('supportConsent').addEventListener('change', () => { if (!$('supportConsent').checked && busy) { generation++; controller?.abort(); busy = false; updateButton(); status.textContent = 'Request stopped. Previously transmitted information cannot be recalled.'; } });
  $('supportAdult').addEventListener('change', () => { if (!$('supportAdult').checked && busy) { generation++; controller?.abort(); busy = false; updateButton(); status.textContent = 'Request stopped.'; } });
  if (personal) {
    try { const saved = localStorage.getItem(goalKey); if (goals.has(saved)) { $('personalGoal').value = saved; $('rememberGoal').checked = true; } } catch (_) {}
    function saveGoal() {
      try {
        if ($('rememberGoal').checked && goals.has($('personalGoal').value)) localStorage.setItem(goalKey, $('personalGoal').value);
        else localStorage.removeItem(goalKey);
        $('goalStatus').textContent = $('rememberGoal').checked ? 'Only the chosen goal category is saved on this device.' : 'Goal will not be remembered after leaving this page.';
      } catch (_) { $('rememberGoal').checked = false; $('goalStatus').textContent = 'Browser storage is unavailable; the goal lasts for this visit only.'; }
    }
    $('rememberGoal').addEventListener('change', saveGoal); $('personalGoal').addEventListener('change', saveGoal);
    $('makeCheckIn').addEventListener('click', () => {
      const goal = $('personalGoal').selectedOptions[0].textContent, mood = $('checkIn').value;
      input.value = 'I would like to reflect on ' + (goals.has($('personalGoal').value) ? goal.toLowerCase() : 'one manageable step today') + (mood ? '. Today feels ' + mood : '') + '. Please help me choose a small next step.'; input.focus();
      status.textContent = 'Check-in prepared. Review it before sending; nothing has been sent.';
    });
  }
  const practices = {
    grounding: 'A brief grounding pause\nIf you would like, notice where your feet or body meet a stable surface. Look around and name three things you can see. Notice one sound. Choose one small action for the next few minutes. Keep your eyes open if that feels better. Stop if the exercise feels uncomfortable.',
    nextstep: 'Choose one manageable step\nWhat needs your attention today? Pick an action small enough to begin in two minutes, such as opening a book or asking a trusted person for a conversation. Decide when to try it. If it does not happen, notice the barrier and make the step smaller; a missed attempt does not define you.',
    connection: 'Prepare for a human conversation\nChoose someone you trust. You could say: “I have been finding things difficult. Could you listen for a few minutes or help me find support?” You can decide how much to share. For ongoing distress, consider a qualified counsellor or mental-health professional.',
    reflection: 'A gentle reflection\nName the feeling you notice without judging it. What matters to you in this situation? What part is within your control today? You do not need to solve everything now. Consider one kind action towards yourself or someone else.'
  };
  document.querySelectorAll('[data-practice]').forEach(button => button.addEventListener('click', () => { $('practiceResult').textContent = practices[button.dataset.practice]; }));
  $('supportForm').addEventListener('submit', async event => {
    event.preventDefault(); if (busy || !available || !event.currentTarget.reportValidity()) return;
    const text = input.value.trim(); if (text.length < 2) { status.textContent = 'Write at least two characters.'; return; }
    const screening = text.normalize('NFKC').replace(/[\u200B-\u200D\uFEFF]/g, '');
    if (/suicid|self[\s-]*harm|kill\s+myself|want to die|end my life|can.?t stay safe|आत्महत्या|pyniap.*(?:alade|ia lade)/i.test(screening)) {
      message('Safety guidance · not an AI response', urgent); status.textContent = 'Human support is the next step. This message was not sent to the AI provider.'; input.value = ''; $('human-help').focus(); return;
    }
    const snapshot = generation; busy = true; updateButton(); controller = new AbortController();
    const active = controller, timeout = setTimeout(() => active.abort(), 115000);
    message('You', text, 'user'); input.value = ''; status.textContent = 'Sending to the AI support service…';
    try {
      const response = await fetch(base + '/api/counselling/chat', {method:'POST', cache:'no-store', credentials:'omit', referrerPolicy:'no-referrer', signal:active.signal, headers:{'Content-Type':'application/json'}, body:JSON.stringify({message:text, history:history.slice(-8), mode:personal?'personal':'support', goal:personal?$('personalGoal').value:'', consent:$('supportConsent').checked, adult:$('supportAdult').checked, faith:$('supportFaith').checked})});
      if (!response.ok) throw new Error(response.status === 429 ? 'Please wait before sending again. The service has a limited daily allowance.' : 'AI support is unavailable right now. Use a guided exercise or contact a person you trust.');
      const result = await response.json(); if (snapshot !== generation) return;
      if (typeof result.reply !== 'string' || !['ai','urgent_support','human_support'].includes(result.kind)) throw new Error('The service could not provide a reply. Please try human support.');
      message(result.kind === 'ai' ? (personal ? 'Personal companion · AI' : 'Counselling support · AI') : 'Human-support guidance', result.reply);
      if (result.kind === 'ai') { history.push({role:'user',content:text}, {role:'assistant',content:result.reply.slice(0,2000)}); if (history.length > 8) history.splice(0, history.length - 8); }
      else history.splice(0);
      status.textContent = result.kind === 'ai' ? 'AI can make mistakes. Consider what fits and seek qualified help when needed.' : 'Please use the human-help options below. This tool cannot monitor an emergency.';
      if (result.kind !== 'ai') $('human-help').focus();
    } catch (error) { if (snapshot === generation) status.textContent = error.name === 'AbortError' ? 'The request timed out or was stopped. Please try a guided exercise or human support.' : error.message; }
    finally { clearTimeout(timeout); if (snapshot === generation) { busy = false; controller = null; updateButton(); } }
  });
  async function checkAvailability() {
    if (!base) { status.textContent = 'AI support is not connected. You can use the guided exercises below.'; return; }
    try {
      const response = await fetch(base + '/api/counselling/status', {cache:'no-store',credentials:'omit',referrerPolicy:'no-referrer',signal:AbortSignal.timeout(8000)});
      if (!response.ok) throw new Error('unavailable');
      const result = await response.json(); available = result.available === true;
      status.textContent = available ? 'AI support is connected. Read the privacy note and give consent before sending.' : 'AI support is not activated yet. Guided exercises and human-help information are ready to use.';
    } catch (_) { status.textContent = 'AI support is currently unavailable. Guided exercises work without an AI connection.'; }
    updateButton();
  }
  checkAvailability();
})();
