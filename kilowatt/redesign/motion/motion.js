/* ============================================================
   «В ОКОПЕ» × НПО «КИЛОВАТТ» — MOTION KIT / motion.js
   Система переходов для светлого каталога (вариант 2).

   Подключение (после catalog.css / theme-quiet.css и app.js):
     <link rel="stylesheet" href="../redesign/motion/motion.css">
     <script src="../redesign/motion/motion.js"></script>

   Что делает:
   • появление секций/сеток при скролле (IntersectionObserver, один раз);
   • stagger для сеток и появления геро-блока;
   • hover/focus карточек — делает их доступными с клавиатуры;
   • sticky-тулбар каталога и плавный счётчик результатов;
   • плавный скролл по якорям с учётом фиксированной шапки;
   • ScrollSpy в верхнем меню;
   • модалка товара: вход/выход, aria, focus trap, возврат фокуса;
   • корзина-заявка: слайд-панель, анимация добавления позиции;
   • мобильное меню — burger/drawer с aria-expanded;
   • «Вариант 1/2» — мягкий переход между страницами;
   • prefers-reduced-motion и html.motion-off — полное отключение.

   Без JS страница остаётся полностью рабочей и видимой:
   все «скрытые» состояния живут только под html.motion-js.
   ============================================================ */
(function () {
  "use strict";

  var doc = document;
  var root = doc.documentElement;
  var body = doc.body;
  var $ = function (sel, r) { return (r || doc).querySelector(sel); };
  var $$ = function (sel, r) { return Array.prototype.slice.call((r || doc).querySelectorAll(sel)); };
  var mqReduce = window.matchMedia ? window.matchMedia("(prefers-reduced-motion: reduce)") : null;
  var hasIO = "IntersectionObserver" in window;
  var STAGGER_CAP = 8;

  /* ---------- утилиты ---------- */
  function reduced() {
    return (mqReduce && mqReduce.matches) || root.classList.contains("motion-off");
  }
  function isEl(n) { return !!n && n.nodeType === 1; }
  function setVar(el, name, val) { if (el && el.style) el.style.setProperty(name, val); }
  function isPlainClick(e) {
    return e.button === 0 && !e.metaKey && !e.ctrlKey && !e.shiftKey && !e.altKey;
  }

  /* ============================================================
     ВЫСОТА ШАПКИ И ПОЛОСА ПРОКРУТКИ
     Реальная высота вместо магической 61px: якоря и sticky-тулбар
     не уезжают под шапку при смене шрифта/темы.
     ============================================================ */
  var topbar = $(".topbar");
  var headerH = 61;
  var sbw = 0;

  function measure() {
    if (topbar) {
      var h = Math.round(topbar.getBoundingClientRect().height);
      if (h > 0) headerH = h;
    }
    root.style.setProperty("--m-topbar", headerH + "px");
    if (!body.classList.contains("m-locked")) {
      sbw = Math.max(0, window.innerWidth - doc.documentElement.clientWidth);
    }
    root.style.setProperty("--m-sbw", sbw + "px");
  }

  /* ============================================================
     БЛОКИРОВКА ПРОКРУТКИ (модалка / корзина / drawer)
     app.js лочит body классом is-locked для модалки; здесь общий
     менеджер, который компенсирует ширину скроллбара — без прыжка.
     ============================================================ */
  var lockEls = {};
  var isLocked = false;

  function refreshLock() {
    var should = false;
    for (var k in lockEls) {
      if (lockEls[k] && lockEls[k].classList && lockEls[k].classList.contains("is-open")) {
        should = true;
        break;
      }
    }
    if (should === isLocked) return;
    /* sbw замеряется заранее (measure), пока скроллбар ещё на месте:
       app.js вешает overflow:hidden до нашего observer'а, поэтому
       пересчитывать в этот момент уже поздно */
    if (should) root.style.setProperty("--m-sbw", sbw + "px");
    isLocked = should;
    body.classList.toggle("m-locked", should);
  }

  /* ============================================================
     1. ПОЯВЛЕНИЕ СЕКЦИЙ И СЕТОК
     ============================================================ */
  var revealTargets = [];
  var revealIO = null;

  var GROUPS = [
    { parent: ".hero__text", child: ":scope > *", step: 70 },
    { parent: ".hero__plate", step: 0 },
    { parent: ".sec__head", child: ":scope > *", step: 55 },
    { parent: ".flags", child: ":scope > .flag", step: 70 },
    { parent: ".grid", child: ":scope > .card", step: 45 },
    { parent: ".about", step: 0 },
    { parent: ".cmp__scroll", step: 0 },
    { parent: ".apps", child: ":scope > .app", step: 40 },
    { parent: ".steps", child: ":scope > .step", step: 45 },
    { parent: ".docs", child: ":scope > .doc", step: 60 },
    { parent: ".legal", step: 0 },
    { parent: ".order", child: ":scope > *", step: 60 },
    { parent: ".footer__in", child: ":scope > *", step: 60 }
  ];

  function showNow(el) {
    el.classList.add("is-in");
    if (revealIO) revealIO.unobserve(el);
  }

  function createRevealIO() {
    if (!hasIO) return null;
    return new IntersectionObserver(function (entries) {
      for (var i = 0; i < entries.length; i++) {
        if (entries[i].isIntersecting) showNow(entries[i].target);
      }
    }, { root: null, rootMargin: "0px 0px -6% 0px", threshold: 0.08 });
  }

  function markReveal(el, delay) {
    if (!isEl(el) || el.classList.contains("m-reveal")) return;
    if (el.closest && el.closest('[data-motion="off"]')) return;
    el.classList.add("m-reveal");
    if (delay) setVar(el, "--m-delay", delay + "ms");
    revealTargets.push(el);
    if (revealIO && !reduced()) revealIO.observe(el);
    else showNow(el);
  }

  function bindReveal() {
    for (var g = 0; g < GROUPS.length; g++) {
      var group = GROUPS[g];
      var parents = $$(group.parent);
      for (var p = 0; p < parents.length; p++) {
        var parent = parents[p];
        var els = group.child ? $$(group.child, parent) : [parent];
        for (var i = 0; i < els.length; i++) {
          if (!isEl(els[i]) || els[i].classList.contains("is-in")) continue;
          var idx = els.length > 9 ? i % STAGGER_CAP : i;
          markReveal(els[i], idx * (group.step || 0));
        }
      }
    }
    $$("[data-motion-reveal]").forEach(function (el) { markReveal(el, 0); });
    $$("[data-motion-stagger]").forEach(function (parent) {
      $$(":scope > *", parent).forEach(function (el, i) {
        markReveal(el, Math.min(i, STAGGER_CAP - 1) * 55);
      });
    });
  }

  function replayReveal() {
    if (!revealTargets.length) return;
    revealTargets.forEach(function (el) { el.classList.remove("is-in"); });
    void root.offsetHeight; /* фиксируем скрытое состояние до повторного показа */
    if (reduced() || !revealIO) {
      revealTargets.forEach(showNow);
      return;
    }
    revealTargets.forEach(function (el) { revealIO.observe(el); });
  }

  /* сетка каталога перерисовывается app.js — даём короткий вход
     без повторного «секционного» reveal */
  function initGridFx() {
    var grid = $("[data-grid]");
    if (!grid || !window.MutationObserver) return;
    new MutationObserver(function () {
      if (reduced()) return;
      var cards = $$(":scope > .card", grid);
      cards.forEach(function (card, i) {
        card.classList.remove("m-grid-in");
        setVar(card, "--m-i", String(i % STAGGER_CAP));
      });
      void grid.offsetHeight;
      cards.forEach(function (card) {
        card.classList.add("m-grid-in");
        card.addEventListener("animationend", function onEnd() {
          card.removeEventListener("animationend", onEnd);
          card.classList.remove("m-grid-in");
        });
      });
    }).observe(grid, { childList: true });
  }

  /* ============================================================
     2. СЧЁТЧИК РЕЗУЛЬТАТОВ + БЕЙДЖ ЗАЯВКИ
     ============================================================ */
  function parseNum(text) {
    var m = /(\d+)/.exec(text || "");
    return m ? parseInt(m[1], 10) : null;
  }

  function initCounter() {
    var el = $("[data-count]");
    if (!el || !window.MutationObserver) return;
    var busy = false;
    var current = parseNum(el.textContent) || 0;
    var lastWritten = null;
    var pending = null;

    function write(text) {
      lastWritten = text;
      el.textContent = text;
    }

    function tweenTo(text) {
      var m = /(\d+)/.exec(text);
      if (!m) return;
      var target = parseInt(m[1], 10);
      var prefix = text.slice(0, m.index);
      var suffix = text.slice(m.index + m[1].length);
      if (reduced() || target === current) { current = target; return; }

      var from = current;
      current = target;
      busy = true;
      var start = 0;
      var dur = 260;
      el.classList.remove("is-tick");
      void el.offsetWidth;
      el.classList.add("is-tick");

      function frame(now) {
        if (!start) start = now;
        var t = Math.min(1, (now - start) / dur);
        var e = 1 - Math.pow(1 - t, 3);
        write(prefix + Math.round(from + (target - from) * e) + suffix);
        if (t < 1) {
          requestAnimationFrame(frame);
        } else {
          write(prefix + target + suffix);
          busy = false;
          setTimeout(function () { el.classList.remove("is-tick"); }, 220);
          if (pending !== null) {
            var p = pending;
            pending = null;
            tweenTo(p);
          }
        }
      }
      requestAnimationFrame(frame);
    }

    new MutationObserver(function () {
      var text = el.textContent;
      if (text === lastWritten) return; /* это наша запись */
      if (busy) { pending = text; return; }
      tweenTo(text);
    }).observe(el, { childList: true, characterData: true, subtree: true });
  }

  function initBadge() {
    var badge = $("[data-cart-badge]");
    if (!badge || !window.MutationObserver) return;
    var timer = null;
    new MutationObserver(function () {
      if (reduced()) return;
      badge.classList.remove("is-bump");
      void badge.offsetWidth;
      badge.classList.add("is-bump");
      clearTimeout(timer);
      timer = setTimeout(function () { badge.classList.remove("is-bump"); }, 340);
    }).observe(badge, { childList: true, characterData: true, subtree: true });
  }

  /* ============================================================
     3. STICKY-ТУЛБАР КАТАЛОГА
     ============================================================ */
  function initStickyToolbar() {
    var toolbar = $(".cat-toolbar");
    if (!toolbar) return;
    var stuck = false;
    var ticking = false;

    function update() {
      ticking = false;
      var rect = toolbar.getBoundingClientRect();
      var nowStuck = rect.top <= headerH + 1 && rect.bottom > headerH + 2;
      if (nowStuck !== stuck) {
        stuck = nowStuck;
        toolbar.classList.toggle("is-stuck", stuck);
      }
      body.classList.toggle("is-scrolled", window.pageYOffset > 40);
    }
    function onScroll() {
      if (ticking) return;
      ticking = true;
      requestAnimationFrame(update);
    }
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll);
    update();
  }

  /* ============================================================
     4. КЛАВИАТУРА: КАРТОЧКИ КАК КНОПКИ
     ============================================================ */
  function enhanceOpenables(scope) {
    $$("[data-open]", scope || doc).forEach(function (el) {
      if (!isEl(el) || el.tagName === "A" || el.tagName === "BUTTON") return;
      if (!el.hasAttribute("tabindex")) el.setAttribute("tabindex", "0");
      if (!el.hasAttribute("role")) el.setAttribute("role", "button");
      if (!el.hasAttribute("aria-label")) {
        var nameEl = el.querySelector(".card__name, .flag__name");
        if (nameEl) el.setAttribute("aria-label", nameEl.textContent.trim() + " — подробнее");
      }
    });
  }

  function initOpenKeys() {
    enhanceOpenables(doc);
    doc.addEventListener("keydown", function (e) {
      if (e.key !== "Enter" && e.key !== " " && e.key !== "Spacebar") return;
      if (e.target.closest && e.target.closest("button, a, input, select, textarea")) return;
      var el = e.target.closest ? e.target.closest("[data-open][tabindex]") : null;
      if (!el) return;
      e.preventDefault();
      el.click();
    }, true);
  }

  /* ============================================================
     5. ПЛАВНЫЙ СКРОЛЛ ПО ЯКОРЯМ
     ============================================================ */
  function scrollToEl(el) {
    var top = el.getBoundingClientRect().top + window.pageYOffset - headerH - 12;
    if (el.id === "top" || el === $("main")) top = 0;
    top = Math.max(0, Math.round(top));
    window.scrollTo({ top: top, behavior: reduced() ? "auto" : "smooth" });
    if (!el.hasAttribute("tabindex")) el.setAttribute("tabindex", "-1");
    try { el.focus({ preventScroll: true }); } catch (err) { /* старые браузеры */ }
  }

  function initAnchors() {
    doc.addEventListener("click", function (e) {
      if (!isPlainClick(e)) return;
      var a = e.target.closest ? e.target.closest('a[href^="#"]') : null;
      if (!a) return;
      var href = a.getAttribute("href");
      if (!href || href.length < 2) return;
      var el = doc.getElementById(href.slice(1));
      if (!el) return;
      e.preventDefault();
      e.stopPropagation();
      scrollToEl(el);
      /* клик по ссылке внутри drawer закрывает меню (иначе capture+stop
         не даёт событию дойти до обработчика панели) */
      if (drawerOpen && drawerEl && a.closest(".m-drawer")) closeDrawer();
      try { window.history.replaceState(null, "", href); } catch (err) { /* file:// и т.п. */ }
    }, true);
    /* глубокая ссылка при загрузке: поправляем на реальную шапку */
    if (window.location.hash && window.location.hash.length > 1) {
      var target = doc.getElementById(window.location.hash.slice(1));
      if (target) setTimeout(function () {
        var y = target.getBoundingClientRect().top + window.pageYOffset - headerH - 12;
        if (Math.abs(y - window.pageYOffset) > 4) window.scrollTo(0, Math.max(0, y));
      }, 420);
    }
  }

  /* ============================================================
     6. SCROLLSPY
     ============================================================ */
  var spyLinks = [];
  function initSpy() {
    var sections = $$("main section[id]");
    if (!sections.length) return;
    spyLinks = $$(".topnav a[href^='#'], .m-drawer__nav a[href^='#']");
    if (!spyLinks.length) return;

    var byId = {};
    spyLinks.forEach(function (a) {
      var id = a.getAttribute("href").slice(1);
      (byId[id] = byId[id] || []).push(a);
    });

    var ticking = false;
    function update() {
      ticking = false;
      var line = headerH + Math.max(80, Math.round(window.innerHeight * 0.22));
      var lastMapped = null;
      for (var i = 0; i < sections.length; i++) {
        if (sections[i].getBoundingClientRect().top <= line) {
          if (byId[sections[i].id]) lastMapped = sections[i].id;
        }
      }
      if (window.innerHeight + window.pageYOffset >= doc.documentElement.scrollHeight - 4) {
        var last = sections[sections.length - 1];
        if (byId[last.id]) lastMapped = last.id;
      }
      spyLinks.forEach(function (a) {
        var on = lastMapped !== null && a.getAttribute("href") === "#" + lastMapped;
        a.classList.toggle("is-active", on);
        if (on) a.setAttribute("aria-current", "true");
        else a.removeAttribute("aria-current");
      });
    }
    function onScroll() {
      if (ticking) return;
      ticking = true;
      requestAnimationFrame(update);
    }
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll);
    update();
  }

  /* ============================================================
     7. ФОКУС-ТРАП ДЛЯ СЛОЁВ
     ============================================================ */
  var FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]), ' +
    'textarea:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';

  function trapTab(e, container) {
    var items = $$(FOCUSABLE, container).filter(function (el) {
      return el.getClientRects().length > 0;
    });
    if (!items.length) { e.preventDefault(); return; }
    var first = items[0];
    var last = items[items.length - 1];
    var active = doc.activeElement;
    if (e.shiftKey) {
      if (active === first || !container.contains(active)) { e.preventDefault(); last.focus(); }
    } else {
      if (active === last || !container.contains(active)) { e.preventDefault(); first.focus(); }
    }
  }

  /* ============================================================
     8. МОДАЛКА ТОВАРА
     ============================================================ */
  var modalEl = null;
  var modalBox = null;
  var lastModalTrigger = null;

  function initModal() {
    modalEl = $("[data-modal]");
    if (!modalEl) return;
    modalBox = $(".modal__box", modalEl);
    if (!modalBox) return;
    if (!modalBox.hasAttribute("tabindex")) modalBox.setAttribute("tabindex", "-1");
    modalEl.setAttribute("aria-hidden", modalEl.classList.contains("is-open") ? "false" : "true");

    function openFx() {
      lastModalTrigger = lastModalTrigger || ((doc.activeElement && doc.activeElement !== body &&
        doc.activeElement !== root) ? doc.activeElement : null);
      modalEl.setAttribute("aria-hidden", "false");
      var title = $(".modal__name", modalEl);
      if (title) {
        if (!title.id) title.id = "m-modal-title";
        modalBox.setAttribute("aria-labelledby", title.id);
      }
      if (modalBox) modalBox.scrollTop = 0;
      try { modalBox.focus({ preventScroll: true }); } catch (err) { modalBox.focus(); }
    }
    function closeFx() {
      var target = lastModalTrigger;
      lastModalTrigger = null;
      if (target && doc.contains(target) && typeof target.focus === "function") {
        try { target.focus({ preventScroll: true }); } catch (err) { target.focus(); }
      } else if (modalEl.contains(doc.activeElement)) {
        var b = $("[data-cart-toggle]");
        if (b) b.focus();
      }
      modalEl.setAttribute("aria-hidden", "true");
    }
    new MutationObserver(function () {
      if (modalEl.classList.contains("is-open")) openFx();
      else closeFx();
    }).observe(modalEl, { attributes: true, attributeFilter: ["class"] });
  }

  /* ============================================================
     9. КОРЗИНА-ЗАЯВКА
     ============================================================ */
  var cartEl = null;
  var lastCartTrigger = null;

  function listIds(list) {
    if (!list) return [];
    return $$("[data-del]", list).map(function (b) { return b.getAttribute("data-del"); });
  }

  function initCart() {
    cartEl = $("[data-cart]");
    if (!cartEl) return;
    var list = $("[data-cart-list]", cartEl);
    var closeBtn = $("[data-cart-close]", cartEl);
    var head = $(".cart__head h3", cartEl);
    if (!cartEl.hasAttribute("role")) {
      cartEl.setAttribute("role", "dialog");
      cartEl.setAttribute("aria-modal", "true");
    }
    if (head) {
      if (!head.id) head.id = "m-cart-title";
      cartEl.setAttribute("aria-labelledby", head.id);
    }

    var pendingNew = [];
    var lastIds = listIds(list);

    function markNewItems() {
      if (!pendingNew.length || !list) return;
      var ids = pendingNew;
      pendingNew = [];
      $$(".cart__item", list).forEach(function (li) {
        var del = li.querySelector("[data-del]");
        if (del && ids.indexOf(del.getAttribute("data-del")) >= 0) {
          li.classList.add("m-cart-new");
          setTimeout(function () { li.classList.remove("m-cart-new"); }, 950);
        }
      });
    }

    function staggerItems() {
      if (!list || reduced()) return;
      var items = $$(".cart__item", list);
      items.forEach(function (li, i) { setVar(li, "--m-i", String(Math.min(i, 6))); });
      items.forEach(function (li) { li.classList.remove("m-cart-item-in"); });
      void list.offsetHeight;
      items.forEach(function (li) { li.classList.add("m-cart-item-in"); });
      setTimeout(function () {
        items.forEach(function (li) { li.classList.remove("m-cart-item-in"); });
      }, 700);
    }

    if (list && window.MutationObserver) {
      new MutationObserver(function () {
        var now = listIds(list);
        var added = now.filter(function (id) { return lastIds.indexOf(id) < 0; });
        lastIds = now;
        if (added.length) {
          pendingNew = pendingNew.concat(added);
          if (cartEl.classList.contains("is-open")) markNewItems();
        }
      }).observe(list, { childList: true });
    }

    function openFx() {
      lastCartTrigger = lastCartTrigger || doc.activeElement;
      staggerItems();
      markNewItems();
      if (closeBtn) closeBtn.focus({ preventScroll: true });
    }
    function closeFx() {
      var target = lastCartTrigger;
      lastCartTrigger = null;
      if (target && doc.contains(target) && typeof target.focus === "function") {
        try { target.focus({ preventScroll: true }); } catch (err) { target.focus(); }
      } else if (cartEl.contains(doc.activeElement)) {
        var b = $("[data-cart-toggle]");
        if (b) b.focus();
      }
    }
    new MutationObserver(function () {
      if (cartEl.classList.contains("is-open")) openFx();
      else closeFx();
    }).observe(cartEl, { attributes: true, attributeFilter: ["class"] });
  }

  /* ============================================================
     10. МОБИЛЬНОЕ МЕНЮ: BURGER + DRAWER
     ============================================================ */
  var drawerEl = null;
  var burgerEl = null;
  var drawerOpen = false;
  var lastDrawerFocus = null;

  function buildDrawer() {
    var topbarIn = $(".topbar__in");
    var nav = $(".topnav");
    if (!topbarIn || !nav) return;

    burgerEl = doc.createElement("button");
    burgerEl.type = "button";
    burgerEl.className = "m-burger";
    burgerEl.setAttribute("aria-label", "Меню");
    burgerEl.setAttribute("aria-expanded", "false");
    burgerEl.setAttribute("aria-controls", "m-drawer");
    burgerEl.innerHTML = "<span></span><span></span><span></span>";
    topbarIn.appendChild(burgerEl);

    drawerEl = doc.createElement("div");
    drawerEl.className = "m-drawer";
    drawerEl.id = "m-drawer";
    drawerEl.setAttribute("aria-hidden", "true");

    var links = $$("a", nav);
    var linksHtml = links.map(function (a, i) {
      var num = ("0" + (i + 1)).slice(-2);
      return '<a href="' + a.getAttribute("href") + '"><span>' + a.textContent.trim() +
        "</span><b>" + num + "</b></a>";
    }).join("");

    var vs = $("[data-variant-switch]");
    var foot = "";
    if (vs) {
      foot = '<a class="cart-btn" data-variant-switch href="' +
        (vs.getAttribute("href") || "#") + '">' + vs.textContent.trim() + "</a>";
    }

    drawerEl.innerHTML =
      '<div class="m-drawer__veil" data-m-drawer-close></div>' +
      '<nav class="m-drawer__panel" aria-label="Разделы">' +
      '<div class="m-drawer__head"><span>Меню / разделы</span>' +
      '<button type="button" class="m-drawer__close" aria-label="Закрыть меню" data-m-drawer-close>×</button></div>' +
      '<div class="m-drawer__nav">' + linksHtml + "</div>" +
      '<div class="m-drawer__foot">' + foot + "</div>" +
      "</nav>";
    /* drawer — fixed-слой вне шапки, чтобы не влиять на её layout */
    body.appendChild(drawerEl);

    $$(".m-drawer__nav a", drawerEl).forEach(function (a, i) { setVar(a, "--m-i", String(Math.min(i, 6))); });

    burgerEl.addEventListener("click", function () {
      if (drawerOpen) closeDrawer();
      else openDrawer();
    });
    drawerEl.addEventListener("click", function (e) {
      if (e.target.closest("[data-m-drawer-close]")) { closeDrawer(); return; }
      var link = e.target.closest("a[href^='#']");
      if (link) closeDrawer();
    });
    if (window.matchMedia) {
      var mq = window.matchMedia("(min-width: 821px)");
      var onChange = function () { if (mq.matches && drawerOpen) closeDrawer(); };
      if (mq.addEventListener) mq.addEventListener("change", onChange);
      else if (mq.addListener) mq.addListener(onChange);
    }
  }

  function openDrawer() {
    if (!drawerEl || drawerOpen) return;
    lastDrawerFocus = (doc.activeElement && doc.activeElement !== body &&
      doc.activeElement !== root) ? doc.activeElement : burgerEl;
    drawerOpen = true;
    drawerEl.classList.add("is-open");
    drawerEl.setAttribute("aria-hidden", "false");
    if (burgerEl) burgerEl.setAttribute("aria-expanded", "true");
    lockEls.drawer = drawerEl;
    refreshLock();
    var close = $(".m-drawer__close", drawerEl);
    if (close) requestAnimationFrame(function () { close.focus({ preventScroll: true }); });
  }

  function closeDrawer() {
    if (!drawerEl || !drawerOpen) return;
    drawerOpen = false;
    drawerEl.classList.remove("is-open");
    drawerEl.setAttribute("aria-hidden", "true");
    if (burgerEl) burgerEl.setAttribute("aria-expanded", "false");
    lockEls.drawer = null;
    refreshLock();
    var target = lastDrawerFocus;
    lastDrawerFocus = null;
    if (target && doc.contains(target) && typeof target.focus === "function") {
      try { target.focus({ preventScroll: true }); } catch (err) { target.focus(); }
    } else if (burgerEl) {
      burgerEl.focus();
    }
  }

  /* ============================================================
     11. ПЕРЕКЛЮЧАТЕЛЬ «ВАРИАНТ 1/2»
     Кросс-документные View Transitions — в CSS; здесь запасной
     мягкий уход для браузеров без этой технологии.
     ============================================================ */
  function initVariantSwitch() {
    var crossDocVT = ("onpagereveal" in window) || ("onpageswap" in window);
    if (crossDocVT) return;
    doc.addEventListener("click", function (e) {
      if (!isPlainClick(e)) return;
      var a = e.target.closest ? e.target.closest("[data-variant-switch]") : null;
      if (!a) return;
      var href = a.getAttribute("href") || "";
      if (!href || href.charAt(0) === "#") return;
      e.preventDefault();
      /* бумажный занавес вместо резкой смены страницы */
      var veil = doc.createElement("div");
      veil.className = "m-page-veil";
      veil.setAttribute("aria-hidden", "true");
      body.appendChild(veil);
      void veil.offsetWidth;
      veil.classList.add("is-on");
      setTimeout(function () { window.location.href = href; }, reduced() ? 0 : 190);
    }, true);
  }

  /* ============================================================
     12. КЛАВИАТУРА: ESC / TAB ДЛЯ СЛОЁВ
     ============================================================ */
  function initLayerKeys() {
    doc.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && drawerOpen) {
        e.stopPropagation();
        closeDrawer();
        return;
      }
      if (e.key !== "Tab") return;
      var modalOpen = modalEl && modalEl.classList.contains("is-open");
      var cartOpen = cartEl && cartEl.classList.contains("is-open");
      if (modalOpen && modalBox) trapTab(e, modalBox);
      else if (cartOpen && cartEl) trapTab(e, cartEl);
      else if (drawerOpen && drawerEl) trapTab(e, $(".m-drawer__panel", drawerEl) || drawerEl);
    }, true);
  }

  /* ============================================================
     13. ЗАПИСЬ ТРИГГЕРОВ И СИНХРОНИЗАЦИЯ БЛОКИРОВКИ
     ============================================================ */
  function initTriggers() {
    doc.addEventListener("click", function (e) {
      if (!e.target.closest) return;
      var open = e.target.closest("[data-open]");
      if (open && modalEl && !modalEl.contains(open)) lastModalTrigger = open;
      if (e.target.closest("[data-cart-toggle]") || e.target.closest("[data-add]")) {
        lastCartTrigger = e.target.closest("[data-cart-toggle]") || e.target.closest("[data-add]");
      }
    }, true);
  }

  function observeLocks() {
    var obs = window.MutationObserver;
    if (!obs) return;
    if (modalEl) {
      lockEls.modal = modalEl;
      new obs(refreshLock).observe(modalEl, { attributes: true, attributeFilter: ["class"] });
    }
    if (cartEl) {
      lockEls.cart = cartEl;
      new obs(refreshLock).observe(cartEl, { attributes: true, attributeFilter: ["class"] });
    }
  }

  /* ============================================================
     14. СТАРТ
     ============================================================ */
  function init() {
    if (!body) body = doc.body;
    measure();
    revealIO = createRevealIO();
    bindReveal();
    enhanceOpenables(doc);
    initOpenKeys();
    initCounter();
    initBadge();
    initModal();
    initCart();
    buildDrawer();
    initSpy();
    initAnchors();
    initStickyToolbar();
    initGridFx();
    initVariantSwitch();
    initLayerKeys();
    initTriggers();
    observeLocks();
    if (mqReduce && mqReduce.addEventListener) {
      mqReduce.addEventListener("change", refreshLock);
    }
    var rTimer = null;
    window.addEventListener("resize", function () {
      clearTimeout(rTimer);
      rTimer = setTimeout(function () { measure(); refreshLock(); }, 150);
    });
    if (doc.fonts && doc.fonts.ready && doc.fonts.ready.then) {
      doc.fonts.ready.then(function () { measure(); });
    }
  }

  /* публичный API: для демо-страницы и отладки */
  window.MotionKit = {
    version: "1.0",
    refresh: function () { bindReveal(); enhanceOpenables(doc); },
    replayReveal: replayReveal,
    openDrawer: openDrawer,
    closeDrawer: closeDrawer,
    closeAll: function () {
      closeDrawer();
      if (modalEl && modalEl.classList.contains("is-open")) modalEl.classList.remove("is-open");
      if (cartEl && cartEl.classList.contains("is-open")) cartEl.classList.remove("is-open");
      var ov = $("[data-overlay]");
      if (ov) ov.classList.remove("is-on");
      body.classList.remove("is-locked");
    },
    reduced: reduced,
    scrollTo: function (sel) {
      var el = typeof sel === "string" ? $(sel) : sel;
      if (el) scrollToEl(el);
    }
  };

  /* html.motion-js включаем сразу: CSS ниже прячет только то,
     что JS успеет пометить .m-reveal — без JS контент виден */
  root.classList.add("motion-js");

  if (doc.readyState === "loading") {
    doc.addEventListener("DOMContentLoaded", function () { setTimeout(init, 0); });
  } else {
    setTimeout(init, 0);
  }
})();
