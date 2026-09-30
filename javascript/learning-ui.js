/* Local navigation only: no analytics, CMS overrides, or user text collection. */
(() => {
  'use strict';
  try { if (localStorage.getItem('mercy-theme') === 'dark') document.body.classList.add('dark'); } catch (_) {}
  document.querySelector('.theme-btn')?.addEventListener('click', () => {
    document.body.classList.toggle('dark');
    try { localStorage.setItem('mercy-theme', document.body.classList.contains('dark') ? 'dark' : 'light'); } catch (_) {}
  });
  const menu = document.querySelector('.menu-btn'), nav = document.querySelector('#main-nav');
  menu?.addEventListener('click', () => { const open = nav.classList.toggle('open'); menu.setAttribute('aria-expanded', String(open)); });
  document.querySelectorAll('[data-year]').forEach(n => { n.textContent = new Date().getFullYear(); });
  if ('serviceWorker' in navigator) navigator.serviceWorker.register('../mercy-sw.js').catch(() => {});
})();
