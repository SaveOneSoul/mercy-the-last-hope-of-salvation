
(() => {
  const root = document.documentElement;
  const saved = localStorage.getItem("mercy-theme");
  if (saved) root.dataset.theme = saved;

  document.querySelectorAll("[data-current-year]").forEach(el => el.textContent = new Date().getFullYear());

  const navToggle = document.querySelector(".nav-toggle");
  const nav = document.querySelector(".site-nav");
  if (navToggle && nav) {
    navToggle.addEventListener("click", () => {
      const isOpen = nav.classList.toggle("open");
      navToggle.setAttribute("aria-expanded", String(isOpen));
    });
  }

  const themeToggle = document.querySelector(".theme-toggle");
  if (themeToggle) {
    themeToggle.addEventListener("click", () => {
      const next = root.dataset.theme === "dark" ? "light" : "dark";
      root.dataset.theme = next;
      localStorage.setItem("mercy-theme", next);
    });
  }

  document.querySelectorAll("[data-mystery-tab]").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll("[data-mystery-tab]").forEach(b => b.setAttribute("aria-selected", "false"));
      document.querySelectorAll(".mystery-panel").forEach(p => p.classList.remove("active"));
      btn.setAttribute("aria-selected", "true");
      const panel = document.getElementById(btn.dataset.mysteryTab);
      if (panel) panel.classList.add("active");
    });
  });

  const bookSearch = document.querySelector("[data-book-search]");
  if (bookSearch) {
    bookSearch.addEventListener("input", () => {
      const q = bookSearch.value.trim().toLowerCase();
      document.querySelectorAll("[data-book]").forEach(book => {
        book.hidden = q && !book.dataset.book.toLowerCase().includes(q);
      });
    });
  }

  const cccSearch = document.querySelector("[data-ccc-search]");
  if (cccSearch) {
    cccSearch.addEventListener("input", () => {
      const q = cccSearch.value.trim().toLowerCase();
      document.querySelectorAll("[data-ccc-topic]").forEach(item => {
        item.hidden = q && !item.dataset.cccTopic.toLowerCase().includes(q);
      });
    });
  }

  // Legacy contact form. Normalize its older fields to the current Mercy API schema.
  const form = document.querySelector("[data-contact-form]");
  if (form) {
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const cfg = window.MERCY_SITE_CONFIG || {};
      const status = form.querySelector("[data-form-status]");
      const submit = form.querySelector('button[type="submit"]');
      const fd = new FormData(form);
      const raw = Object.fromEntries(fd.entries());
      const apiBase = String(cfg.apiBaseUrl || "https://mercy-api-h6icv7sk7a-el.a.run.app").replace(/\/$/, "");
      const topic = String(raw.topic || "Website message").trim();
      const phone = String(raw.phone || "").trim();
      const originalMessage = String(raw.message || "").trim();
      const payload = {
        name: String(raw.name || "").trim(),
        email: String(raw.email || "").trim(),
        subject: topic.slice(0, 160),
        message: (phone ? `WhatsApp / phone: ${phone}\n\n` : "") + originalMessage,
        website: ""
      };

      status.className = "form-status";
      if (!payload.name || !payload.email || originalMessage.length < 2) {
        status.classList.add("error");
        status.textContent = "Please enter your name, email address and message before submitting.";
        return;
      }

      if (submit) submit.disabled = true;
      status.textContent = "Sending securely…";

      try {
        const res = await fetch(apiBase + "/api/contact", {
          method: "POST",
          headers: {"Content-Type":"application/json", "Accept":"application/json"},
          body: JSON.stringify(payload),
          cache: "no-store"
        });
        const text = await res.text();
        let data = {};
        try { data = text ? JSON.parse(text) : {}; } catch (_) {}
        if (!res.ok) throw new Error(data.detail || ("Server returned " + res.status));
        status.classList.add("success");
        status.textContent = data.id
          ? `Thank you. Your message was received securely. Reference #${data.id}.`
          : "Thank you. Your message was received securely.";
        form.reset();
        return;
      } catch (err) {
        console.warn("Mercy API submission failed; using configured contact fallback.", err);
      } finally {
        if (submit) submit.disabled = false;
      }

      const subject = encodeURIComponent(`[Mercy Website] ${topic} from ${payload.name || "Visitor"}`);
      const message = encodeURIComponent(
`Name: ${payload.name || ""}
Email: ${payload.email || ""}
Phone/WhatsApp: ${phone}
Topic: ${topic}

Message:
${originalMessage}`
      );

      if (cfg.contactEmail) {
        window.location.href = `mailto:${cfg.contactEmail}?subject=${subject}&body=${message}`;
        status.classList.add("success");
        status.textContent = "The Cloud submission was unavailable, so your email app has been opened with the message prepared.";
      } else if (cfg.whatsappNumber) {
        window.open(`https://wa.me/${cfg.whatsappNumber}?text=${message}`, "_blank", "noopener");
        status.classList.add("success");
        status.textContent = "The Cloud submission was unavailable, so WhatsApp has been opened with the message prepared.";
      } else {
        status.classList.add("error");
        status.textContent = "Your message could not be delivered right now. Please try again later.";
      }
    });
  }
})();
