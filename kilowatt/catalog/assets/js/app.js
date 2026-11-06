/* Каталог «В ОКОПЕ» × НПО «Киловатт» — движок.
   Данные: window.CATALOG (генерируется build_data.py из kilowatt/data/products.json).
   Конфиг контактов: window.SITE_CONTACTS (заполняет владелец). */
(function () {
  "use strict";

  var DATA = window.CATALOG || { products: [], content: {}, generated: "" };
  var CONTACTS = window.SITE_CONTACTS || { tg: "", phone: "", email: "", note: "" };
  var state = { cat: "all", q: "", sort: "default", cart: [], active: null, gallery: 0 };
  var $ = function (sel, root) { return (root || document).querySelector(sel); };
  var $$ = function (sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); };

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function money(v) {
    if (v == null || v === "" || isNaN(+v)) return null;
    return (+v).toLocaleString("ru-RU");
  }
  function priceHtml(p) {
    if (p.price_dima == null) return '<span class="price price--request">Цена по запросу</span>';
    var v = money(p.price_dima);
    return '<span class="price"><span class="price__num">' + v + '</span> <span class="price__cur">₽</span></span>';
  }
  function mainPhoto(p) {
    return (p.photos && p.photos.length) ? p.photos[0] : "assets/img/no-photo.svg";
  }
  function chip(text, cls, attrs) {
    return '<span class="chip ' + (cls || "") + '" ' + (attrs || "") + ">" + esc(text) + "</span>";
  }

  /* ---------- ХЕДЕР: прогресс скролла ---------- */
  function initScroll() {
    var bar = $("[data-scrollbar]");
    if (!bar) return;
    var onScroll = function () {
      var h = document.documentElement;
      var max = h.scrollHeight - h.clientHeight;
      bar.style.transform = "scaleX(" + (max > 0 ? h.scrollTop / max : 0) + ")";
      document.body.classList.toggle("is-scrolled", h.scrollTop > 40);
    };
    document.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
  }

  /* ---------- ФЛАГМАНЫ ---------- */
  function renderFlagships() {
    var box = $("[data-flagships]");
    if (!box) return;
    var list = DATA.products.filter(function (p) { return p.flagship; }).slice(0, 3);
    box.innerHTML = list.map(function (p, i) {
      return '' +
        '<article class="flag" data-open="' + esc(p.id) + '" style="--i:' + i + '">' +
        '<div class="flag__media"><img src="' + esc(mainPhoto(p)) + '" alt="' + esc(p.name) + '" loading="lazy"></div>' +
        '<div class="flag__body">' +
        '<div class="flag__kicker">0' + (i + 1) + ' · ' + esc(p.category) + "</div>" +
        '<h3 class="flag__name">' + esc(p.name) + "</h3>" +
        '<p class="flag__short">' + esc(p.short || "") + "</p>" +
        '<ul class="flag__specs">' + (p.specs || []).slice(0, 3).map(function (s) {
          return "<li><span>" + esc(s.label) + "</span><b>" + esc(s.value) + "</b></li>";
        }).join("") + "</ul>" +
        '<div class="flag__foot">' + priceHtml(p) +
        '<button class="btn btn--ghost" data-open="' + esc(p.id) + '">Подробнее</button></div>' +
        "</div></article>";
    }).join("");
  }

  /* ---------- КАТЕГОРИИ ---------- */
  function categories() {
    var seen = [];
    DATA.products.forEach(function (p) {
      if (p.category && seen.indexOf(p.category) < 0) seen.push(p.category);
    });
    return seen;
  }
  function renderChips() {
    var box = $("[data-chips]");
    if (!box) return;
    var cats = categories();
    var counts = {};
    DATA.products.forEach(function (p) { counts[p.category] = (counts[p.category] || 0) + 1; });
    box.innerHTML = '<button class="chip chip--btn is-active" data-cat="all">Все <b>' + DATA.products.length + "</b></button>" +
      cats.map(function (c) {
        return '<button class="chip chip--btn" data-cat="' + esc(c) + '">' + esc(c) + " <b>" + (counts[c] || 0) + "</b></button>";
      }).join("");
  }

  /* ---------- СЕТКА КАТАЛОГА ---------- */
  function filtered() {
    var q = state.q.toLowerCase().trim();
    var list = DATA.products.filter(function (p) {
      if (state.cat !== "all" && p.category !== state.cat) return false;
      if (!q) return true;
      var blob = [p.name, p.category, p.short, p.description].concat((p.specs || []).map(function (s) { return s.label + " " + s.value; })).join(" ").toLowerCase();
      return blob.indexOf(q) >= 0;
    });
    if (state.sort === "price-asc") list.sort(function (a, b) { return (a.price_dima || 1e12) - (b.price_dima || 1e12); });
    if (state.sort === "price-desc") list.sort(function (a, b) { return (b.price_dima || -1) - (a.price_dima || -1); });
    if (state.sort === "name") list.sort(function (a, b) { return a.name.localeCompare(b.name, "ru"); });
    return list;
  }
  function renderGrid() {
    var box = $("[data-grid]");
    if (!box) return;
    var list = filtered();
    $("[data-count]").textContent = list.length + " " + plural(list.length, ["позиция", "позиции", "позиций"]);
    if (!list.length) {
      box.innerHTML = '<div class="empty">Ничего не нашлось. Попробуйте другой запрос или категорию.</div>';
      return;
    }
    box.innerHTML = list.map(function (p) {
      var specs = (p.specs || []).slice(0, 4).map(function (s) {
        return '<li><span>' + esc(s.label) + "</span><b>" + esc(s.value) + "</b></li>";
      }).join("");
      return '' +
        '<article class="card' + (p.on_site === false ? " card--archive" : "") + '" data-open="' + esc(p.id) + '">' +
        '<div class="card__media"><img src="' + esc(mainPhoto(p)) + '" alt="' + esc(p.name) + '" loading="lazy">' +
        (p.flagship ? '<span class="badge badge--flag">Флагман</span>' : "") +
        (p.on_site === false ? '<span class="badge badge--archive">Вне сайта</span>' : "") +
        (p.availability ? '<span class="badge badge--avail">' + esc(p.availability) + "</span>" : "") +
        "</div>" +
        '<div class="card__body">' +
        '<div class="card__cat">' + esc(p.category) + "</div>" +
        '<h3 class="card__name">' + esc(p.name) + "</h3>" +
        '<p class="card__short">' + esc(p.short || "") + "</p>" +
        '<ul class="card__specs">' + specs + "</ul>" +
        '<div class="card__foot">' + priceHtml(p) +
        '<button class="btn btn--mini" data-add="' + esc(p.id) + '">В заявку</button></div>' +
        "</div></article>";
    }).join("");
  }
  function plural(n, forms) {
    var a = Math.abs(n) % 100, b = a % 10;
    if (a > 10 && a < 20) return forms[2];
    if (b > 1 && b < 5) return forms[1];
    if (b === 1) return forms[0];
    return forms[2];
  }

  /* ---------- МОДАЛКА ТОВАРА ---------- */
  function openProduct(id) {
    var p = DATA.products.filter(function (x) { return x.id === id; })[0];
    if (!p) return;
    state.active = p; state.gallery = 0;
    var modal = $("[data-modal]");
    var photos = (p.photos && p.photos.length) ? p.photos : ["assets/img/no-photo.svg"];
    $("[data-modal-body]").innerHTML = '' +
      '<button class="modal__close" data-close aria-label="Закрыть">×</button>' +
      '<div class="modal__grid">' +
      '<div class="modal__media">' +
      '<div class="gallery"><img data-gallery-main src="' + esc(photos[0]) + '" alt="' + esc(p.name) + '"></div>' +
      '<div class="gallery__thumbs">' + photos.map(function (ph, i) {
        return '<button class="gallery__thumb' + (i === 0 ? " is-active" : "") + '" data-thumb="' + i + '"><img src="' + esc(ph) + '" alt="" loading="lazy"></button>';
      }).join("") + "</div></div>" +
      '<div class="modal__info">' +
      '<div class="modal__cat">' + esc(p.category) + (p.flagship ? ' · <span class="flag-mark">флагман</span>' : "") + "</div>" +
      "<h2 class=\"modal__name\">" + esc(p.name) + "</h2>" +
      (p.description ? '<p class="modal__desc">' + esc(p.description) + "</p>" : "") +
      '<table class="specs"><tbody>' + (p.specs || []).map(function (s) {
        return "<tr><th>" + esc(s.label) + "</th><td>" + esc(s.value) + "</td></tr>";
      }).join("") + "</tbody></table>" +
      (p.warnings && p.warnings.length ? '<p class="modal__warn">' + esc(p.warnings.join(" ")) + "</p>" : "") +
      '<div class="modal__buy">' + priceHtml(p) +
      '<button class="btn btn--solid" data-add="' + esc(p.id) + '">Добавить в заявку</button></div>' +
      (p.price_source ? '<p class="modal__src">Источник цены: ' + esc(p.price_source) + "</p>" : "") +
      "</div></div>";
    modal.classList.add("is-open");
    document.body.classList.add("is-locked");
  }
  function closeModal() {
    $("[data-modal]").classList.remove("is-open");
    document.body.classList.remove("is-locked");
  }

  /* ---------- ЗАЯВКА (корзина) ---------- */
  function addToCart(id) {
    if (state.cart.indexOf(id) < 0) state.cart.push(id);
    renderCart(); openCart();
  }
  function removeFromCart(id) {
    state.cart = state.cart.filter(function (x) { return x !== id; });
    renderCart();
  }
  function cartProducts() {
    return state.cart.map(function (id) {
      return DATA.products.filter(function (p) { return p.id === id; })[0];
    }).filter(Boolean);
  }
  function cartText(extra) {
    var lines = ["Заявка с каталога «В ОКОПЕ» (НПО «Киловатт»)"];
    if (cartProducts().length) {
      lines.push("", "Позиции:");
      cartProducts().forEach(function (p, i) {
        lines.push((i + 1) + ". " + p.name + (p.price_dima != null ? " — от " + money(p.price_dima) + " ₽" : " — цена по запросу"));
      });
    }
    if (extra) {
      lines.push("", extra);
    }
    lines.push("", "Прошу связаться для расчёта и сроков.");
    return lines.join("\n");
  }
  function renderCart() {
    var list = $("[data-cart-list]");
    if (!list) return;
    var items = cartProducts();
    $("[data-cart-count]").textContent = items.length;
    $("[data-cart-badge]").textContent = items.length;
    $("[data-cart-badge]").classList.toggle("is-empty", items.length === 0);
    list.innerHTML = items.length ? items.map(function (p) {
      return '<li class="cart__item"><img src="' + esc(mainPhoto(p)) + '" alt=""><div><b>' + esc(p.name) + "</b>" +
        (p.price_dima != null ? "<span>" + money(p.price_dima) + " ₽</span>" : "<span>по запросу</span>") +
        '</div><button class="cart__del" data-del="' + esc(p.id) + '" aria-label="Убрать">×</button></li>';
    }).join("") : '<li class="cart__empty">Пока пусто. Добавьте позиции из каталога — заявка соберётся сама.</li>';
  }
  function openCart() { $("[data-cart]").classList.add("is-open"); $("[data-overlay]").classList.add("is-on"); }
  function closeCart() { $("[data-cart]").classList.remove("is-open"); $("[data-overlay]").classList.remove("is-on"); }
  function copyText(text, btn) {
    var done = function () {
      if (!btn) return;
      var old = btn.textContent; btn.textContent = "Скопировано ✓";
      setTimeout(function () { btn.textContent = old; }, 1800);
    };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(done, function () { fallbackCopy(text, done); });
    } else fallbackCopy(text, done);
  }
  function fallbackCopy(text, cb) {
    var ta = document.createElement("textarea");
    ta.value = text; ta.style.position = "fixed"; ta.style.opacity = "0";
    document.body.appendChild(ta); ta.select();
    try { document.execCommand("copy"); } catch (e) {}
    document.body.removeChild(ta); cb();
  }
  function submitRequest() {
    var f = $("[data-request-form]");
    var extra = [];
    if (f) {
      var name = f.elements["name"] ? f.elements["name"].value.trim() : "";
      var org = f.elements["org"] ? f.elements["org"].value.trim() : "";
      var contact = f.elements["contact"] ? f.elements["contact"].value.trim() : "";
      var object = f.elements["object"] ? f.elements["object"].value.trim() : "";
      var comment = f.elements["comment"] ? f.elements["comment"].value.trim() : "";
      if (name) extra.push("Имя: " + name);
      if (org) extra.push("Организация: " + org);
      if (contact) extra.push("Контакт: " + contact);
      if (object) extra.push("Объект: " + object);
      if (comment) extra.push("Комментарий: " + comment);
    }
    var text = cartText(extra.join("\n"));
    var tg = CONTACTS.tg || "";
    if (tg) {
      var url = "https://t.me/" + tg.replace(/^@/, "") + "?text=" + encodeURIComponent(text);
      window.open(url, "_blank");
    } else {
      copyText(text, $("[data-copy-request]"));
      var note = $("[data-request-note]");
      if (note) note.textContent = "Текст заявки скопирован — вставьте его в Telegram или отправьте нам. (Контакт для кнопки задаётся в настройках сайта.)";
    }
  }

  /* ---------- СОБЫТИЯ ---------- */
  function bind() {
    document.addEventListener("click", function (e) {
      var t = e.target.closest("[data-open]");
      if (t) { e.preventDefault(); openProduct(t.getAttribute("data-open")); return; }
      if (e.target.closest("[data-close]")) { closeModal(); return; }
      var add = e.target.closest("[data-add]");
      if (add) { e.preventDefault(); e.stopPropagation(); addToCart(add.getAttribute("data-add")); return; }
      var del = e.target.closest("[data-del]");
      if (del) { removeFromCart(del.getAttribute("data-del")); return; }
      var thumb = e.target.closest("[data-thumb]");
      if (thumb) {
        var i = +thumb.getAttribute("data-thumb");
        state.gallery = i;
        var p = state.active;
        $("[data-gallery-main]").src = p.photos[i];
        $$(".gallery__thumb").forEach(function (b) { b.classList.toggle("is-active", +b.getAttribute("data-thumb") === i); });
        return;
      }
      var cat = e.target.closest("[data-cat]");
      if (cat) {
        state.cat = cat.getAttribute("data-cat");
        $$("[data-cat]").forEach(function (b) { b.classList.toggle("is-active", b === cat); });
        renderGrid(); return;
      }
      if (e.target.closest("[data-cart-toggle]")) { openCart(); return; }
      if (e.target.closest("[data-cart-close]") || e.target.closest("[data-overlay]")) { closeCart(); return; }
      if (e.target.closest("[data-copy-request]")) { copyText(cartText(""), e.target.closest("[data-copy-request]")); return; }
      if (e.target.closest("[data-submit-request]")) { submitRequest(); return; }
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") { closeModal(); closeCart(); }
    });
    var search = $("[data-search]");
    if (search) {
      var t = null;
      search.addEventListener("input", function () {
        clearTimeout(t);
        t = setTimeout(function () { state.q = search.value; renderGrid(); }, 160);
      });
    }
    var sort = $("[data-sort]");
    if (sort) sort.addEventListener("change", function () { state.sort = sort.value; renderGrid(); });
    // плавный скролл по якорям
    document.addEventListener("click", function (e) {
      var a = e.target.closest('a[href^="#"]');
      if (!a) return;
      var id = a.getAttribute("href");
      if (id.length < 2) return;
      var el = document.querySelector(id);
      if (!el) return;
      e.preventDefault();
      el.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  }

  /* ---------- СТАРТ ---------- */
  function init() {
    initScroll();
    renderFlagships();
    renderChips();
    renderGrid();
    renderCart();
    bind();
    var meta = $("[data-generated]");
    if (meta && DATA.generated) meta.textContent = DATA.generated;
    // переключение вариантов оформления
    var alt = document.body.getAttribute("data-alt");
    var sw = $("[data-variant-switch]");
    if (sw && alt) {
      sw.setAttribute("href", alt);
      sw.textContent = document.body.getAttribute("data-theme") === "field" ? "Вариант 2 →" : "← Вариант 1";
    }
    if (window.CATALOG_READY) window.CATALOG_READY(DATA);
    // глубокие ссылки на секции (и скриншоты): прокрутка после вёрстки
    if (location.hash && location.hash.length > 1) {
      var target = document.querySelector(location.hash);
      if (target) {
        var jump = function () {
          var y = target.getBoundingClientRect().top + (window.pageYOffset || document.documentElement.scrollTop) - 62;
          var prev = document.documentElement.style.scrollBehavior;
          document.documentElement.style.scrollBehavior = "auto";
          window.scrollTo(0, y);
          document.documentElement.style.scrollBehavior = prev;
        };
        setTimeout(jump, 250);
        window.addEventListener("load", function () { setTimeout(jump, 60); });
      }
    }
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
