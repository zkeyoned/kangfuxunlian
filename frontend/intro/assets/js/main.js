/* 康师复介绍站 — 页面交互 */
(function () {
  'use strict';

  var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  var header = document.getElementById('siteHeader');

  /* ---------- 吸顶导航 ---------- */
  function syncHeader() {
    if (!header) return;
    header.classList.toggle('is-scrolled', window.scrollY > 40);
  }

  var ticking = false;
  window.addEventListener('scroll', function () {
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(function () { syncHeader(); ticking = false; });
  }, { passive: true });
  window.addEventListener('resize', syncHeader);
  syncHeader();

  /* ---------- 首屏轮播 ---------- */
  var slides = Array.prototype.slice.call(document.querySelectorAll('.hero__slide'));
  var dots = Array.prototype.slice.call(document.querySelectorAll('.hero__dot'));
  var heroIndex = 0;
  var heroTimer = null;

  function goSlide(i) {
    if (!slides.length) return;
    heroIndex = (i + slides.length) % slides.length;
    slides.forEach(function (s, idx) { s.classList.toggle('is-active', idx === heroIndex); });
    dots.forEach(function (d, idx) {
      d.classList.toggle('is-active', idx === heroIndex);
      d.setAttribute('aria-selected', String(idx === heroIndex));
    });
  }

  function startHero() {
    stopHero();
    if (reduceMotion.matches) return;
    heroTimer = setInterval(function () { goSlide(heroIndex + 1); }, 5000);
  }
  function stopHero() {
    if (heroTimer) { clearInterval(heroTimer); heroTimer = null; }
  }

  dots.forEach(function (dot, idx) {
    dot.addEventListener('click', function () { goSlide(idx); startHero(); });
  });

  var hero = document.querySelector('.hero');
  if (hero && slides.length) {
    hero.addEventListener('mouseenter', stopHero);
    hero.addEventListener('mouseleave', startHero);
    startHero();
  }

  /* ---------- 左文右画面：sticky 切换 ---------- */
  var panelEls = Array.prototype.slice.call(document.querySelectorAll('.panel[data-panel-index]'));
  var mediaEls = Array.prototype.slice.call(document.querySelectorAll('.media-layer[data-media-index]'));

  function setActivePanel(index) {
    panelEls.forEach(function (p) {
      p.classList.toggle('is-active', Number(p.getAttribute('data-panel-index')) === index);
    });
    mediaEls.forEach(function (m) {
      m.classList.toggle('is-active', Number(m.getAttribute('data-media-index')) === index);
    });
  }

  function syncPanels() {
    if (!panelEls.length) return;
    var mid = window.innerHeight * 0.5;
    var best = 0;
    var bestDist = Infinity;
    panelEls.forEach(function (p, idx) {
      var r = p.getBoundingClientRect();
      var c = r.top + r.height / 2;
      var d = Math.abs(c - mid);
      if (d < bestDist) { bestDist = d; best = idx; }
    });
    setActivePanel(best);
  }

  var panelTicking = false;
  window.addEventListener('scroll', function () {
    if (panelTicking) return;
    panelTicking = true;
    requestAnimationFrame(function () { syncPanels(); panelTicking = false; });
  }, { passive: true });
  window.addEventListener('resize', syncPanels);
  syncPanels();

  /* ---------- 数字滚动 ---------- */
  var counters = Array.prototype.slice.call(document.querySelectorAll('[data-count]'));
  var counted = new WeakSet();

  function formatValue(el, value) {
    var prefix = el.getAttribute('data-prefix') || '';
    var suffix = el.getAttribute('data-suffix') || '';
    var out = String(Math.round(value));
    if (el.getAttribute('data-format') === 'comma') {
      out = out.replace(/\B(?=(\d{3})+(?!\d))/g, ',');
    }
    return prefix + out + suffix;
  }

  function runCounter(el) {
    var target = Number(el.getAttribute('data-count')) || 0;
    if (reduceMotion.matches) {
      el.textContent = formatValue(el, target);
      return;
    }
    var duration = 1400;
    var start = null;
    function frame(ts) {
      if (start === null) start = ts;
      var t = Math.min((ts - start) / duration, 1);
      var eased = 1 - Math.pow(1 - t, 3);
      el.textContent = formatValue(el, target * eased);
      if (t < 1) requestAnimationFrame(frame);
      else el.textContent = formatValue(el, target);
    }
    requestAnimationFrame(frame);
  }

  if ('IntersectionObserver' in window && counters.length) {
    var counterObserver = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting || counted.has(entry.target)) return;
        counted.add(entry.target);
        runCounter(entry.target);
        counterObserver.unobserve(entry.target);
      });
    }, { threshold: 0.4 });
    counters.forEach(function (el) { counterObserver.observe(el); });
  } else {
    counters.forEach(function (el) { el.textContent = formatValue(el, Number(el.getAttribute('data-count')) || 0); });
  }

  /* ---------- 滚动淡入 ---------- */
  var revealTargets = Array.prototype.slice.call(document.querySelectorAll('[data-reveal]'));
  revealTargets.forEach(function (el) { el.classList.add('reveal'); });

  if (reduceMotion.matches) {
    revealTargets.forEach(function (el) { el.classList.add('is-in'); });
  } else if ('IntersectionObserver' in window) {
    var revealObserver = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        entry.target.classList.add('is-in');
        revealObserver.unobserve(entry.target);
      });
    }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });
    revealTargets.forEach(function (el) {
      var r = el.getBoundingClientRect();
      if (r.top < window.innerHeight * 0.9) {
        el.classList.add('is-in');
      } else {
        revealObserver.observe(el);
      }
    });
  } else {
    revealTargets.forEach(function (el) { el.classList.add('is-in'); });
  }

  /* ---------- 演示按钮：仅提示，不放假视频 ---------- */
  var toast = document.getElementById('toast');
  var toastTimer = null;

  function showToast(message) {
    if (!toast) return;
    toast.textContent = message;
    toast.classList.add('is-visible');
    if (toastTimer) clearTimeout(toastTimer);
    toastTimer = setTimeout(function () {
      toast.classList.remove('is-visible');
    }, 2400);
  }

  document.querySelectorAll('[data-demo-toast]').forEach(function (btn) {
    btn.addEventListener('click', function () { showToast('演示视频即将上线'); });
  });

  /* ---------- 平滑锚点 ---------- */
  document.querySelectorAll('a[href^="#"]').forEach(function (a) {
    a.addEventListener('click', function (e) {
      var href = a.getAttribute('href');
      if (href === '#' || href.length < 2) return;
      var target = document.querySelector(href);
      if (!target) return;
      e.preventDefault();
      target.scrollIntoView({ behavior: reduceMotion.matches ? 'auto' : 'smooth', block: 'start' });
    });
  });
})();
