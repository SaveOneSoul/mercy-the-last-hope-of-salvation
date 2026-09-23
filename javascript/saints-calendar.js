(() => {
  const entries = [...document.querySelectorAll('.saint-list article.saint-item[id]')].map(article => {
    const source = article.querySelector('.saint-source a')?.href || '';
    const match = source.match(/\/saints\/(\d{2})\/(\d{2})\.html/);
    return { id: article.id, name: article.querySelector('h3')?.textContent.trim() || '',
      date: match ? `${match[1]}-${match[2]}` : null,
      summary: [...article.querySelectorAll(':scope > p')].find(p => !p.classList.contains('saint-source'))?.textContent.trim() || '' };
  });
  const now = new Date(), today = `${String(now.getMonth()+1).padStart(2,'0')}-${String(now.getDate()).padStart(2,'0')}`;
  const dateEl = document.getElementById('saints-today-date'), target = document.getElementById('saints-today');
  dateEl.textContent = new Intl.DateTimeFormat(undefined,{weekday:'long',month:'long',day:'numeric'}).format(now);
  const found = entries.filter(entry => entry.date === today);
  target.replaceChildren();
  if (!found.length) {const p=document.createElement('p');p.textContent='No saint in this featured selection has a feast listed today. Browse the full Church calendar below.';target.append(p)}
  found.forEach(entry => {const p=document.createElement('p'),link=document.createElement('a');link.href=`saint.html?id=${encodeURIComponent(entry.id)}`;link.className='btn secondary';link.textContent=`${entry.name} — read story`;p.append(link);target.append(p)});
  document.getElementById('saints-calendar-download')?.addEventListener('click',() => {
    const escape = value => value.replace(/\\/g,'\\\\').replace(/;/g,'\\;').replace(/,/g,'\\,').replace(/\r?\n/g,'\\n');
    const lines=['BEGIN:VCALENDAR','VERSION:2.0','PRODID:-//Save One Soul//Featured Saints//EN','CALSCALE:GREGORIAN','METHOD:PUBLISH','X-WR-CALNAME:Featured Saints - Save One Soul'];
    for(const entry of entries.filter(e=>e.date)){
      const [month,day]=entry.date.split('-').map(Number), year=month===2&&day===29?2028:2026;
      const start=`${year}${String(month).padStart(2,'0')}${String(day).padStart(2,'0')}`;
      const next=new Date(Date.UTC(year,month-1,day+1)).toISOString().slice(0,10).replace(/-/g,'');
      lines.push('BEGIN:VEVENT',`UID:${entry.id}@saveonesoul.github.io`,`DTSTART;VALUE=DATE:${start}`,`DTEND;VALUE=DATE:${next}`,'RRULE:FREQ=YEARLY',`SUMMARY:${escape(entry.name)} - feast day`,`DESCRIPTION:${escape(entry.summary)}\\nSee https://saveonesoul.github.io/mercy-the-last-hope-of-salvation/pages/saint.html?id=${entry.id}`,'BEGIN:VALARM','TRIGGER:-PT9H','ACTION:DISPLAY',`DESCRIPTION:${escape(entry.name)} - feast day`,'END:VALARM','END:VEVENT');
    }
    lines.push('END:VCALENDAR');
    const blob=new Blob([lines.join('\r\n')+'\r\n'],{type:'text/calendar;charset=utf-8'}),link=document.createElement('a');
    link.href=URL.createObjectURL(blob);link.download='save-one-soul-featured-saints.ics';link.click();setTimeout(()=>URL.revokeObjectURL(link.href),1000);
  });
})();
