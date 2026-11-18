import { createCanvas, GlobalFonts, loadImage } from '@napi-rs/canvas';
import { fileURLToPath } from 'node:url';
import QRCode from 'qrcode';
import { ease, ellipse, fill, line, path, rounded } from '../bulat/art.mjs';
import { C, product, setArt, text } from './art.mjs';
import { CHAPTERS, CONTACTS, DESIGN_CUT, DURATION, KIT_CUT, WIPE, chapterAt } from './story.mjs';

export const WIDTH = 540;
export const HEIGHT = 960;
const W = WIDTH, H = HEIGHT;
const logo = await loadImage(fileURLToPath(new URL('../bulat/assets/v-okope-white.png', import.meta.url)));
let prepared = false;
function fonts() {
  if (prepared) return;
  for (const face of ['Black', 'Medium']) {
    const file = fileURLToPath(new URL(`../../fonts/Roboto-${face}.woff`, import.meta.url));
    if (!GlobalFonts.registerFromPath(file, `Tak${face}`)) throw new Error(`Шрифт не загружен: ${face}`);
  }
  prepared = true;
}
function base(ctx, n, label, color = C.paper, dark = false) {
  fill(ctx, color, 0, 0, W, H);
  const ink = dark ? C.mint : C.ink;
  for (let x = 19; x < W; x += 24) for (let y = 27; y < H; y += 23) {
    fill(ctx, dark ? '#c8dfc326' : '#3b6a6324', x, y, 1.1, 1.1);
  }
  fill(ctx, dark ? C.amber : '#a78354', 36, 45, 4.5, 18);
  text(ctx, label, 50, 58, 12, ink, { track: 1.7 });
  text(ctx, `0${n} / 05`, 503, 58, 12, ink, { align: 'right', track: 1.35 });
  line(ctx, 37, 77, 466, dark ? '#68837b' : '#919f8b');
}
function footer(ctx, t, label, dark = false) {
  const ink = dark ? C.mint : C.muted;
  line(ctx, 37, 901, 466, dark ? '#5c7f74' : '#9ca892');
  line(ctx, 37, 901, 466 * t / DURATION, ink, 1.8);
  text(ctx, label, 37, 927, 10.2, ink, { track: 1.55 });
  text(ctx, `00:${String(Math.floor(t)).padStart(2, '0')}`, 503, 927, 10.2, ink, { align: 'right', track: 1.25 });
}
function tag(ctx, value, x, y, w, bg = '#355450', color = C.cream) {
  rounded(ctx, bg, x, y, w, 28, 4);
  text(ctx, value, x + 9, y + 18.5, 10.5, color, { track: 1.4 });
}
function copy(ctx, chip, lines, dark = false) {
  rounded(ctx, dark ? '#374848' : '#dedfca', 37, 768, 466, 102, 8, dark ? '#6c8075' : '#a5aa97');
  fill(ctx, dark ? C.amber : '#9f8357', 37, 785, 3, 56);
  text(ctx, chip, 54, 791, 10.5, dark ? C.amber : C.muted, { track: 1.65 });
  lines.forEach((value, i) => text(ctx, value, 54, 819 + 25 * i, 19, dark ? C.cream : C.ink, { medium: true }));
}
function headline(ctx, first, second, a = 73, b = 75, dark = false) {
  text(ctx, first, 35, 151, a, dark ? C.cream : C.ink);
  text(ctx, second, 35, 220, b, dark ? C.amber : '#607b70');
}
function studio(ctx, x, y, w, h) {
  const tint = ctx.createLinearGradient(x - 30, y, x + w, y + h);
  tint.addColorStop(0, '#678578'); tint.addColorStop(.5, '#50756d'); tint.addColorStop(1, '#2e5353');
  rounded(ctx, tint, x, y, w, h, 9, '#69877a', 1.8);
}
function rising(ctx, x, y, radius, color) {
  path(ctx, [[x, y - radius], [x + radius * .2, y - radius * .18], [x + radius * .64, y],
    [x + radius * .21, y + radius * .17], [x, y + radius], [x - radius * .25, y + radius * .18],
    [x - radius * .64, y], [x - radius * .21, y - radius * .22]], color);
}
function hero(ctx, t) {
  base(ctx, 1, 'XMETIX / ПЕРВАЯ ПОМОЩЬ');
  text(ctx, 'XMETIX', 34, 157, 87, C.ink);
  rounded(ctx, C.ink, 356, 105, 146, 56, 8);
  text(ctx, 'TAK710', 429, 141, 28, C.amber, { align: 'center', track: 1 });
  text(ctx, 'Автоматический жгут', 37, 218, 39, '#607b70');
  studio(ctx, 37, 251, 466, 482);
  const arrival = ease(t / .65);
  ellipse(ctx, '#92ad93', 270, 495, 178, 162);
  ellipse(ctx, null, 270, 495, 188, 174, '#a6bc9e', 1.2);
  ellipse(ctx, null, 270, 495, 204, 193, '#7c9c8c', 1.4);
  ellipse(ctx, '#192c2a61', 273, 658, 145, 21);
  rising(ctx, 421, 369, 17 * arrival, '#ffda88');
  rising(ctx, 116, 595, 12 * arrival, '#cbdbc0');
  const float = Math.sin(t * 1.21);
  product(ctx, 268, 512 + 45 * (1 - arrival) + 7 * float, .83 + .11 * arrival, -.20 + .12 * arrival + .042 * float);
  tag(ctx, 'РИСУНОК ПО ФОТО', 53, 689, 161);
  copy(ctx, 'НАЗНАЧЕНИЕ', ['Для остановки опасного', 'кровотечения из руки или ноги.']);
  footer(ctx, t, 'XMETIX TAK710 / ОБЗОР');
}
function design(ctx, t) {
  const strap = t >= DESIGN_CUT;
  const local = t - (strap ? DESIGN_CUT : CHAPTERS[1].start);
  base(ctx, 2, 'XMETIX / КОНСТРУКЦИЯ', '#283f42', true);
  headline(ctx, 'Экран и', 'ремень.', 75, 77, true);
  studio(ctx, 37, 251, 466, 482);
  const reframe = 1 - ease(local / .42);
  const flash = reframe * .11;
  ctx.save(); ctx.beginPath(); ctx.rect(50, 267, 440, 378); ctx.clip();
  const y = strap ? 497 : 462;
  const x = strap ? 19 : 270;
  ellipse(ctx, '#2f5556', 270, 435, 222, 192);
  product(ctx, x + Math.sin(local * 1.9) * 7 + 36 * reframe, y + Math.cos(local * 1.7) * 4,
    (strap ? 2.17 : 1.75) - .16 * reframe, -.023 + .013 * Math.sin(local), 1);
  fill(ctx, `rgba(245,222,169,${flash})`, 50, 267, 440, 378);
  ctx.restore();
  rounded(ctx, null, 50, 267, 440, 378, 1, '#a1bda4');
  tag(ctx, strap ? '02 / РЕМЕНЬ' : '01 / ЭКРАН', 62, 280, 127, '#233d3e');
  rounded(ctx, '#3e605a', 50, 653, 440, 64, 5, '#6f9385');
  text(ctx, strap ? 'Ремень и пряжка' : 'Экран и кнопка', 66, 695, 33, C.cream);
  copy(ctx, 'АВТОМАТИКА', ['Натяжение ремня регулируется', 'автоматически.'], true);
  footer(ctx, t, 'ЭКРАН ПОКАЗАН СХЕМАТИЧНО', true);
}
function context(ctx, t) {
  const road = t >= KIT_CUT;
  const local = t - (road ? KIT_CUT : CHAPTERS[2].start);
  base(ctx, 3, 'АПТЕЧКА / НАЗНАЧЕНИЕ');
  headline(ctx, 'Первая', 'помощь.', 78, 82);
  setArt(ctx, road ? 1 : 0, local, 37, 251, 466, 402);
  rounded(ctx, null, 37, 251, 466, 402, 0, '#829c88', 1.7);
  tag(ctx, road ? '02 / В ДОРОГЕ' : '01 / НА РАБОТЕ', 51, 266, 134);
  rounded(ctx, '#d9e0cb', 37, 653, 466, 79, 0, '#a5b39d');
  text(ctx, road ? 'Дорожная аптечка' : 'Аптечка на рабочем месте', 52, 696, road ? 34 : 31, C.ink);
  copy(ctx, 'КОГДА НУЖНА ПОМОЩЬ', ['При опасном кровотечении', 'из руки или ноги.']);
  footer(ctx, t, 'ПЕРВАЯ ПОМОЩЬ / ГРАЖДАНСКИЕ СЦЕНЫ');
}
function handset(ctx, x, y) {
  ctx.save(); ctx.translate(x, y); ctx.rotate(-.09);
  // Detached emergency-call pictogram, not a control on the device.
  path(ctx, [[-32, -34], [-43, -19], [-38, 2], [-27, 21], [-8, 39], [14, 47],
    [30, 35], [28, 24], [10, 13], [0, 22], [-13, 12], [-24, -4], [-23, -12], [-14, -20], [-22, -34]], '#3b4641');
  ctx.restore();
}
function emergency(ctx, t) {
  const local = t - CHAPTERS[3].start;
  base(ctx, 4, 'ЭКСТРЕННЫЕ СЛУЖБЫ / РОССИЯ', '#2f3f40', true);
  headline(ctx, 'Вызов', 'помощи.', 78, 80, true);
  rounded(ctx, '#eac179', 37, 251, 466, 482, 11, '#b9975e');
  const appear = ease(local / .41);
  ellipse(ctx, '#f5d594', 270, 367, 73, 70);
  ellipse(ctx, null, 270, 367, 84, 81, '#b58e57', 1.2);
  handset(ctx, 271, 360 + 12 * (1 - appear));
  ctx.save(); ctx.translate(0, 14 * (1 - appear));
  text(ctx, '112', 270, 604, 172, '#293c3b', { align: 'center', track: 4 });
  ctx.restore();
  line(ctx, 94, 631, 352, '#ba9862');
  text(ctx, 'ПРИ СИЛЬНОМ КРОВОТЕЧЕНИИ', 270, 674, 14, '#445249', { align: 'center', track: 1.6 });
  copy(ctx, 'ЭКСТРЕННЫЙ ВЫЗОВ', ['В России звоните 112.', 'Следуйте указаниям диспетчера.'], true);
  footer(ctx, t, '112 / ЭКСТРЕННАЯ ПОМОЩЬ', true);
}
export const QR_X = [104, 252, 400];
export const QR_Y = 626;
const qr = CONTACTS.map(({ href }) => QRCode.create(href, { errorCorrectionLevel: 'M' }).modules);
function contact(ctx, i) {
  const x = QR_X[i], m = qr[i];
  const step = Math.floor(106 / (m.size + 8));
  const side = step * (m.size + 8), left = Math.round(x - side / 2);
  rounded(ctx, '#294b49', x - 65, QR_Y - 10, 130, 155, 7, '#668881');
  fill(ctx, '#fffef1', left, QR_Y, side, side);
  for (let y = 0; y < m.size; y++) for (let x = 0; x < m.size; x++) {
    if (m.get(y, x)) fill(ctx, '#112e2a', left + (x + 4) * step, QR_Y + (y + 4) * step, step, step);
  }
  text(ctx, CONTACTS[i].label, QR_X[i], QR_Y + 122, 14, C.cream, { align: 'center' });
  text(ctx, CONTACTS[i].handle, QR_X[i], QR_Y + 139, 11, C.mint, { align: 'center', medium: true });
}
function final(ctx, t) {
  base(ctx, 5, 'В ОКОПЕ / КОНТАКТЫ', '#203d3d', true);
  const p = ease((t - CHAPTERS[4].start) / .47);
  rounded(ctx, '#284b49', 38, 103, 464, 266, 10, '#63867d');
  const src = [344, 202, 1016, 918], w = 261;
  ctx.drawImage(logo, ...src, (W - w) / 2, 118 + 8 * (1 - p), w, w * src[3] / src[2]);
  rising(ctx, 440, 142, 13 * p, C.amber);
  text(ctx, 'Первая помощь.', 37, 444, 53, C.cream);
  text(ctx, 'Обзор, не инструкция.', 38, 506, 34, C.amber);
  text(ctx, 'Изучите инструкцию производителя.', 39, 545, 21, C.mint, { medium: true });
  text(ctx, 'Пройдите обучение первой помощи.', 39, 573, 21, C.mint, { medium: true });
  line(ctx, 37, 597, 466, '#6d9283');
  CONTACTS.forEach((_, i) => contact(ctx, i));
  footer(ctx, t, 'МАГАЗИН / 03 КОНТАКТА', true);
}
function paperTile() {
  const canvas = createCanvas(123, 127), ctx = canvas.getContext('2d');
  const pixels = ctx.createImageData(canvas.width, canvas.height);
  let seed = 3026;
  for (let i = 0; i < pixels.data.length; i += 4) {
    seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0;
    const light = seed >>> 31;
    pixels.data[i] = light ? 242 : 27;
    pixels.data[i + 1] = light ? 237 : 33;
    pixels.data[i + 2] = light ? 208 : 33;
    pixels.data[i + 3] = (seed >>> 23) % 29;
  }
  ctx.putImageData(pixels, 0, 0);
  return canvas;
}
const scenes = [hero, design, context, emergency, final];
export function createFilm(scale = 2) {
  fonts();
  const canvas = createCanvas(W * scale, H * scale), ctx = canvas.getContext('2d');
  const pattern = ctx.createPattern(paperTile(), 'repeat');
  return {
    canvas, draw(time) {
      const t = Math.min(DURATION, Math.max(0, time));
      const i = chapterAt(t);
      ctx.setTransform(scale, 0, 0, scale, 0, 0);
      ctx.lineJoin = 'round'; ctx.lineCap = 'round';
      scenes[i](ctx, t);
      ctx.save(); ctx.globalAlpha *= .43; fill(ctx, pattern, 0, 0, W, H); ctx.restore();
      const local = t - CHAPTERS[i].start;
      if (i > 0 && local < WIPE) line(ctx, 37, 77, 466 * (1 - ease(local / WIPE)), C.amber, 2.5);
      return canvas;
    },
  };
}
