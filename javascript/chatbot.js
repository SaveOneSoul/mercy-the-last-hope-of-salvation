(() => {
  const launcher = document.querySelector(".chat-launcher");
  const panel = document.querySelector(".chat-panel");
  const close = document.querySelector("[data-chat-close]");
  const form = document.querySelector("[data-chat-form]");
  const input = document.querySelector("[data-chat-input]");
  const messages = document.querySelector("[data-chat-messages]");
  if (!launcher || !panel || !form || !input || !messages) return;

  function toggle(open) {
    panel.hidden = !open;
    launcher.setAttribute("aria-expanded", String(open));
    if (open) input.focus();
  }
  launcher.addEventListener("click", () => toggle(panel.hidden));
  close?.addEventListener("click", () => toggle(false));

  function add(text, who="bot") {
    const div = document.createElement("div");
    div.className = who === "user" ? "user-message" : "bot-message";
    div.textContent = text;
    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
    return div;
  }

  function addSources(sources) {
    if (!sources?.length) return;
    const box = document.createElement("div");
    box.className = "bot-sources";
    const title = document.createElement("strong");
    title.textContent = "Catholic sources:";
    box.appendChild(title);
    const ul = document.createElement("ul");
    for (const source of sources) {
      const li = document.createElement("li");
      const a = document.createElement("a");
      a.href = source.url;
      a.target = "_blank";
      a.rel = "noopener";
      a.textContent = source.title;
      li.appendChild(a);
      ul.appendChild(li);
    }
    box.appendChild(ul);
    messages.appendChild(box);
    messages.scrollTop = messages.scrollHeight;
  }

  function getClientId() {
    let id = localStorage.getItem("mercy-client-id");
    if (!id) {
      id = (crypto.randomUUID?.() || `mercy-${Date.now()}-${Math.random().toString(16).slice(2)}`);
      localStorage.setItem("mercy-client-id", id);
    }
    return id;
  }

  const catholicSignals = [
    "catholic","church","catechism","pope","bishop","priest","mass","eucharist","communion","confession",
    "reconciliation","baptism","confirmation","matrimony","sacrament","jesus","christ","trinity","holy spirit",
    "mary","our lady","rosary","chaplet","divine mercy","faustina","saint","bible","scripture","gospel","prayer",
    "charismatic","charis","pentecost","purgatory","sin","grace","salvation","mercy","novena","adoration"
  ];
  const localFacts = [
    {keys:["chaplet"], text:"The Divine Mercy Chaplet is prayed on ordinary Rosary beads. Use the Chaplet page for the approved sequence and source link."},
    {keys:["rosary","mystery","mysteries"], text:"The Rosary has Joyful, Luminous, Sorrowful and Glorious Mysteries and is a Christ-centered Marian prayer of contemplation."},
    {keys:["baptism in the holy spirit","baptism in spirit"], text:"In Catholic Charismatic Renewal, Baptism in the Holy Spirit is not another sacrament. CHARIS presents it as an experiential awakening or release of graces associated especially with Baptism and Confirmation."},
    {keys:["eucharist","transubstantiation","real presence"], text:"Catholic teaching holds that Christ is truly, really and substantially present in the Eucharist; the Church uses the term transubstantiation for the change of the substance of bread and wine."},
    {keys:["confession","reconciliation","absolution"], text:"The Sacrament of Penance and Reconciliation is the ordinary sacramental encounter with Christ's forgiveness after Baptism. For a personal confession or conscience question, speak directly with a priest."},
    {keys:["saint","saints","intercession"], text:"Catholics honor the saints as members of Christ and ask their intercession within the communion of saints; adoration belongs to God alone."},
    {keys:["bible","scripture"], text:"Catholic Scripture study reads the Bible within the unity of Scripture, the Church's living Tradition and the analogy of faith, following Dei Verbum."},
    {keys:["holy spirit","gift","gifts"], text:"Catholic teaching names seven gifts of the Holy Spirit: wisdom, understanding, counsel, fortitude, knowledge, piety and fear of the Lord."},
  ];

  function localCatholicAnswer(question) {
    const q = question.toLowerCase();
    const inScope = catholicSignals.some(term => q.includes(term));
    if (!inScope) {
      return {reply:"Mercy Guide is limited to Roman Catholic faith, Scripture in Catholic context, doctrine, sacraments, prayer, saints, Divine Mercy and Catholic spiritual life. Please ask a Catholic-related question.", sources:[]};
    }
    const fact = localFacts.find(item => item.keys.some(k => q.includes(k)));
    if (fact) return {reply:fact.text, sources:[]};
    return {reply:"This appears to be a Catholic question, but the offline starter does not contain enough approved source material to answer it faithfully. Please use the contact form or enable the secure Catholic AI backend.", sources:[]};
  }

  async function remoteAnswer(question) {
    const cfg = window.MERCY_SITE_CONFIG || {};
    if (!cfg.enableRemoteAI || !cfg.apiBaseUrl) return null;
    try {
      let recaptchaToken = null;
      if (cfg.recaptchaEnabled) {
        recaptchaToken = await window.MercyRecaptcha.execute("chat");
      }

      const res = await fetch(cfg.apiBaseUrl.replace(/\/$/, "") + "/api/chat", {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({
          message:question,
          client_id:getClientId(),
          recaptcha_token:recaptchaToken
        })
      });
      if (!res.ok) return null;
      return await res.json();
    } catch {
      return null;
    }
  }

  form.addEventListener("submit", async e => {
    e.preventDefault();
    const q = input.value.trim();
    if (!q) return;
    input.value = "";
    add(q, "user");
    const pending = add("Checking approved Catholic sources…", "bot");
    const result = await remoteAnswer(q) || localCatholicAnswer(q);
    pending.textContent = result.reply;
    addSources(result.sources);
    if (result.needs_human_follow_up) {
      add("This question may need direct human pastoral follow-up. You can use the Prayer Requests & Contact page.", "bot");
    }
    messages.scrollTop = messages.scrollHeight;
  });
})();
