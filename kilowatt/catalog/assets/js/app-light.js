/* «В ОКОПЕ» × НПО «Киловатт» — каталог, вариант 2 «Стенд» / «Ведомость».
   Форк catalog/assets/js/app.js: вся логика сохранена (данные window.CATALOG,
   фильтры/поиск/сортировка/архив, модалка с галереей, заявка, копирование,
   контакты из config.js), рендер переписан под редакционный дизайн:
   каталог — строки-индекс + липкое «поле образца», флагманы — щит из трёх
   плиток, сравнение — паспортная таблица на волосяных линиях. */
(function () {
  "use strict";

  var DATA = window.CATALOG || { products: [], content: {}, generated: "" };
  var CONTACTS = window.SITE_CONTACTS || { tg: "", phone: "", email: "", note: "" };
  var state = { cat: "all", q: "", sort: "default", cart: [], active: null, gallery: 0, archiveOnly: false };
  var $ = function (sel, root) { return (root || document).querySelector(sel); };
  var $$ = function (sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); };

  var TOTAL = DATA.products.length || 43;
  var byId = {};
  var posOf = {};
  DATA.products.forEach(function (p, i) {
    byId[p.id] = p;
    posOf[p.id] = i + 1;
  });

  var NO_PHOTO = "assets/img/no-photo.svg";
  var SORT_LABELS = { "price-asc": "цена по возрастанию", "price-desc": "цена по убыванию", name: "по названию" };

  /* ---------- утилиты ---------- */
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function money(v) {
    if (v == null || v === "" || isNaN(+v)) return null;
    return (+v).toLocaleString("ru-RU");
  }
  function pad2(n) {
    n = +n || 0;
    return ("0" + n).slice(-2);
  }
  function plural(n, forms) {
    var a = Math.abs(n) % 100, b = a % 10;
    if (a > 10 && a < 20) return forms[2];
    if (b > 1 && b < 5) return forms[1];
    if (b === 1) return forms[0];
    return forms[2];
  }
  function positions(n) {
    return n + "\u00A0" + plural(n, ["позиция", "позиции", "позиций"]);
  }
  function priceHtml(p) {
    if (p.price_dima == null) return '<span class="price price--request">Цена по запросу</span>';
    return '<span class="price"><span class="price__num">' + money(p.price_dima) +
      '</span>\u00A0<span class="price__cur">₽</span></span>';
  }
  function mainPhoto(p) {
    return (p.photos && p.photos.length) ? p.photos[0] : NO_PHOTO;
  }
  function hasPhoto(p) {
    return !!(p.photos && p.photos.length);
  }
  function specFind(p, pats) {
    var specs = p.specs || [];
    for (var i = 0; i < specs.length; i++) {
      var l = (specs[i].label || "").toLowerCase();
      for (var j = 0; j < pats.length; j++) {
        if (l.indexOf(pats[j]) >= 0) return specs[i];
      }
    }
    return null;
  }
  function keySpecs(p, n) {
    n = n || 3;
    var preferred = [
      ["диапазон"],
      ["мощность передатчиков", "выходная мощность", "суммарная мощность"],
      ["дальность подавления", "дальность"]
    ];
    var out = [];
    var used = [];
    preferred.forEach(function (pats) {
      var s = specFind(p, pats);
      if (s && out.indexOf(s) < 0 && used.indexOf(s.label) < 0) {
        out.push(s);
        used.push(s.label);
      }
    });
    (p.specs || []).forEach(function (s) {
      if (out.length >= n) return;
      if (used.indexOf(s.label) >= 0) return;
      out.push(s);
      used.push(s.label);
    });
    return out.slice(0, n);
  }
  function badgesHTML(p) {
    var out = "";
    if (p.flagship) out += '<span class="badge badge--flag">Флагман</span>';
    if (p.on_site === false) out += '<span class="badge badge--archive">Вне сайта</span>';
    if (p.availability) out += '<span class="badge badge--avail">' + esc(p.availability) + "</span>";
    return out;
  }
  /* неразрывные пробелы перед единицами: МГц, Вт, м, км, кг, мм, °C … */
  function typograph(s) {
    var v = String(s == null ? "" : s);
    v = v.replace(/(\d)\s+(МГц|ГГц|кГц|Вт|кВт|мВт|м|км|мм|см|кг|г|т|ч|мин|°C|мес|месяц(?:а|ев)?|В|А|шт)/g, "$1\u00A0$2");
    v = v.replace(/\s+(₽)/g, "\u00A0$1");
    return v;
  }
  /* компактная запись паспортной характеристики для строки ведомости */
  function shortSpecValue(label, value) {
    var v = String(value == null ? "" : value);
    var l = String(label == null ? "" : label).toLowerCase();
    if (l.indexOf("диапазон") >= 0) {
      var unitMatch = /(ГГц|МГц)\s*$/.exec(v);
      var nums = v.match(/\d[\d.,]*/g) || [];
      if (nums.length >= 2) {
        return nums[0] + "\u2013" + nums[nums.length - 1] + (unitMatch ? "\u00A0" + unitMatch[1] : "");
      }
    }
    var cleaned = v.replace(/\s*\([^)]*\)/g, "").replace(/\s+от объекта защиты/gi, "");
    return typograph(cleaned);
  }
  function statusLabel(p) {
    if (p.availability) return p.availability;
    return p.on_site === false ? "вне сайта" : "под заказ";
  }
  function shortCat(name) {
    return String(name)
      .replace("Переносные (рюкзаки)", "Переносные")
      .replace("Детекторы БПЛА", "Детекторы")
      .replace("Доп. модули", "Модули")
      .replace("Купольные станции", "Купольные")
      .replace("Стационарные", "Стационарные");
  }
  function categories() {
    var seen = [];
    DATA.products.forEach(function (p) {
      if (p.category && seen.indexOf(p.category) < 0) seen.push(p.category);
    });
    return seen;
  }
  function catIndex(name) {
    return categories().indexOf(name);
  }
  function refreshMotion() {
    if (window.MotionKit && typeof window.MotionKit.refresh === "function") {
      try { window.MotionKit.refresh(); } catch (err) { /* motion опционален */ }
    }
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

  /* ============================================================
     02 ФЛАГМАНЫ — щит из трёх разнокалиберных плиток
     ============================================================ */
  function renderFlagships() {
    var box = $("[data-flagships]");
    if (!box) return;
    var list = DATA.products.filter(function (p) { return p.flagship; }).slice(0, 3);
    if (!list.length) return;
    box.innerHTML = list.map(function (p, i) {
      var lead = i === 0;
      var specs = keySpecs(p, 3);
      var specsHtml = specs.length
        ? specs.map(function (s) {
            return '<div><span>' + esc(s.label) + "</span><b>" + esc(typograph(s.value)) + "</b></div>";
          }).join("")
        : '<div><span>Характеристики</span><b>уточняются при запросе</b></div>';
      var price = p.price_dima == null
        ? '<span class="flag__price">по запросу<small>цена по запросу</small></span>'
        : '<span class="flag__price">' + priceHtml(p) + "<small>цена поставщика · ориентир</small></span>";
      return '' +
        '<article class="flag ' + (lead ? "flag--lead" : "flag--side") + '" data-open="' + esc(p.id) + '">' +
          '<div class="flag__media"><img src="' + esc(mainPhoto(p)) + '" alt="' + esc(p.name) + '" loading="' + (lead ? "eager" : "lazy") + '"></div>' +
          '<div class="flag__body">' +
            '<div class="flag__kicker"><span><b>Флагман ' + pad2(i + 1) + "</b> · " + esc(p.category) + "</span><span>" + esc(statusLabel(p)) + "</span></div>" +
            '<h3 class="flag__name">' + esc(p.name) + "</h3>" +
            '<p class="flag__short">' + esc(p.short || "") + "</p>" +
            '<div class="flag__specs">' + specsHtml + "</div>" +
            '<div class="flag__foot">' + price +
              '<span class="flag__more">Подробнее <span aria-hidden="true">→</span></span>' +
            "</div>" +
          "</div>" +
        "</article>";
    }).join("");
  }

  /* ============================================================
     02.1 СРАВНЕНИЕ — паспортная ведомость
     ============================================================ */
  function renderCompare() {
    var box = $("[data-compare]");
    if (!box) return;
    var flags = DATA.products.filter(function (p) { return p.flagship; }).slice(0, 3);
    if (!flags.length) return;
    var rows = [
      ["Диапазон частот", ["диапазон"]],
      ["Мощность передатчиков", ["мощность передатчиков", "выходная мощность", "суммарная"]],
      ["Дальность", ["дальность"]],
      ["Питание", ["питание"]],
      ["Вес", ["вес"]],
      ["Гарантия", ["гарантия"]]
    ];
    var head = '<thead><tr><th class="cmp__label">Характеристика</th>' + flags.map(function (p) {
      return '<th><span class="cmp__cat">' + esc(p.category) + "</span>" +
        '<span class="cmp__name">' + esc(p.name) + "</span>" +
        '<button class="cmp__more" type="button" data-open="' + esc(p.id) + '">Подробнее <span aria-hidden="true">→</span></button></th>';
    }).join("") + "</tr></thead>";
    var body = "<tbody>" + rows.map(function (r) {
      return '<tr><th class="cmp__label">' + esc(r[0]) + "</th>" + flags.map(function (p) {
        var s = specFind(p, r[1]);
        return "<td>" + esc(s ? typograph(s.value) : "—") + "</td>";
      }).join("") + "</tr>";
    }).join("") +
      '<tr class="cmp__price"><th class="cmp__label">Цена поставщика</th>' + flags.map(function (p) {
        return "<td>" + priceHtml(p) + "</td>";
      }).join("") + "</tr></tbody>";
    box.innerHTML = '<div class="cmp__scroll"><table class="cmp">' + head + body + "</table></div>" +
      '<p class="cmp__note"><span>Данные — по паспортам изделий</span><span>Цены — ориентир поставщика, не оферта</span></p>';
  }

  /* ============================================================
     03 КАТАЛОГ — фильтры и ведомость
     ============================================================ */
  function renderChips() {
    var box = $("[data-chips]");
    if (!box) return;
    var counts = {};
    DATA.products.forEach(function (p) { counts[p.category] = (counts[p.category] || 0) + 1; });
    var archiveN = DATA.products.filter(function (p) { return p.on_site === false; }).length;
    box.innerHTML =
      '<button class="chip is-active" type="button" data-cat="all">Все <b>' + TOTAL + "</b></button>" +
      categories().map(function (c) {
        return '<button class="chip" type="button" data-cat="' + esc(c) + '">' + esc(shortCat(c)) + " <b>" + (counts[c] || 0) + "</b></button>";
      }).join("") +
      (archiveN ? '<button class="chip chip--archive" type="button" data-archive="1">Вне сайта <b>' + archiveN + "</b></button>" : "");
    syncChips();
  }
  function syncChips() {
    $$("[data-chips] [data-cat]").forEach(function (b) {
      b.classList.toggle("is-active", !state.archiveOnly && b.getAttribute("data-cat") === state.cat);
    });
    $$("[data-chips] [data-archive]").forEach(function (b) {
      b.classList.toggle("is-active", state.archiveOnly);
    });
  }
  function filtered() {
    var q = state.q.toLowerCase().trim();
    var list = DATA.products.filter(function (p) {
      if (state.archiveOnly && p.on_site !== false) return false;
      if (state.cat !== "all" && p.category !== state.cat) return false;
      if (!q) return true;
      var blob = [p.name, p.category, p.short, p.description]
        .concat((p.specs || []).map(function (s) { return s.label + " " + s.value; }))
        .join(" ").toLowerCase();
      return blob.indexOf(q) >= 0;
    });
    if (state.sort === "price-asc") list.sort(function (a, b) { return (a.price_dima == null ? 1e12 : a.price_dima) - (b.price_dima == null ? 1e12 : b.price_dima); });
    if (state.sort === "price-desc") list.sort(function (a, b) { return (b.price_dima == null ? -1 : b.price_dima) - (a.price_dima == null ? -1 : a.price_dima); });
    if (state.sort === "name") list.sort(function (a, b) { return a.name.localeCompare(b.name, "ru"); });
    return list;
  }

  /* одна строка из 2–3 ключевых ТТХ: «300–5900 МГц · до 240 Вт · 50–200 м» */
  var BAD_SPEC_LABEL = /(тип|применен|ттх|цена|цен[аы]|наличи|комплект|примечан|описан|назначен|состоян|статус|источник|ссылк|фото)/i;
  function specLineHTML(p) {
    /* в строке ведомости — только короткие паспортные значения:
       длинные описания уходят в карточку, клик по строке открывает модалку */
    var specs = keySpecs(p, 8).filter(function (s) {
      var v = shortSpecValue(s.label, s.value);
      if (BAD_SPEC_LABEL.test(s.label)) return false;
      if (v.length > 30) return false;
      if (/[.!?]$/.test(v)) return false;
      return true;
    }).slice(0, 3);
    if (!specs.length) {
      return '<div class="row__specs row__specs--empty">' +
        (p.on_site === false ? "вне сайта · характеристики уточняются" : "характеристики уточняются при запросе") + "</div>";
    }
    var parts = specs.map(function (s) {
      return '<span class="spec" title="' + esc(typograph(s.label) + ": " + typograph(s.value)) + '"><i>' +
        esc(s.label) + "</i><b>" + esc(shortSpecValue(s.label, s.value)) + "</b></span>";
    });
    return '<div class="row__specs">' + parts.join("") + "</div>";
  }

  function rowHTML(p) {
    var no = posOf[p.id] || 0;
    var idxLabel = pad2(no) + "/" + pad2(TOTAL);
    var thumb = hasPhoto(p)
      ? '<span class="card__media row__thumb"><img src="' + esc(mainPhoto(p)) + '" alt="" loading="lazy"></span>'
      : '<span class="card__media row__thumb row__thumb--none"><img src="' + NO_PHOTO + '" alt="" loading="lazy"></span>';
    return '' +
      '<article class="card row" data-open="' + esc(p.id) + '" data-id="' + esc(p.id) + '" data-line="' + pad2(no) + '">' +
        '<span class="row__idx">' + pad2(no) + "<small>/" + pad2(TOTAL) + "</small></span>" +
        thumb +
        '<div class="row__main">' +
          '<div class="row__cat"><span class="row__pid">' + idxLabel + "</span><span>" + esc(p.category) + "</span></div>" +
          '<h4 class="card__name row__name">' + esc(p.name) + "</h4>" +
          '<div class="row__flags">' + badgesHTML(p) + "</div>" +
          specLineHTML(p) +
        "</div>" +
        '<div class="row__right">' +
          '<div class="row__price">' + priceHtml(p) + "</div>" +
          '<span class="row__cta">Подробнее <i aria-hidden="true">→</i></span>' +
        "</div>" +
      "</article>";
  }

  function groupHTML(catName, items) {
    var ci = catIndex(catName);
    var num = ci >= 0 ? pad2(ci + 1) : "—";
    return '<div class="group">' +
      '<div class="group__head">' +
        '<span class="group__num">' + num + "</span>" +
        '<h3 class="group__name">' + esc(catName) + "</h3>" +
        '<span class="group__count">' + positions(items.length) + "</span>" +
      "</div>" +
      '<div class="grid">' + items.map(rowHTML).join("") + "</div>" +
    "</div>";
  }

  function ledgerSumHTML(list) {
    var withPrice = list.filter(function (p) { return p.price_dima != null; }).length;
    var archiveN = list.filter(function (p) { return p.on_site === false; }).length;
    return "<span><b>Итого</b> " + positions(list.length) + "</span>" +
      "<span>с ценой <b>" + withPrice + "</b></span>" +
      "<span>по запросу <b>" + (list.length - withPrice) + "</b></span>" +
      "<span>вне сайта <b>" + archiveN + "</b></span>";
  }

  function renderGrid() {
    var box = $("[data-grid]");
    if (!box) return;
    var list = filtered();
    state.viewIds = list.map(function (p) { return p.id; });
    var count = $("[data-count]");
    if (count) count.textContent = "показано " + list.length + "\u00A0из " + TOTAL;
    var sum = $("[data-sum]");
    if (sum) sum.innerHTML = ledgerSumHTML(list);

    if (!list.length) {
      box.innerHTML = '<div class="empty">Ничего не нашлось. Сбросьте фильтр или измените запрос.</div>';
      setEmptyPreview();
      refreshMotion();
      return;
    }

    var groups;
    if (state.archiveOnly) {
      groups = [{ cat: "Вне сайта", items: list }];
    } else if (state.cat !== "all") {
      groups = [{ cat: state.cat, items: list }];
    } else if (state.sort !== "default") {
      groups = [{ cat: "Все категории · " + SORT_LABELS[state.sort], items: list }];
    } else {
      groups = categories().map(function (c) {
        return { cat: c, items: list.filter(function (p) { return p.category === c; }) };
      }).filter(function (g) { return g.items.length; });
    }
    box.innerHTML = groups.map(function (g) { return groupHTML(g.cat, g.items); }).join("");
    setPreview(list[0], false);
    refreshMotion();
  }

  /* ---------- поле образца ---------- */
  var pv = null;
  function initProof() {
    var proof = $("[data-proof]");
    if (!proof) return;
    pv = {
      img: $("[data-pv-img]", proof),
      name: $("[data-pv-name]", proof),
      badges: $("[data-pv-badges]", proof),
      specs: $("[data-pv-specs]", proof),
      price: $("[data-pv-price]", proof),
      open: $("[data-pv-open]", proof),
      count: $("[data-pv-count]", proof)
    };
  }
  function setPreview(p, animate) {
    if (!pv || !p) return;
    if (pv.currentId === p.id && !animate) return;
    pv.currentId = p.id;
    var src = mainPhoto(p);
    if (pv.img.getAttribute("src") !== src) {
      pv.img.src = src;
    }
    pv.img.alt = p.name;
    if (animate) {
      pv.img.classList.remove("is-swap");
      void pv.img.offsetWidth;
      pv.img.classList.add("is-swap");
    }
    pv.name.textContent = p.name;
    pv.badges.innerHTML = badgesHTML(p);
    var specs = keySpecs(p, 3);
    pv.specs.innerHTML = specs.length
      ? specs.map(function (s) {
          return '<div class="proof__spec"><i>' + esc(s.label) + "</i><b>" + esc(typograph(s.value)) + "</b></div>";
        }).join("")
      : '<div class="proof__spec"><i>характеристики</i><b>уточняются при запросе</b></div>';
    pv.price.innerHTML = priceHtml(p);
    pv.open.setAttribute("data-open", p.id);
    pv.open.setAttribute("aria-label", "Подробнее: " + p.name);
    if (pv.count) pv.count.textContent = pad2(posOf[p.id]) + " / " + pad2(TOTAL);
  }
  function setEmptyPreview() {
    if (!pv) return;
    pv.currentId = null;
    pv.img.removeAttribute("src");
    pv.img.alt = "";
    pv.name.textContent = "Позиции не выбраны";
    pv.badges.innerHTML = "";
    pv.specs.innerHTML = "";
    pv.price.innerHTML = "";
    pv.open.setAttribute("data-open", "");
    if (pv.count) pv.count.textContent = "— / " + pad2(TOTAL);
  }

  /* ============================================================
     МОДАЛКА ТОВАРА
     ============================================================ */
  function publicWarnings(p) {
    return (p.warnings || []).filter(function (w) { return /цен|изготовител/i.test(w); });
  }
  function openProduct(id) {
    var p = byId[id];
    if (!p) return;
    state.active = p;
    state.gallery = 0;
    var modal = $("[data-modal]");
    var photos = (p.photos && p.photos.length) ? p.photos : [NO_PHOTO];
    var warn = publicWarnings(p);
    $("[data-modal-body]").innerHTML = '' +
      '<button class="modal__close" data-close aria-label="Закрыть">×</button>' +
      '<div class="modal__grid">' +
        '<div class="modal__media">' +
          '<div class="gallery"><img data-gallery-main src="' + esc(photos[0]) + '" alt="' + esc(p.name) + '"></div>' +
          '<div class="gallery__thumbs">' + photos.map(function (ph, i) {
            return '<button class="gallery__thumb' + (i === 0 ? " is-active" : "") + '" data-thumb="' + i + '" aria-label="Фото ' + (i + 1) + '"><img src="' + esc(ph) + '" alt="" loading="lazy"></button>';
          }).join("") + "</div>" +
        "</div>" +
        '<div class="modal__info">' +
          '<div class="modal__cat">' + esc(p.category) + (p.flagship ? ' · <span class="flag-mark">флагман</span>' : "") + "</div>" +
          '<h2 class="modal__name">' + esc(p.name) + "</h2>" +
          (p.description ? '<p class="modal__desc">' + esc(p.description) + "</p>" : "") +
          '<table class="specs"><tbody>' + (p.specs || []).map(function (s) {
            return "<tr><th>" + esc(s.label) + "</th><td>" + esc(s.value) + "</td></tr>";
          }).join("") + "</tbody></table>" +
          (warn.length ? '<ul class="modal__warns">' + warn.map(function (w) {
            return "<li>" + esc(w) + "</li>";
          }).join("") + "</ul>" : "") +
          '<div class="modal__buy">' + priceHtml(p) +
            '<button class="ebtn ebtn--solid" type="button" data-add="' + esc(p.id) + '">Добавить в заявку</button></div>' +
          (p.price_source ? '<p class="modal__src">Источник цены: ' + esc(p.price_source) + "</p>" : "") +
        "</div>" +
      "</div>";
    modal.classList.add("is-open");
    modal.setAttribute("aria-hidden", "false");
    document.body.classList.add("is-locked");
  }
  function closeModal() {
    var modal = $("[data-modal]");
    if (!modal) return;
    modal.classList.remove("is-open");
    modal.setAttribute("aria-hidden", "true");
    document.body.classList.remove("is-locked");
  }

  /* ============================================================
     ЗАЯВКА (корзина)
     ============================================================ */
  function addToCart(id) {
    if (state.cart.indexOf(id) < 0) state.cart.push(id);
    renderCart();
    closeModal();
    openCart();
  }
  function removeFromCart(id) {
    state.cart = state.cart.filter(function (x) { return x !== id; });
    renderCart();
  }
  function cartProducts() {
    return state.cart.map(function (id) { return byId[id]; }).filter(Boolean);
  }
  function cartText(extra) {
    var lines = ["Заявка с каталога «В ОКОПЕ» (НПО «Киловатт»)"];
    if (cartProducts().length) {
      lines.push("", "Позиции:");
      cartProducts().forEach(function (p, i) {
        lines.push((i + 1) + ". " + p.name + (p.price_dima != null ? " — от " + money(p.price_dima) + "\u00A0₽" : " — цена по запросу"));
      });
    }
    if (extra) lines.push("", extra);
    lines.push("", "Прошу связаться для расчёта и сроков.");
    return lines.join("\n");
  }
  function renderCart() {
    var list = $("[data-cart-list]");
    if (!list) return;
    var items = cartProducts();
    var countEl = $("[data-cart-count]");
    var badgeEl = $("[data-cart-badge]");
    if (countEl) countEl.textContent = items.length;
    if (badgeEl) {
      badgeEl.textContent = items.length;
      badgeEl.classList.toggle("is-empty", items.length === 0);
    }
    list.innerHTML = items.length ? items.map(function (p) {
      return '<li class="cart__item">' +
        '<img src="' + esc(mainPhoto(p)) + '" alt="">' +
        "<div><b>" + esc(p.name) + "</b>" +
        (p.price_dima != null ? "<span>" + money(p.price_dima) + "\u00A0₽</span>" : "<span>по запросу</span>") +
        '</div><button class="cart__del" type="button" data-del="' + esc(p.id) + '" aria-label="Убрать">×</button></li>';
    }).join("") : '<li class="cart__empty">Пока пусто. Добавьте позиции из каталога — заявка соберётся сама.</li>';
  }
  function openCart() {
    var cart = $("[data-cart]");
    var overlay = $("[data-overlay]");
    if (cart) cart.classList.add("is-open");
    if (overlay) overlay.classList.add("is-on");
  }
  function closeCart() {
    var cart = $("[data-cart]");
    var overlay = $("[data-overlay]");
    if (cart) cart.classList.remove("is-open");
    if (overlay) overlay.classList.remove("is-on");
  }
  function copyText(text, btn) {
    var done = function () {
      if (!btn) return;
      var old = btn.textContent;
      btn.textContent = "Скопировано ✓";
      setTimeout(function () { btn.textContent = old; }, 1800);
    };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(done, function () { fallbackCopy(text, done); });
    } else fallbackCopy(text, done);
  }
  function fallbackCopy(text, cb) {
    var ta = document.createElement("textarea");
    ta.value = text;
    ta.style.position = "fixed";
    ta.style.opacity = "0";
    document.body.appendChild(ta);
    ta.select();
    try { document.execCommand("copy"); } catch (e) { /* старые браузеры */ }
    document.body.removeChild(ta);
    cb();
  }
  function formExtra() {
    var f = $("[data-request-form]");
    var extra = [];
    if (!f || !f.elements) return "";
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
    return extra.join("\n");
  }
  function submitRequest() {
    var text = cartText(formExtra());
    var tg = CONTACTS.tg || "";
    if (tg) {
      var url = "https://t.me/" + tg.replace(/^@/, "") + "?text=" + encodeURIComponent(text);
      window.open(url, "_blank");
      return;
    }
    copyText(text, $("[data-copy-request]"));
    var note = $("[data-request-note]");
    if (note) note.textContent = "Текст заявки скопирован — вставьте его в Telegram, WhatsApp или отправьте нам. Данные остаются у вас, пока вы сами их не отправите.";
  }

  /* ============================================================
     СОБЫТИЯ
     ============================================================ */
  function bind() {
    document.addEventListener("click", function (e) {
      if (!e.target.closest) return;

      var add = e.target.closest("[data-add]");
      if (add) {
        e.preventDefault();
        e.stopPropagation();
        addToCart(add.getAttribute("data-add"));
        return;
      }
      var del = e.target.closest("[data-del]");
      if (del) { removeFromCart(del.getAttribute("data-del")); return; }
      var thumb = e.target.closest("[data-thumb]");
      if (thumb) {
        var ti = +thumb.getAttribute("data-thumb");
        var p = state.active;
        if (p && p.photos && p.photos[ti]) {
          state.gallery = ti;
          var main = $("[data-gallery-main]");
          if (main) main.src = p.photos[ti];
          $$(".gallery__thumb").forEach(function (b) {
            b.classList.toggle("is-active", +b.getAttribute("data-thumb") === ti);
          });
        }
        return;
      }
      if (e.target.closest("[data-close]")) { closeModal(); return; }
      var cat = e.target.closest("[data-cat]");
      if (cat) {
        state.cat = cat.getAttribute("data-cat");
        state.archiveOnly = false;
        syncChips();
        renderGrid();
        return;
      }
      if (e.target.closest("[data-archive]")) {
        state.archiveOnly = !state.archiveOnly;
        if (state.archiveOnly) state.cat = "all";
        syncChips();
        renderGrid();
        return;
      }
      if (e.target.closest("[data-cart-toggle]")) { openCart(); return; }
      if (e.target.closest("[data-cart-close]") || e.target.closest("[data-overlay]")) { closeCart(); return; }
      if (e.target.closest("[data-copy-request]")) {
        copyText(cartText(formExtra()), e.target.closest("[data-copy-request]"));
        return;
      }
      if (e.target.closest("[data-submit-request]")) { submitRequest(); return; }

      var open = e.target.closest("[data-open]");
      if (open) {
        var id = open.getAttribute("data-open");
        if (!id) return;
        e.preventDefault();
        openProduct(id);
        return;
      }
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

    /* поле образца: наведение и клавиатурный фокус по строке */
    var lastHover = null;
    function previewFromRow(e) {
      var row = e.target.closest ? e.target.closest(".card.row") : null;
      if (!row) return;
      var id = row.getAttribute("data-id");
      if (!id || id === lastHover) return;
      lastHover = id;
      var p = byId[id];
      if (p) setPreview(p, true);
    }
    document.addEventListener("mouseover", previewFromRow);
    document.addEventListener("focusin", previewFromRow);
    var grid = $("[data-grid]");
    if (grid) grid.addEventListener("mouseleave", function () {
      lastHover = null;
      if (state.viewIds && state.viewIds.length) setPreview(byId[state.viewIds[0]], false);
    });

    /* плавный скролл по якорям (фолбэк без motion-кита) */
    document.addEventListener("click", function (e) {
      var a = e.target.closest ? e.target.closest('a[href^="#"]') : null;
      if (!a) return;
      var id = a.getAttribute("href");
      if (!id || id.length < 2) return;
      var el = document.querySelector(id);
      if (!el) return;
      e.preventDefault();
      el.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  }

  /* ============================================================
     СТАРТ
     ============================================================ */
  function init() {
    initProof();
    initScroll();
    renderFlagships();
    renderCompare();
    renderChips();
    renderGrid();
    renderCart();
    bind();
    var meta = $("[data-generated]");
    if (meta && DATA.generated) meta.textContent = DATA.generated;
    /* переключатель вариантов оформления */
    var alt = document.body.getAttribute("data-alt");
    var sw = $("[data-variant-switch]");
    if (sw && alt) {
      sw.setAttribute("href", alt);
      sw.textContent = document.body.getAttribute("data-theme") === "field" ? "Вариант 2 →" : "← Вариант 1";
    }
    if (window.CATALOG_READY) window.CATALOG_READY(DATA);
    /* глубокие ссылки на секции (скриншоты/шаринг) */
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
