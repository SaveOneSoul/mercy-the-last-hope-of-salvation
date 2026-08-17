
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

  // Rosary mystery tabs
  document.querySelectorAll("[data-mystery-tab]").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll("[data-mystery-tab]").forEach(b => b.setAttribute("aria-selected", "false"));
      document.querySelectorAll(".mystery-panel").forEach(p => p.classList.remove("active"));
      btn.setAttribute("aria-selected", "true");
      const panel = document.getElementById(btn.dataset.mysteryTab);
      if (panel) panel.classList.add("active");
    });
  });

  // Bible book filter
  const bookSearch = document.querySelector("[data-book-search]");
  if (bookSearch) {
    bookSearch.addEventListener("input", () => {
      const q = bookSearch.value.trim().toLowerCase();
      document.querySelectorAll("[data-book]").forEach(book => {
        book.hidden = q && !book.dataset.book.toLowerCase().includes(q);
      });
    });
  }


  // Catechism topic filter
  const cccSearch = document.querySelector("[data-ccc-search]");
  if (cccSearch) {
    cccSearch.addEventListener("input", () => {
      const q = cccSearch.value.trim().toLowerCase();
      document.querySelectorAll("[data-ccc-topic]").forEach(item => {
        item.hidden = q && !item.dataset.cccTopic.toLowerCase().includes(q);
      });
    });
  }

  // Contact form: API first, then email/WhatsApp fallback.
  const form = document.querySelector("[data-contact-form]");
  if (form) {
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const cfg = window.MERCY_SITE_CONFIG || {};
      const status = form.querySelector("[data-form-status]");
      const fd = new FormData(form);
      const payload = Object.fromEntries(fd.entries());
      status.className = "form-status";
      status.textContent = "Preparing your message…";

      if (cfg.apiBaseUrl) {
        try {
          const res = await fetch(cfg.apiBaseUrl.replace(/\/$/, "") + "/api/contact", {
            method: "POST",
            headers: {"Content-Type":"application/json"},
            body: JSON.stringify(payload)
          });
          if (!res.ok) throw new Error("Server returned " + res.status);
          const data = await res.json();
          status.classList.add("success");
          status.textContent = data.automatic_reply
            ? `Submitted successfully. Automatic Catholic reply: ${data.automatic_reply}`
            : "Thank you. Your message has been submitted successfully.";
          form.reset();
          return;
        } catch (err) {
          console.warn("API submission failed; attempting fallback.", err);
        }
      }

      const subject = encodeURIComponent(`[Mercy Website] ${payload.topic || "New message"} from ${payload.name || "Visitor"}`);
      const message = encodeURIComponent(
`Name: ${payload.name || ""}
Email: ${payload.email || ""}
Phone/WhatsApp: ${payload.phone || ""}
Topic: ${payload.topic || ""}

Message:
${payload.message || ""}`
      );

      if (cfg.contactEmail) {
        window.location.href = `mailto:${cfg.contactEmail}?subject=${subject}&body=${message}`;
        status.classList.add("success");
        status.textContent = "Your email app has been opened with the message prepared.";
      } else if (cfg.whatsappNumber) {
        window.open(`https://wa.me/${cfg.whatsappNumber}?text=${message}`, "_blank", "noopener");
        status.classList.add("success");
        status.textContent = "WhatsApp has been opened with the message prepared.";
      } else {
        status.classList.add("error");
        status.textContent = "Contact delivery is not configured yet. Set contactEmail or whatsappNumber in javascript/config.js, or connect the backend API.";
      }
    });
  }
})();
