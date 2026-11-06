/* Контакты и настройки каталога.
   Владелец: телефон +7 (999) 136-71-42 (ёмкая связка — только телефон).
   TG-кнопка: если задать tg, кнопка «Отправить заявку» откроет чат с готовым текстом;
   если пусто — текст заявки просто копируется (безопасный режим). */
window.SITE_CONTACTS = {
  tg: "",                       // например "vokope_ru" (без @) — необязательно
  phone: "+7 (999) 136-71-42",  // контакт владельца
  email: "",                    // необязательно
  note: ""
};

document.addEventListener("DOMContentLoaded", function () {
  var c = window.SITE_CONTACTS || {};
  var tgEl = document.querySelector("[data-contact-tg]");
  var phEl = document.querySelector("[data-contact-phone]");
  var emEl = document.querySelector("[data-contact-email]");
  if (tgEl) tgEl.textContent = c.tg ? "@" + c.tg.replace(/^@/, "") : "уточняется";
  if (phEl) phEl.textContent = c.phone || "уточняется";
  if (emEl) emEl.textContent = c.email || "уточняется";
  if (tgEl && c.tg) {
    tgEl.innerHTML = '<a href="https://t.me/' + c.tg.replace(/^@/, "") + '" target="_blank" rel="noopener">@' + c.tg.replace(/^@/, "") + "</a>";
  }
  if (phEl && c.phone) {
    phEl.innerHTML = '<a href="tel:' + c.phone.replace(/[^\d+]/g, "") + '">' + c.phone + "</a>";
  }
  if (emEl && c.email) {
    emEl.innerHTML = '<a href="mailto:' + c.email + '">' + c.email + "</a>";
  }
});
