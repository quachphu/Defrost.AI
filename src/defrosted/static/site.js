/* ═══════════════════════════════════════════════════════════════
   Defrost.AI — shared site JS
   Mobile nav drawer · cookie-consent banner · scroll reveal ·
   FAQ accordion · generic form handler (placeholder endpoints)
   ═══════════════════════════════════════════════════════════════ */
(function () {
  'use strict';

  /* ────────────────────────────────────────
     Mobile nav drawer — built from the existing desktop nav markup,
     so pages don't duplicate menu HTML.
  ──────────────────────────────────────── */
  function initMobileNav() {
    var nav = document.querySelector('nav');
    if (!nav || nav.querySelector('.nav-burger')) return;
    var actions = nav.querySelector('.nav-actions') || nav;

    var burger = document.createElement('button');
    burger.className = 'nav-burger';
    burger.setAttribute('aria-label', 'Open menu');
    burger.setAttribute('aria-expanded', 'false');
    burger.innerHTML = '<span></span><span></span><span></span>';
    actions.appendChild(burger);

    var menu = document.createElement('div');
    menu.className = 'mobile-menu';
    menu.setAttribute('aria-label', 'Mobile menu');

    // Clone dropdown groups
    nav.querySelectorAll('.nav-item').forEach(function (item) {
      var label = item.querySelector('.nav-link');
      var drop = item.querySelector('.nav-dropdown');
      if (!drop) return;
      var group = document.createElement('div');
      group.className = 'mm-group';
      var title = document.createElement('div');
      title.className = 'mm-group-title';
      title.textContent = label ? label.textContent.replace('▼', '').trim() : '';
      group.appendChild(title);
      drop.querySelectorAll('a').forEach(function (a) {
        group.appendChild(a.cloneNode(true));
      });
      menu.appendChild(group);
    });

    // Clone action buttons (log in / get started)
    var mmActions = document.createElement('div');
    mmActions.className = 'mm-actions';
    actions.querySelectorAll('a, button').forEach(function (el) {
      if (el === burger) return;
      var clone = el.cloneNode(true);
      if (el.tagName === 'BUTTON' && el.getAttribute('onclick')) {
        clone.setAttribute('onclick', el.getAttribute('onclick'));
      }
      mmActions.appendChild(clone);
    });
    menu.appendChild(mmActions);
    document.body.appendChild(menu);

    function setOpen(open) {
      menu.classList.toggle('open', open);
      burger.setAttribute('aria-expanded', String(open));
      burger.setAttribute('aria-label', open ? 'Close menu' : 'Open menu');
      document.body.style.overflow = open ? 'hidden' : '';
    }
    burger.addEventListener('click', function () {
      setOpen(!menu.classList.contains('open'));
    });
    menu.addEventListener('click', function (e) {
      if (e.target.tagName === 'A') setOpen(false);
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && menu.classList.contains('open')) {
        setOpen(false);
        burger.focus();
      }
    });
  }

  /* ────────────────────────────────────────
     Cookie consent banner (California/GDPR-aware, category toggles).
     Stores {essential:true, analytics:bool, marketing:bool} in localStorage.
     NOTE: no analytics/marketing scripts are wired yet — when they are,
     gate them on window.defrostCookiePrefs(). Copy is placeholder —
     [[LEGAL REVIEW REQUIRED]].
  ──────────────────────────────────────── */
  var CONSENT_KEY = 'defrost_cookie_consent';

  window.defrostCookiePrefs = function () {
    try { return JSON.parse(localStorage.getItem(CONSENT_KEY)); } catch (e) { return null; }
  };

  function saveConsent(analytics, marketing) {
    localStorage.setItem(CONSENT_KEY, JSON.stringify({
      essential: true, analytics: !!analytics, marketing: !!marketing, ts: Date.now()
    }));
  }

  function buildBanner() {
    var el = document.createElement('div');
    el.className = 'cookie-banner';
    el.setAttribute('role', 'dialog');
    el.setAttribute('aria-label', 'Cookie preferences');
    el.innerHTML =
      '<h2>Cookies &amp; privacy</h2>' +
      '<p>We use essential cookies to make Defrost.AI work. With your consent, we may also use analytics cookies to understand how the site is used. We do not use advertising cookies today. See our <a href="/legal/cookies">Cookie Policy</a>.</p>' +
      '<div class="cb-toggles">' +
        '<div class="cb-row"><span><span class="cb-name">Essential</span><br><span class="cb-desc">Required for login and core features. Always on.</span></span><input type="checkbox" checked disabled aria-label="Essential cookies (always on)"></div>' +
        '<div class="cb-row"><span><span class="cb-name">Analytics</span><br><span class="cb-desc">Anonymous usage measurement. Off by default.</span></span><input type="checkbox" id="cb-analytics" aria-label="Analytics cookies"></div>' +
        '<div class="cb-row"><span><span class="cb-name">Marketing</span><br><span class="cb-desc">Not used today; reserved for the future.</span></span><input type="checkbox" id="cb-marketing" aria-label="Marketing cookies"></div>' +
      '</div>' +
      '<div class="cb-actions">' +
        '<button class="btn-lg btn-filled" id="cb-accept">Accept all</button>' +
        '<button class="btn-lg btn-outline" id="cb-essential">Essential only</button>' +
        '<button class="cb-link-btn" id="cb-prefs">Preferences</button>' +
      '</div>';

    el.querySelector('#cb-accept').addEventListener('click', function () {
      saveConsent(true, true); el.remove();
    });
    el.querySelector('#cb-essential').addEventListener('click', function () {
      saveConsent(false, false); el.remove();
    });
    el.querySelector('#cb-prefs').addEventListener('click', function () {
      var t = el.querySelector('.cb-toggles');
      var open = t.classList.toggle('open');
      if (open) {
        var btn = el.querySelector('#cb-prefs');
        btn.textContent = 'Save preferences';
        btn.addEventListener('click', function onSave() {
          saveConsent(el.querySelector('#cb-analytics').checked, el.querySelector('#cb-marketing').checked);
          el.remove();
          btn.removeEventListener('click', onSave);
        });
      }
    });
    return el;
  }

  function initCookieBanner() {
    if (window.defrostCookiePrefs()) return;
    document.body.appendChild(buildBanner());
  }

  // "Manage cookie preferences" links (e.g. on /legal/cookies) reopen the banner.
  window.showCookiePreferences = function () {
    var existing = document.querySelector('.cookie-banner');
    if (existing) existing.remove();
    var b = buildBanner();
    document.body.appendChild(b);
    b.querySelector('#cb-prefs').click();
  };

  /* ────────────────────────────────────────
     Scroll reveal
  ──────────────────────────────────────── */
  function initReveal() {
    var els = document.querySelectorAll('.reveal,.reveal-l,.reveal-r');
    if (!els.length) return;
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      els.forEach(function (el) { el.classList.add('visible'); });
      return;
    }
    var obs = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (!e.isIntersecting) return;
        var d = parseFloat(e.target.style.transitionDelay || 0) * 1000;
        setTimeout(function () { e.target.classList.add('visible'); }, d);
        obs.unobserve(e.target);
      });
    }, { threshold: 0.1 });
    els.forEach(function (el) { obs.observe(el); });
  }

  /* ────────────────────────────────────────
     FAQ accordion — markup: .acc-item > button.acc-btn + .acc-panel
  ──────────────────────────────────────── */
  function initAccordions() {
    document.querySelectorAll('.acc-item').forEach(function (item) {
      var btn = item.querySelector('.acc-btn');
      var panel = item.querySelector('.acc-panel');
      if (!btn || !panel) return;
      btn.setAttribute('aria-expanded', 'false');
      btn.addEventListener('click', function () {
        var open = item.classList.toggle('open');
        btn.setAttribute('aria-expanded', String(open));
      });
    });
  }

  /* ────────────────────────────────────────
     Generic form handler.
     Usage: <form data-endpoint="/api/forms/contact"> with .field wrappers.
     PLACEHOLDER ENDPOINTS: /api/forms/* accept and validate but do not
     deliver anywhere yet — swap data-endpoint for a real service when ready.
  ──────────────────────────────────────── */
  function initForms() {
    document.querySelectorAll('form[data-endpoint]').forEach(function (form) {
      form.addEventListener('submit', async function (e) {
        e.preventDefault();
        var ok = true;
        var payload = {};
        form.querySelectorAll('.field').forEach(function (field) {
          var input = field.querySelector('input, textarea, select');
          if (!input) return;
          field.classList.remove('invalid');
          var v = input.value.trim();
          payload[input.name || input.id] = v;
          if (input.required && !v) { field.classList.add('invalid'); ok = false; }
          else if (input.type === 'email' && v && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v)) {
            field.classList.add('invalid'); ok = false;
          }
        });
        var msg = form.querySelector('.form-msg');
        if (!ok) {
          if (msg) { msg.className = 'form-msg err'; msg.textContent = 'Please fix the highlighted fields.'; }
          return;
        }
        var btn = form.querySelector('[type="submit"]');
        if (btn) { btn.disabled = true; }
        try {
          var r = await fetch(form.dataset.endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ form: form.dataset.formName || form.id || 'form', fields: payload })
          });
          if (!r.ok) throw new Error('Request failed');
          if (msg) { msg.className = 'form-msg ok'; msg.textContent = form.dataset.successMsg || 'Thanks — we got it. We’ll get back to you.'; }
          form.reset();
        } catch (err) {
          if (msg) { msg.className = 'form-msg err'; msg.textContent = 'Something went wrong. Please email us instead.'; }
        } finally {
          if (btn) { btn.disabled = false; }
        }
      });
    });
  }

  /* ────────────────────────────────────────
     FAQ live filter — <input data-faq-filter> filters .acc-item text
  ──────────────────────────────────────── */
  function initFaqFilter() {
    var input = document.querySelector('[data-faq-filter]');
    if (!input) return;
    input.addEventListener('input', function () {
      var q = input.value.trim().toLowerCase();
      document.querySelectorAll('.acc-item').forEach(function (item) {
        item.style.display = !q || item.textContent.toLowerCase().indexOf(q) !== -1 ? '' : 'none';
      });
      document.querySelectorAll('[data-faq-section]').forEach(function (sec) {
        var any = Array.prototype.some.call(sec.querySelectorAll('.acc-item'), function (i) { return i.style.display !== 'none'; });
        sec.style.display = any ? '' : 'none';
      });
    });
  }

  function init() {
    initMobileNav();
    initCookieBanner();
    initReveal();
    initAccordions();
    initForms();
    initFaqFilter();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
