(() => {
  'use strict';
  const reader = document.querySelector('.prayer-reader');
  const status = document.querySelector('[data-reader-status]');
  let size = 1.1;
  document.querySelectorAll('[data-font]').forEach(b => b.addEventListener('click', () => {
    size = Math.min(1.8, Math.max(.95, size + Number(b.dataset.font)));
    reader.style.setProperty('--reader-size', size + 'rem');
  }));
  document.querySelector('[data-share-prayer]')?.addEventListener('click', async () => {
    try {
      if (navigator.share) await navigator.share({title: document.title, url: location.href});
      else { await navigator.clipboard.writeText(location.href); status.textContent = 'Page link copied. Paste it in your preferred app.'; }
    } catch (e) { if (e.name !== 'AbortError') status.textContent = 'Use the WhatsApp link or copy this page’s address to share.'; }
  });
  const whatsapp = document.querySelector('[data-whatsapp]');
  const updateShare = () => { if (whatsapp) whatsapp.href = 'https://wa.me/?text=' + encodeURIComponent(document.title + '\n' + location.href); };
  updateShare();
  const day = document.querySelector('#novenaDay');
  if (!day) return;
  const key = 'mercyNovena54V1';
  let saved = {day: 1, complete: []}, storageOK = true;
  try { const value = JSON.parse(localStorage.getItem(key) || 'null'); if (value && typeof value === 'object') saved = {day: Number(value.day) || 1, complete: Array.isArray(value.complete) ? value.complete.filter(n => Number.isInteger(n) && n >= 1 && n <= 54) : []}; } catch (_) { storageOK = false; }
  const write = () => { try { localStorage.setItem(key, JSON.stringify(saved)); } catch (_) { storageOK = false; } };
  const candidate = Number(new URL(location.href).searchParams.get('day')) || saved.day;
  const initial = Number.isInteger(candidate) ? candidate : 1;
  for (let i = 1; i <= 54; i++) { const o = document.createElement('option'); o.value = i; o.textContent = 'Day ' + i; day.append(o); }
  day.value = String(Math.min(54, Math.max(1, initial)));
  function render() {
    const n = Number(day.value), phase = n <= 27 ? 'petition' : 'thanksgiving', mystery = ['joyful','sorrowful','glorious'][(n - 1) % 3];
    saved.day = n;
    document.querySelectorAll('[data-mystery]').forEach(s => { s.hidden = s.dataset.mystery !== mystery; });
    document.querySelectorAll('[data-phase]').forEach(s => { s.hidden = s.dataset.phase !== phase; });
    document.querySelector('#novenaSummary').textContent = 'Day ' + n + ' · ' + (phase === 'petition' ? 'Petition' : 'Thanksgiving') + ' · ' + mystery[0].toUpperCase() + mystery.slice(1) + ' Mysteries';
    document.querySelector('#novenaProgress').value = new Set(saved.complete).size;
    document.querySelector('#novenaProgressText').textContent = new Set(saved.complete).size + ' of 54 days marked complete.';
    const complete = document.querySelector('#novenaComplete'); complete.textContent = saved.complete.includes(n) ? 'Mark this day unfinished' : 'Mark this day complete';
    document.querySelector('#novenaPrevious').disabled = n === 1;
    document.querySelector('#novenaNext').disabled = n === 54;
    const u = new URL(location.href); u.searchParams.set('day', n); history.replaceState(null, '', u); updateShare();
    write();
    if (!storageOK) status.textContent = 'Progress is available for this visit only because browser storage is unavailable.';
  }
  day.addEventListener('change', render);
  for (const [id, diff] of [['novenaPrevious', -1], ['novenaNext', 1]]) document.getElementById(id).addEventListener('click', () => { day.value = Number(day.value) + diff; render(); });
  document.querySelector('#novenaComplete').addEventListener('click', () => { const n = Number(day.value); saved.complete = saved.complete.includes(n) ? saved.complete.filter(x => x !== n) : [...saved.complete, n]; render(); });
  document.querySelector('#novenaReset').addEventListener('click', () => { if (confirm('Clear the 54-day progress saved on this device?')) { saved = {day:1,complete:[]}; day.value = '1'; render(); } });
  render();
})();
