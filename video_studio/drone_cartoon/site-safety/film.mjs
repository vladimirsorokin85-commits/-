import { createCanvas, GlobalFonts, loadImage } from '@napi-rs/canvas';
import { fileURLToPath } from 'node:url';
import { ease, ellipse, fill, line, path, rounded } from '../bulat/art.mjs';
import { place } from '../tak710/locations.mjs';
import { openBroll } from './broll.mjs';
import { DURATION, SHOTS, WIPE } from './story.mjs';

export const WIDTH = 540;
export const HEIGHT = 960;
const W = WIDTH, H = HEIGHT;
const ink = '#1e3b3e', dark = '#224346', cream = '#f8eed6', mint = '#aed1ba', gold = '#f2ca7d';
const photos = new Map(await Promise.all([4, 16].map(async (id) => [
  id, await loadImage(fileURLToPath(new URL(`./assets/archive-${id}.jpg`, import.meta.url))),
])));
let ready = false;
function fonts() {
  if (ready) return;
  for (const face of ['Black', 'Medium']) {
    const path = fileURLToPath(new URL(`../../fonts/Roboto-${face}.woff`, import.meta.url));
    if (!GlobalFonts.registerFromPath(path, `Site${face}`)) throw new Error(`Шрифт не загружен: ${face}`);
  }
  ready = true;
}
function type(ctx, value, x, y, size, color, { align = 'left', medium = false, track = 0 } = {}) {
  ctx.font = `${size}px Site${medium ? 'Medium' : 'Black'}`;
  ctx.textBaseline = 'alphabetic'; ctx.fillStyle = color;
  if (!track) { ctx.textAlign = align; ctx.fillText(value, x, y); return; }
  ctx.textAlign = 'left';
  const parts = [...value].map((ch) => [ch, ctx.measureText(ch).width + track]);
  const width = parts.reduce((sum, [, w]) => sum + w, -track);
  x -= align === 'right' ? width : align === 'center' ? width / 2 : 0;
  for (const [ch, w] of parts) { ctx.fillText(ch, x, y); x += w; }
}
function board(ctx, t, pale = false, alt = false) {
  const shade = ctx.createLinearGradient(0, 0, W, H);
  shade.addColorStop(0, pale ? '#f0e5cc' : alt ? '#385d59' : '#254a50');
  shade.addColorStop(1, pale ? '#c7cdb2' : '#172f36');
  fill(ctx, shade, 0, 0, W, H);
  const hair = pale ? '#46675c31' : '#a6c5b13b';
  for (let i = -2; i < 8; i++) {
    const y = i * 137 - (t * 10 % 137);
    path(ctx, [[0, y + 144], [540, y]], null, hair, 1.2);
  }
  for (let x = 18; x <= W; x += 25) for (let y = 23; y <= H; y += 23) fill(ctx, hair, x, y, 1.1, 1.1);
}
function header(ctx, left, right, pale = false) {
  fill(ctx, pale ? '#9b7e51' : gold, 37, 57, 4, 21);
  type(ctx, left, 50, 73, 12, pale ? ink : cream, { track: 1.5 });
  type(ctx, right, 502, 73, 12, pale ? ink : cream, { track: 1.5, align: 'right' });
  line(ctx, 37, 94, 466, pale ? '#4e746d62' : '#c8ddbd75');
}
function footer(ctx, t, label, pale = false) {
  const color = pale ? '#3f665d' : '#bcddc1';
  line(ctx, 37, 898, 466, pale ? '#5e786657' : '#c3dfb834');
  line(ctx, 37, 898, 466 * t / DURATION, color, 1.5);
  type(ctx, label, 37, 925, 11.5, color, { track: 1.20 });
  const seconds = Math.floor(t);
  type(ctx, `${String(Math.floor(seconds / 60)).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')}`, 502, 925, 12, color,
    { align: 'right', track: 1 });
}
function heading(ctx, a, b, pale = false, sizes = [73, 77]) {
  type(ctx, a, 34, 175, sizes[0], pale ? ink : cream);
  type(ctx, b, 34, 249, sizes[1], pale ? '#547b68' : gold);
}
function card(ctx, y, label, lines, pale = false) {
  rounded(ctx, pale ? '#ede7cd' : '#2c5052', 37, y, 466, 114, 7, pale ? '#86a08d' : '#779c8a');
  fill(ctx, pale ? '#9b7d51' : gold, 37, y + 17, 3.6, 75);
  type(ctx, label, 53, y + 25, 12, pale ? '#547a6b' : gold, { track: 1.45 });
  for (const [i, value] of lines.entries()) type(ctx, value, 53, y + 54 + i * 26, 23, pale ? ink : cream, { medium: true });
}
function star(ctx, x, y, size, color = gold) {
  path(ctx, [[x, y - size], [x + 2.5, y - 2.4], [x + size * .72, y], [x + 2.5, y + 2.4],
    [x, y + size], [x - 2.5, y + 2.4], [x - size * .72, y], [x - 2.5, y - 2.4]], color);
}
function cloud(ctx, x, y, k) {
  ellipse(ctx, '#d4dabbc0', x, y, 49 * k, 10 * k);
  ellipse(ctx, '#d7ddc0', x - 8 * k, y - 7 * k, 28 * k, 15 * k);
}
function forklift(ctx, x, y, k, t) {
  ctx.save(); ctx.translate(x, y); ctx.scale(k, k);
  ellipse(ctx, '#24494956', 7, 6, 48, 8);
  rounded(ctx, '#a96d4a', -36, -36, 71, 31, 6, '#4d5f54', 2.8);
  rounded(ctx, '#edbc70', -36, -42, 67, 31, 5, '#846953', 2.3);
  path(ctx, [[-28, -43], [-25, -77], [22, -76], [26, -44]], '#7c9c86', '#435f55', 3.5);
  path(ctx, [[-25, -77], [23, -77]], null, '#eac784', 4.5);
  ellipse(ctx, '#e0a867', 0, -62, 9, 9);
  path(ctx, [[30, -78], [30, -14], [60, -14]], null, '#385951', 4.0);
  rounded(ctx, '#c9b48a', 35, -44, 26, 28, 3, '#87775b', 2.5);
  for (const w of [-22, 22]) {
    ellipse(ctx, '#233d3d', w, -6, 13, 13);
    ellipse(ctx, '#83978a', w, -6, 5.8, 5.8);
  }
  line(ctx, -62 - 10 * Math.sin(t * 4), -19, 16, '#e0d6b88a', 1.7);
  ctx.restore();
}
function yard(ctx, t, abs) {
  board(ctx, t, true);
  heading(ctx, 'Дрон над', 'объектом.', true, [80, 76]);
  header(ctx, 'ПАМЯТКА ДЛЯ СОТРУДНИКОВ', '01 / 06', true);
  ctx.save(); ctx.beginPath(); ctx.rect(37, 285, 466, 402); ctx.clip();
  const sky = ctx.createLinearGradient(0, 280, 0, 674);
  sky.addColorStop(0, '#8eb8aa'); sky.addColorStop(1, '#d7d1a3');
  fill(ctx, sky, 37, 285, 466, 402);
  ellipse(ctx, '#f4ce8d', 393, 360, 43, 43);
  cloud(ctx, 123 - t * 13, 361, 1.07); cloud(ctx, 271 + t * 8, 401, .69);
  path(ctx, [[37, 487], [102, 443], [212, 485], [318, 430], [503, 484], [503, 687], [37, 687]], '#7b9e87');
  path(ctx, [[37, 633], [502, 569], [503, 687], [37, 687]], '#65837a');
  path(ctx, [[37, 648], [502, 589], [503, 659], [37, 712]], '#4b6f68');
  for (let i = -1; i < 12; i++) {
    const x = 42 + i * 43 - (t * 39 % 43), y = 685 - (x - 37) * .132;
    path(ctx, [[x, y], [x + 19, y - 3]], null, '#dbcb97', 1.9);
  }
  path(ctx, [[72, 544], [236, 517], [305, 482], [484, 503], [483, 611], [72, 641]], '#b8c8a7', '#365e59', 3.5);
  path(ctx, [[72, 544], [236, 517], [236, 625], [72, 641]], '#91ac97', '#527b6c', 2.4);
  path(ctx, [[65, 539], [122, 504], [305, 476], [486, 498], [307, 525], [233, 537]], '#557e73', '#416d65', 2.7);
  for (let i = 0; i < 4; i++) {
    const x = 251 + i * 55, y = 539 - i * 4;
    rounded(ctx, '#557d70', x, y + 35, 43, 54, 2, '#496d62', 2.2);
    for (let r = 0; r < 5; r++) line(ctx, x + 4, y + 42 + r * 8, 34, '#8eaa90', 1.2);
    rounded(ctx, '#6f9285', x, y + 5, 43, 16, 2, '#527c6c');
  }
  rounded(ctx, '#3c6b60', 91, 562, 126, 24, 2);
  type(ctx, 'ПРОИЗВОДСТВО', 155, 578, 11, cream, { align: 'center', track: 1.3 });
  forklift(ctx, 133 + 79 * t, 675 - 10 * t, .76, t);
  ctx.restore();
  rounded(ctx, null, 37, 285, 466, 402, 2, '#688c79', 1.7);
  card(ctx, 726, 'ЗНАТЬ ЗАРАНЕЕ', ['Кому сообщить и как действовать', 'по плану своего объекта.'], true);
  footer(ctx, abs, 'РИСОВАННАЯ СЦЕНА / ОБЫЧНАЯ СМЕНА', true);
}
function broll(ctx, t, abs, { kind }, footage) {
  const stock = kind === 'warehouse';
  board(ctx, t, stock, !stock);
  header(ctx, stock ? 'ОБЫЧНАЯ РАБОТА СКЛАДА' : 'КАНАЛ СВЯЗИ', 'ВИДЕО', stock);
  heading(ctx, stock ? 'Обычная' : 'Кому', stock ? 'смена.' : 'сообщить?', stock, stock ? [72, 90] : [85, 77]);
  rounded(ctx, stock ? '#e7dfc2' : '#315759', 30, 306, 480, 326, 8, stock ? '#8a9e87' : '#82a18c', 1.8);
  ctx.drawImage(footage(kind, t), 38, 315, 464, 261);
  fill(ctx, '#2d655622', 38, 315, 464, 261);
  fill(ctx, stock ? '#b39561' : gold, 45, 594, 4.5, 18);
  type(ctx, stock ? 'ИЛЛЮСТРАТИВНАЯ СЪЁМКА' : 'ПЕЙЗАЖ ИЗ ПРИСЛАННОГО ВИДЕО', 57, 609, 15,
    stock ? ink : cream, { track: 1.1 });
  if (stock) type(ctx, 'Tiger Lily / Pexels', 490, 608, 12, ink, { align: 'right', medium: true });
  card(ctx, 726, stock ? 'КОНТЕКСТ' : 'ПОДГОТОВКА', stock ? ['Склад в обычную смену.', 'Не запись происшествия.'] :
    ['Заранее узнайте, кому сообщать', 'на вашем объекте.'], stock);
  footer(ctx, abs, stock ? 'ВИДЕО / НЕ СЪЁМКА УСТРОЙСТВА' : 'ВИДЕО / ТОЛЬКО ПОЛЕ И НЕБО', stock);
}
function aisle(ctx, t, abs) {
  board(ctx, t);
  header(ctx, 'ПРОИЗВОДСТВО', 'РИСУНОК');
  place(ctx, 0, t, { x: 37, y: 130, w: 466, h: 477 });
  rounded(ctx, null, 37, 130, 466, 477, 1, '#92ac97', 1.4);
  type(ctx, 'Важен порядок.', 36, 721, 52, cream);
  type(ctx, 'Уточните его до начала смены.', 36, 777, 28, gold, { medium: true });
  footer(ctx, abs, 'ГРАЖДАНСКИЙ ОБЪЕКТ');
}
function archive(ctx, t, abs, { photo }) {
  const pale = photo === 16;
  board(ctx, t, pale, true);
  header(ctx, 'ФОТОМАТЕРИАЛЫ ВЛАДЕЛЬЦА', 'ФОТО', pale);
  heading(ctx, '«Стриж»', 'внешний вид.', pale, [81, 61]);
  const x = 63, y = 282 + 7 * (1 - ease(t / .5)), d = 414;
  rounded(ctx, '#1b343c30', x + 8, y + 9, d + 12, d + 12, 5);
  rounded(ctx, pale ? '#f6edd4' : '#c8cfb5', x - 7, y - 7, d + 14, d + 14, 5);
  ctx.drawImage(photos.get(photo), x, y, d, d);
  card(ctx, 736, 'СТАТИЧНОЕ ФОТО', ['Только общий вид устройства.', 'Не испытание и не демонстрация.'], pale);
  footer(ctx, abs, 'ФОТО / ВИД СНАРУЖИ', pale);
}
function phoneIcon(ctx, x, y, k, paper = false) {
  ctx.save(); ctx.translate(x, y); ctx.scale(k, k);
  rounded(ctx, paper ? '#527669' : '#193c41', -59, -103, 118, 203, 18, '#9abba6', 2.2);
  rounded(ctx, paper ? '#cce0be' : '#b3c9a8', -50, -82, 100, 152, 9);
  line(ctx, -16, 83, 31, '#8daa90', 3.2);
  path(ctx, [[-24, -50], [24, -50], [24, 1], [-7, 1], [-20, 16], [-20, 1], [-26, 1]], '#456f62');
  for (const dx of [-12, 1, 14]) ellipse(ctx, cream, dx, -25, 3.2, 3.2);
  ctx.restore();
}
function disk(ctx, color, x, y, r, t) {
  ellipse(ctx, color, x, y, r, r);
  ellipse(ctx, null, x, y, r + 13, r + 12, '#d2dfbc9b', 1.2);
  ellipse(ctx, null, x + Math.cos(t * 1.45) * 6, y, r + 25, r + 20, '#c3d9b868', 1.3);
  star(ctx, x + r * .77, y - r * .84, 13 + 2.4 * Math.sin(t * 2.1));
}
function report(ctx, t, abs, { close }) {
  board(ctx, t, close, true);
  header(ctx, 'КАНАЛ СВЯЗИ', close ? 'БЕЗОПАСНОЕ МЕСТО' : '03 / 06', close);
  heading(ctx, close ? 'Сначала' : 'Сообщите', close ? 'безопасность.' : 'ответственному.', close, [72, close ? 59 : 49]);
  disk(ctx, close ? '#a8c4a1' : '#548177', 270, 471, 146, t);
  ctx.save(); ctx.translate(270, 474 + 9 * Math.sin(t * 1.45)); ctx.rotate((close ? .12 : -.16) + .045 * Math.sin(t * 1.8));
  phoneIcon(ctx, 0, 0, close ? 1.3 : 1.22, close);
  ctx.restore();
  card(ctx, 726, 'ВАЖНО', close ? ['Не ведите наблюдение', 'с открытой площадки.'] : ['Свяжитесь с ответственным', 'из безопасного места.'], close);
  footer(ctx, abs, 'СВЯЗЬ / ПО ПОРЯДКУ ОБЪЕКТА', close);
}
function camera(ctx, t, abs) {
  board(ctx, t, true);
  header(ctx, 'БЕЗОПАСНОСТЬ ПЕРСОНАЛА', '04 / 06', true);
  heading(ctx, 'Не выходите', 'ради съёмки.', true, [64, 65]);
  disk(ctx, '#c2ab81', 270, 471, 150, t);
  const y = 464 + 6 * Math.sin(t * 1.66);
  rounded(ctx, '#385f57', 171, y - 51, 198, 111, 20, '#294d4b', 3);
  rounded(ctx, '#385f57', 213, y - 69, 59, 34, 6);
  ellipse(ctx, '#698f7a', 268, y + 4, 44, 44, '#153c3f', 4);
  ellipse(ctx, '#243f42', 268, y + 4, 31, 31);
  ellipse(ctx, '#82a495', 259, y - 5, 10, 7);
  ellipse(ctx, null, 270, 471, 126, 126, '#c2765e', 14);
  path(ctx, [[184, 386], [356, 556]], null, '#c2765e', 14);
  card(ctx, 726, 'ПРИ ОПОВЕЩЕНИИ', ['Сначала — безопасность.', 'Следуйте плану объекта.'], true);
  footer(ctx, abs, 'ПАМЯТКА / БЕЗ САМОСТОЯТЕЛЬНЫХ ДЕЙСТВИЙ', true);
}
function plan(ctx, t, abs, { close }) {
  board(ctx, t, close, true);
  header(ctx, 'ГОТОВНОСТЬ СМЕНЫ', 'ПЛАН', close);
  heading(ctx, 'План', 'объекта.', close, [81, 79]);
  const e = 1 - ease(t / .48);
  ctx.save(); ctx.translate(close ? 281 : 270, 484 + e * 17);
  ctx.rotate((close ? -.075 : .07) * (1 - .5 * e));
  rounded(ctx, '#233e426c', -155, -159, 319, 335, 17);
  rounded(ctx, '#cdaa73', -164, -166, 315, 334, 14, '#6c805f', 2.8);
  rounded(ctx, '#f3e9c9', -149, -152, 284, 302, 8, '#b99e71');
  rounded(ctx, '#567c6e', -56, -181, 99, 34, 7, '#3b6057', 2.3);
  const list = ['Кто отвечает', 'Где безопасно', 'Что делать после сигнала'];
  for (const [i, value] of list.entries()) {
    const y = -68 + 72 * i;
    rounded(ctx, '#d2dfb8', -132, y - 23, 33, 33, 5, '#97a78a');
    path(ctx, [[-124, y - 8], [-117, y - 1], [-106, y - 14]], null, '#528169', 3.4);
    type(ctx, value, -87, y, 17, ink, { medium: true });
    line(ctx, -129, y + 22, 239, '#9baf8ea5');
  }
  ctx.restore();
  card(ctx, 726, 'ДЕЙСТВУЙТЕ ПО ПЛАНУ', ['Следуйте указаниям служб', 'и ответственного на объекте.'], close);
  footer(ctx, abs, 'ПЛАН / ПРАВИЛА ВАШЕГО ОБЪЕКТА', close);
}
function distance(ctx, t, abs) {
  board(ctx, t, false, true);
  header(ctx, 'ЕСЛИ НАЙДЕНЫ ОБЛОМКИ', '05 / 06');
  heading(ctx, 'Держите', 'дистанцию.', false, [82, 73]);
  disk(ctx, '#546e62', 270, 474, 145, t);
  path(ctx, [[270, 344], [394, 550], [148, 550]], '#e6ba72', '#f3d297', 5);
  rounded(ctx, '#4c6252', 259, 398, 22, 94, 8);
  ellipse(ctx, '#4c6252', 270, 520, 12, 12);
  card(ctx, 726, 'НЕ ПРИБЛИЖАЙТЕСЬ', ['Не трогайте и не перемещайте', 'упавший аппарат или обломки.']);
  footer(ctx, abs, 'ОПАСНАЯ НАХОДКА / ДИСТАНЦИЯ');
}
function help(ctx, t, abs) {
  board(ctx, t, true);
  header(ctx, 'НЕ ТРОГАЙТЕ НАХОДКУ', 'СООБЩЕНИЕ', true);
  heading(ctx, 'Сообщите', 'службам.', true, [79, 80]);
  disk(ctx, '#abc4a2', 270, 468, 145, t);
  phoneIcon(ctx, 272, 471 + 7 * Math.sin(t * 1.34), 1.25, true);
  card(ctx, 726, 'ИЗ БЕЗОПАСНОГО МЕСТА', ['Сообщите экстренным службам', 'о находке. Не возвращайтесь к ней.'], true);
  footer(ctx, abs, 'ПАМЯТКА / ОБЩИЕ РЕКОМЕНДАЦИИ', true);
}
function final(ctx, t, abs) {
  board(ctx, t, false, true);
  header(ctx, 'БЕЗОПАСНОСТЬ НА ОБЪЕКТЕ', '06 / 06');
  heading(ctx, 'Три', 'правила.', false, [81, 89]);
  const rows = [
    ['Дистанция', 'Не подходите к находке.'],
    ['Сообщение', 'Свяжитесь с ответственным.'],
    ['План', 'Следуйте указаниям на объекте.'],
  ];
  for (const [i, [title, note]] of rows.entries()) {
    const e = 1 - ease((t - .17 * i) / .45);
    const x = 37 + 46 * e, y = 298 + 143 * i;
    rounded(ctx, '#315659', x, y, 466, 121, 8, '#87ae98');
    ellipse(ctx, gold, x + 48, y + 59, 26, 26);
    type(ctx, String(i + 1), x + 48, y + 68, 26, dark, { align: 'center' });
    type(ctx, title, x + 91, y + 54, 40, cream);
    type(ctx, note, x + 93, y + 85, 22, mint, { medium: true });
  }
  type(ctx, 'При угрозе — указания служб и план объекта.', 38, 813, 20, mint, { medium: true });
  footer(ctx, abs, 'ПАМЯТКА ДЛЯ ГРАЖДАНСКОГО ОБЪЕКТА');
}

const scenes = { yard, warehouse: broll, landscape: broll, aisle, archive, report, camera, plan, distance, help, final };
function tile() {
  const c = createCanvas(117, 121), ctx = c.getContext('2d'), data = ctx.createImageData(117, 121);
  let seed = 120;
  for (let i = 0; i < data.data.length; i += 4) {
    seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0;
    data.data[i] = seed >>> 31 ? 239 : 23;
    data.data[i + 1] = seed >>> 31 ? 238 : 43;
    data.data[i + 2] = seed >>> 31 ? 208 : 43;
    data.data[i + 3] = (seed >>> 21) % 25;
  }
  ctx.putImageData(data, 0, 0);
  return c;
}
export function createFilm(scale = 2, { ffmpeg, footage = openBroll(ffmpeg) } = {}) {
  fonts();
  const canvas = createCanvas(W * scale, H * scale), ctx = canvas.getContext('2d');
  const texture = ctx.createPattern(tile(), 'repeat');
  return {
    canvas, draw(seconds) {
      const t = Math.min(DURATION, Math.max(0, seconds));
      const i = SHOTS.findLastIndex(({ start }) => t >= start), shot = SHOTS[i];
      const local = t - shot.start;
      ctx.setTransform(scale, 0, 0, scale, 0, 0);
      ctx.lineJoin = 'round'; ctx.lineCap = 'round';
      scenes[shot.kind](ctx, local, t, shot, footage);
      ctx.save(); ctx.globalAlpha = .32; fill(ctx, texture, 0, 0, W, H); ctx.restore();
      if (i && local < WIPE) {
        const x = -185 + 920 * ease(local / WIPE);
        path(ctx, [[x, 0], [x + 32, 0], [x - 109, H], [x - 146, H]], '#f2d59336');
      }
      return canvas;
    },
  };
}
