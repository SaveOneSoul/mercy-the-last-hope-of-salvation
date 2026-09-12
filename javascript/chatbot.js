(() => {
  'use strict';
  const DEFAULT_API_BASE = 'https://mercy-api-h6icv7sk7a-el.a.run.app';
  const launcher = document.querySelector('.chat-launcher');
  const panel = document.querySelector('.chat-panel');
  const close = document.querySelector('[data-chat-close]');
  const form = document.querySelector('[data-chat-form]');
  const input = document.querySelector('[data-chat-input]');
  const messages = document.querySelector('[data-chat-messages]');
  if (!launcher || !panel || !form || !input || !messages) return;

  const isKh = location.pathname.includes('/kh/');
  const t = (en, kh) => isKh ? kh : en;

  function toggle(open) {
    panel.hidden = !open;
    launcher.setAttribute('aria-expanded', String(open));
    if (open) input.focus();
  }
  launcher.addEventListener('click', () => toggle(panel.hidden));
  close?.addEventListener('click', () => toggle(false));

  function add(text, who = 'bot') {
    const div = document.createElement('div');
    div.className = who === 'user' ? 'user-message' : 'bot-message';
    div.textContent = text;
    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
    return div;
  }

  function addSources(sources) {
    if (!Array.isArray(sources) || !sources.length) return;
    const box = document.createElement('div');
    box.className = 'bot-sources';
    const title = document.createElement('strong');
    title.textContent = t('Catholic sources:', 'Ki Catholic source:');
    box.appendChild(title);
    const ul = document.createElement('ul');
    for (const source of sources) {
      if (!source) continue;
      const li = document.createElement('li');
      const label = String(source.title || source.reference || 'Catholic source');
      if (source.url) {
        const a = document.createElement('a');
        a.href = source.url;
        a.target = '_blank';
        a.rel = 'noopener noreferrer';
        a.textContent = label;
        li.appendChild(a);
      } else {
        li.textContent = label;
      }
      ul.appendChild(li);
    }
    box.appendChild(ul);
    messages.appendChild(box);
    messages.scrollTop = messages.scrollHeight;
  }

  const catholicSignals = [
    'catholic','church','catechism','pope','bishop','priest','mass','eucharist','communion','confession',
    'reconciliation','baptism','confirmation','matrimony','sacrament','jesus','christ','trinity','holy spirit',
    'mary','our lady','rosary','chaplet','divine mercy','faustina','saint','bible','scripture','gospel','prayer',
    'charismatic','charis','pentecost','purgatory','sin','grace','salvation','mercy','novena','adoration'
  ];
  const localFacts = [
    {keys:['chaplet'], text:'The Divine Mercy Chaplet is prayed on ordinary Rosary beads. Use the Chaplet page for the approved sequence and source link.'},
    {keys:['rosary','mystery','mysteries'], text:'The Rosary has Joyful, Luminous, Sorrowful and Glorious Mysteries and is a Christ-centered Marian prayer of contemplation.'},
    {keys:['baptism in the holy spirit','baptism in spirit'], text:'In Catholic Charismatic Renewal, Baptism in the Holy Spirit is not another sacrament. CHARIS presents it as an experiential awakening or release of graces associated especially with Baptism and Confirmation.'},
    {keys:['eucharist','transubstantiation','real presence'], text:'Catholic teaching holds that Christ is truly, really and substantially present in the Eucharist; the Church uses the term transubstantiation for the change of the substance of bread and wine.'},
    {keys:['confession','reconciliation','absolution'], text:"The Sacrament of Penance and Reconciliation is the ordinary sacramental encounter with Christ's forgiveness after Baptism. For a personal confession or conscience question, speak directly with a priest."},
    {keys:['saint','saints','intercession'], text:'Catholics honor the saints as members of Christ and ask their intercession within the communion of saints; adoration belongs to God alone.'},
    {keys:['bible','scripture'], text:"Catholic Scripture study reads the Bible within the unity of Scripture, the Church's living Tradition and the analogy of faith, following Dei Verbum."},
    {keys:['holy spirit','gift','gifts'], text:'Catholic teaching names seven gifts of the Holy Spirit: wisdom, understanding, counsel, fortitude, knowledge, piety and fear of the Lord.'}
  ];

  function localCatholicAnswer(question) {
    const q = question.toLowerCase();
    const inScope = catholicSignals.some(term => q.includes(term));
    if (!inScope) {
      return {reply:t('Mercy Guide is limited to Roman Catholic faith, Scripture in Catholic context, doctrine, sacraments, prayer, saints, Divine Mercy and Catholic spiritual life. Please ask a Catholic-related question.','Mercy Guide ka long tang na ka bynta ka jingngeit Catholic, Scripture, doctrine, sacraments, jingduwai, ki riewkhuid, Divine Mercy bad ka jingim mynsiem Catholic.'), sources:[]};
    }
    const fact = localFacts.find(item => item.keys.some(k => q.includes(k)));
    if (fact) return {reply:fact.text, sources:[]};
    return {reply:t('The live Catholic AI could not be reached. Please try again when your connection is stable.','Ym lah ban poi sha live Catholic AI. Sngewbha pyrshang biang haba ka internet ka biang.'), sources:[]};
  }

  function apiBase() {
    const cfg = window.MERCY_SITE_CONFIG || {};
    return String(cfg.apiBaseUrl || DEFAULT_API_BASE).replace(/\/$/, '') || DEFAULT_API_BASE;
  }

  async function remoteAnswer(question) {
    const cfg = window.MERCY_SITE_CONFIG || {};
    if (cfg.enableRemoteAI === false) return null;
    const controller = typeof AbortController !== 'undefined' ? new AbortController() : null;
    const timer = controller ? setTimeout(() => controller.abort(), 110000) : null;
    try {
      const res = await fetch(apiBase() + '/api/chat', {
        method:'POST',
        headers:{'Content-Type':'application/json','Accept':'application/json'},
        body:JSON.stringify({message:question, language:isKh?'kha':'en'}),
        cache:'no-store',
        signal:controller ? controller.signal : undefined
      });
      if (!res.ok) {
        const err = new Error('HTTP ' + res.status);
        err.status = res.status;
        throw err;
      }
      return await res.json();
    } finally {
      if (timer) clearTimeout(timer);
    }
  }

  form.addEventListener('submit', async e => {
    e.preventDefault();
    const q = input.value.trim();
    if (!q) return;
    const submit = form.querySelector('button[type="submit"]');
    input.value = '';
    add(q, 'user');
    const pending = add(t('Connecting to Catholic AI…','Dang connect sha Catholic AI…'), 'bot');
    if (submit) submit.disabled = true;
    input.disabled = true;
    try {
      const result = await remoteAnswer(q);
      if (!result || !result.reply) throw new Error('empty_response');
      pending.textContent = result.reply;
      addSources(result.sources);
      if (result.needs_human_follow_up) {
        add(t('This question may need direct human pastoral follow-up. Please contact an appropriate priest or qualified professional when necessary.','Kane ka jingkylli ka lah ban donkam pastoral follow-up. Sngewbha contact ia u lyngdoh ne qualified professional katkum ka jingdonkam.'), 'bot');
      }
    } catch (err) {
      const fallback = localCatholicAnswer(q);
      pending.textContent = fallback.reply;
      addSources(fallback.sources);
      if (err && err.status === 429) {
        add(t('The live request limit has been reached. Please wait a minute and try again.','La poi sha ka request limit. Sngewbha ap shi minit bad pyrshang biang.'), 'bot');
      }
    } finally {
      if (submit) submit.disabled = false;
      input.disabled = false;
      input.focus();
      messages.scrollTop = messages.scrollHeight;
    }
  });
})();
