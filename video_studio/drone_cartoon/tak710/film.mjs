import { createCanvas, GlobalFonts, loadImage } from '@napi-rs/canvas';
import { fileURLToPath } from 'node:url';
import QRCode from 'qrcode';
import { ease, ellipse, fill, line, path, rounded } from '../bulat/art.mjs';
import { C, medKit, product, text } from './art.mjs';
import { place } from './locations.mjs';
import { CONTACTS, CUTS, DURATION, EXAMPLES, OUTRO, WIPE } from './story.mjs';

export const WIDTH = 540;
export const HEIGHT = 960;
const W = WIDTH, H = HEIGHT;
const logo = await loadImage(fileURLToPath(new URL('../bulat/assets/v-okope-white.png', import.meta.url)));
const spring = (t, d = .34) => 1 - ease(t / d);
const light = '#f6d188', white = '#fff4d8', ink = '#152b32';
let prepared = false;
function fonts() {
  if (prepared) return;
  for (const face of ['Black', 'Medium']) {
    const file = fileURLToPath(new URL(`../../fonts/Roboto-${face}.woff`, import.meta.url));
    if (!GlobalFonts.registerFromPath(file, `Tak${face}`)) throw new Error(`Шрифт не загружен: ${face}`);
  }
  prepared = true;
}
function field(ctx, a, b, t, stroke = '#aec9b823') {
  const grad = ctx.createLinearGradient(0, 62, W, H);
  grad.addColorStop(0, a); grad.addColorStop(1, b);
  fill(ctx, grad, 0, 0, W, H);
  for (let i = -1; i < 7; i++) {
    const y = 164 * i - (t * 17 % 164);
    path(ctx, [[0, y + 151], [W, y]], null, stroke, 1.5);
    path(ctx, [[0, y + 160], [W, y + 9]], null, '#0e26251a', 1);
  }
  for (let x = 24; x < W; x += 30) for (let y = 104; y < 844; y += 30) fill(ctx, stroke, x, y, 1, 1);
}
function mark(ctx, label, camera, dark = true) {
  const color = dark ? white : ink;
  fill(ctx, dark ? light : '#937546', 36, 67, 4, 18);
  text(ctx, label, 50, 81, 13, color, { track: 1.8 });
  text(ctx, camera, 501, 81, 12, color, { align: 'right', track: 1.5 });
  line(ctx, 37, 101, 465, dark ? '#d9e6c657' : '#465e5b65');
}
function progress(ctx, t, label, dark = true) {
  const color = dark ? '#d5e2c0' : '#49635e';
  line(ctx, 36, 894, 467, dark ? '#a9c9b64e' : '#42686455', 1.2);
  line(ctx, 36, 894, 467 * t / DURATION, color, 1.7);
  text(ctx, label, 36, 920, 11.5, color, { track: 1.45 });
}
function lens(ctx, x, y, rx, ry, color, t) {
  ellipse(ctx, color, x, y, rx, ry);
  ellipse(ctx, null, x, y, rx + 14, ry + 16, '#cee6c38a', 1.1);
  ctx.save(); ctx.translate(x, y); ctx.rotate(-.35 + .28 * Math.sin(t * .95));
  ellipse(ctx, null, 0, 0, rx + 42, ry + 23, '#d8e5b36f', 1.25);
  ctx.restore();
}
function sparks(ctx, x, y, size, color) {
  path(ctx, [[x, y - size], [x + 2.7, y - 2.2], [x + size * .65, y], [x + 2.7, y + 2.5],
    [x, y + size], [x - 2.7, y + 2.5], [x - size * .65, y], [x - 2.7, y - 2.3]], color);
}
function name(ctx, y, dark) {
  text(ctx, 'XMETIX', 34, y, 84, dark ? white : ink);
  rounded(ctx, dark ? light : ink, 350, y - 53, 154, 55, 7);
  text(ctx, 'TAK710', 426, y - 16, 28, dark ? ink : light, { align: 'center', track: 1.15 });
}
function hero(ctx, local, t, take) {
  const paper = take === 1;
  const e = spring(local, .42);
  field(ctx, paper ? '#eee5cd' : '#234b52', paper ? '#b9c7a8' : '#16313c', local, paper ? '#426a5c27' : undefined);
  if (!paper) path(ctx, [[0, 645], [540, 322], [540, 489], [0, 812]], '#75a49747');
  lens(ctx, 268 + 13 * e, 475, take === 2 ? 168 : 206, take === 2 ? 183 : 190,
    paper ? '#9cbba5' : '#487e79', local);
  ellipse(ctx, paper ? '#314a4251' : '#0f232864', 265, 667, 152, 22);
  const a = [-.24, .055, .22][take] + .17 * e + .041 * Math.sin(local * 1.7);
  const k = [1.08, 1.16, 1.32][take] + .064 * (1 - e);
  product(ctx, 269 + [29, -33, -57][take] * e, 491 + [74, -14, 18][take] * e - 7 * Math.sin(local * 1.48), k, a);
  sparks(ctx, 450, 330, 15 + 3 * Math.sin(t * 4.4), paper ? '#fbefc2' : light);
  sparks(ctx, 85, 602, 9, '#bdd5b7');
  mark(ctx, 'ПЕРВАЯ ПОМОЩЬ', 'ОБЗОР', !paper);
  name(ctx, 212, !paper);
  line(ctx, 36, 726, 465, paper ? '#5e7d6c' : '#a8c5ae', 1.3);
  text(ctx, 'Автоматический', 35, 774, 41, paper ? ink : white);
  text(ctx, 'жгут', 36, 819, 43, paper ? '#4a6f61' : light);
  progress(ctx, t, 'РИСУНОК ПО ФОТО', !paper);
}

const details = [
  { focus: [-7, 64], center: [269, 453], scale: 2.38, angle: -.10, tone: ['#548a80', '#244653'], words: ['Одна кнопка'], caption: 'КОРПУС И ЭКРАН', ring: 84 },
  { focus: [100, 81], center: [329, 447], scale: 2.8, angle: -.12, tone: ['#b37c64', '#513735'], words: ['Защитная чека'], caption: 'КРАСНАЯ БОКОВАЯ ДЕТАЛЬ', ring: 49 },
  { focus: [122, -9], center: [295, 450], scale: 2.47, angle: .16, tone: ['#92ab87', '#535f53'], words: ['Ремень'], caption: 'ЛЕНТА И ПРЯЖКА', ring: 87 },
];
function macro(ctx, local, t, take) {
  const d = details[take], e = spring(local, .30);
  field(ctx, ...d.tone, local);
  const [x, y] = d.center;
  const angle = d.angle + .024 * Math.sin(local * 2.5) - .048 * e;
  const k = d.scale - .16 * e;
  const [fx, fy] = d.focus;
  const cx = x - 22 * e, cy = y + 8 * Math.sin(local * 1.5);
  const ox = cx - k * (fx * Math.cos(angle) - fy * Math.sin(angle));
  const oy = cy - k * (fx * Math.sin(angle) + fy * Math.cos(angle));
  product(ctx, ox, oy, k, angle, 1);
  // Invariant outline around a stationary feature: no hand, press or motion of the part.
  const rx = d.ring + 7 * e, ry = take === 1 ? 140 + 8 * e : rx;
  ellipse(ctx, null, cx, cy, rx, ry, '#fff0bdba', 2.0);
  const shade = ctx.createLinearGradient(0, 596, 0, H);
  shade.addColorStop(0, '#18292d00'); shade.addColorStop(.45, '#192c31dd'); shade.addColorStop(1, '#142a31');
  fill(ctx, shade, 0, 590, W, H - 590);
  rounded(ctx, '#183036aa', 18, 50, 504, 69, 12);
  mark(ctx, 'КРУПНЫЙ ПЛАН', 'TAK710');
  text(ctx, d.caption, 36, 716, 14, light, { track: 1.75 });
  text(ctx, d.words[0], 32, 784, take === 1 ? 58 : 72, white);
  progress(ctx, t, 'ДЕТАЛИ УСТРОЙСТВА');
}
function orbit(ctx, x, y, t) {
  const c = ['#8db8a65c', '#d3cd945f', '#7faca57f'];
  for (let i = 0; i < 3; i++) {
    const beat = (t * 54 + i * 93) % 280, a = -.65 + i * .57;
    const ax = 158 + beat * .26;
    const ay = 115 + beat * .285;
    ctx.save(); ctx.translate(x, y); ctx.rotate(a);
    ellipse(ctx, null, 0, 0, ax, ay, c[i], 1.9);
    const dot = t * (1.3 + i * .22) + i * 2.1;
    ellipse(ctx, i % 2 ? '#cdd9ae' : '#dbbe7b', ax * Math.cos(dot), ay * Math.sin(dot), 3.8, 3.8);
    ctx.restore();
  }
}
function automatic(ctx, local, t, take) {
  const e = spring(local);
  const pale = !!take;
  field(ctx, pale ? '#d1cfab' : '#2a5260', pale ? '#83aa92' : '#1d3840', local,
    pale ? '#3a655b30' : undefined);
  path(ctx, [[0, 428], [540, 248], [540, 441], [0, 625]], pale ? '#e1d8af80' : '#83b9ae46');
  lens(ctx, 272, 450, 184, 158, pale ? '#b9c9a1' : '#4a7d78', local);
  orbit(ctx, 272, 451, t);
  product(ctx, 270 + (pale ? 43 : -32) * e, 464 + 26 * e, (pale ? 1.13 : 1.04) + .08 * (1 - e),
    (pale ? .17 : -.13) - .11 * e + .05 * Math.sin(local * 1.8), 1);
  mark(ctx, 'КОНСТРУКЦИЯ', 'TAK710', !pale);
  text(ctx, 'НАТЯЖЕНИЕ РЕМНЯ', 36, 672, 17, pale ? '#456a5b' : light, { track: 1.85 });
  text(ctx, 'Автоматически.', 34, 751, 56, pale ? ink : white);
  progress(ctx, t, 'НАТЯЖЕНИЕ РЕГУЛИРУЕТ АВТОМАТИКА', !pale);
}
function purpose(ctx, local, t, take) {
  const e = spring(local), pale = take === 0;
  field(ctx, pale ? '#ddd0ad' : '#667f6b', pale ? '#9db29c' : '#304f50', local, pale ? '#49685e42' : undefined);
  path(ctx, [[0, 611], [540, 398], [540, 493], [0, 713]], pale ? '#f7e7b76c' : '#adc4a63d');
  mark(ctx, 'НАЗНАЧЕНИЕ ЖГУТА', 'ПЕРВАЯ ПОМОЩЬ', !pale);
  medKit(ctx, (pale ? 347 : 148) + (pale ? 19 : -30) * e, (pale ? 475 : 427) - 18 * Math.sin(local * 1.5), pale ? 1.22 : 1.36);
  product(ctx, (pale ? 184 : 346) - 37 * e, 478 + 40 * e, pale ? .76 : 1.16,
    (pale ? -.17 : .23) - .24 * e + .05 * Math.sin(local * 2));
  const slug = pale ? '#e5dec0' : '#213b41';
  rounded(ctx, slug, 37, 665, 465, 117, 7, pale ? '#738c75' : '#8aaf99');
  const color = pale ? ink : white;
  text(ctx, 'При опасном кровотечении', 55, 708, 30, color);
  text(ctx, 'из руки или ноги.', 55, 748, 30, color);
  progress(ctx, t, 'ПЕРВАЯ ПОМОЩЬ', !pale);
}
function sceneShade(ctx, y0, y1) {
  const grad = ctx.createLinearGradient(0, y0, 0, y1);
  grad.addColorStop(0, '#102a3100'); grad.addColorStop(1, '#13282ff0');
  fill(ctx, grad, 0, y0, W, H - y0);
}
function example(ctx, local, t, i) {
  place(ctx, i, local);
  sceneShade(ctx, 594, 901);
  rounded(ctx, '#18343dd9', 19, 50, 503, 69, 12);
  mark(ctx, 'ГДЕ МОЖЕТ ПОНАДОБИТЬСЯ', 'ПРИМЕР');
  const e = spring(local, .22);
  rounded(ctx, light, 39, 759, 8, 63, 2);
  text(ctx, EXAMPLES[i].context, 62, 750, 14, light, { track: 1.85 });
  text(ctx, EXAMPLES[i].label, 57 + 26 * e, 818, 66, white);
  progress(ctx, t, 'ПЕРВАЯ ПОМОЩЬ / ТРИ СИТУАЦИИ');
}
function recap(ctx, local, t) {
  field(ctx, '#305058', '#172f39', local);
  mark(ctx, 'ПЕРВАЯ ПОМОЩЬ', 'ТРИ СИТУАЦИИ');
  for (let i = 0; i < EXAMPLES.length; i++) {
    const e = spring(Math.max(0, local - .07 * i), .27);
    const x = 36 + (i % 2 ? 1 : -1) * 35 * e, y = 186 + i * 204;
    place(ctx, i, .56 + local * .39, { x, y, w: 467, h: 168 });
    const titleShade = ctx.createLinearGradient(x, y, x + 320, y);
    titleShade.addColorStop(0, '#19333ae8'); titleShade.addColorStop(1, '#19333a00');
    fill(ctx, titleShade, x, y, 467, 168);
    rounded(ctx, null, x, y, 467, 168, 2, '#c2d0b5', 1.2);
    fill(ctx, light, x + 17, y + 48, 3, 75);
    text(ctx, EXAMPLES[i].label, x + 29, y + 103, 43, white);
  }
  progress(ctx, t, 'ПОДГОТОВЬТЕСЬ ЗАРАНЕЕ');
}

export const QR_X = [104, 252, 400];
export const QR_Y = 626;
const qr = CONTACTS.map(({ href }) => QRCode.create(href, { errorCorrectionLevel: 'M' }).modules);
function contact(ctx, i) {
  const x = QR_X[i], m = qr[i];
  const step = Math.floor(106 / (m.size + 8));
  const side = step * (m.size + 8), left = Math.round(x - side / 2);
  rounded(ctx, '#263f48', x - 65, QR_Y - 10, 130, 155, 7, '#5f817b');
  fill(ctx, '#fffef1', left, QR_Y, side, side);
  for (let y = 0; y < m.size; y++) for (let x = 0; x < m.size; x++) {
    if (m.get(y, x)) fill(ctx, '#112e2a', left + (x + 4) * step, QR_Y + (y + 4) * step, step, step);
  }
  text(ctx, CONTACTS[i].label, x, QR_Y + 122, 15, white, { align: 'center' });
  text(ctx, CONTACTS[i].handle, x, QR_Y + 139, 11.5, C.mint, { align: 'center', medium: true });
}
function final(ctx, local, t) {
  field(ctx, '#29434b', '#152b33', local, '#a4bba52a');
  const e = spring(local, .45);
  mark(ctx, 'МАГАЗИН «В ОКОПЕ»', 'КОНТАКТЫ');
  rounded(ctx, '#2c474f', 37, 137, 465, 245, 9, '#71908b');
  const src = [344, 202, 1016, 918], w = 240;
  ctx.drawImage(logo, ...src, (W - w) / 2 + 16 * e, 150 + 9 * e, w, w * src[3] / src[2]);
  sparks(ctx, 429, 192, 12 + 6 * e, light);
  text(ctx, 'XMETIX TAK710', 36, 460, 51, white);
  line(ctx, 37, 482, 466, '#779d90');
  text(ctx, 'Изучите инструкцию производителя', 37, 526, 23, light, { medium: true });
  text(ctx, 'и пройдите обучение первой помощи.', 37, 559, 23, C.mint, { medium: true });
  CONTACTS.forEach((_, i) => contact(ctx, i));
  progress(ctx, t, 'ОБЗОР, НЕ ИНСТРУКЦИЯ');
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

const takes = [
  [hero, 0], [hero, 1], [hero, 2], [macro, 0], [macro, 1], [macro, 2],
  [automatic, 0], [automatic, 1], [purpose, 0], [purpose, 1],
  [example, 0], [example, 1], [example, 2], [recap], [final],
];
export function createFilm(scale = 2) {
  fonts();
  const canvas = createCanvas(W * scale, H * scale), ctx = canvas.getContext('2d');
  const pattern = ctx.createPattern(paperTile(), 'repeat');
  return {
    canvas, draw(time) {
      const t = Math.min(DURATION, Math.max(0, time));
      const i = CUTS.findLastIndex((start) => t >= start);
      const local = t - CUTS[i];
      ctx.setTransform(scale, 0, 0, scale, 0, 0);
      ctx.lineJoin = 'round'; ctx.lineCap = 'round';
      const [scene, take] = takes[i];
      scene(ctx, local, t, take);
      ctx.save(); ctx.globalAlpha *= .44; fill(ctx, pattern, 0, 0, W, H); ctx.restore();
      // A narrow diagonal tear that follows the cut; no flashing apparatus or status cue.
      if (i && t < OUTRO && local < WIPE) {
        const x = -201 + 1024 * ease(local / WIPE);
        path(ctx, [[x, 0], [x + 27, 0], [x - 126, H], [x - 157, H]], '#f3cf872b');
      }
      return canvas;
    },
  };
}
