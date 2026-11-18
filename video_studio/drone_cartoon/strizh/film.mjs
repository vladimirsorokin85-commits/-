import { createCanvas, GlobalFonts, loadImage } from '@napi-rs/canvas';
import { fileURLToPath } from 'node:url';
import { clamp, ease, ellipse, fill, line, path, rounded } from '../bulat/art.mjs';
import { DURATION, SHOTS, VIEWS, WIPE } from './story.mjs';

export const WIDTH = 540;
export const HEIGHT = 960;
const W = WIDTH, H = HEIGHT;
const LIGHT = { top: '#f5eace', bottom: '#c9ccb0', ink: '#203c3d', sub: '#4a6e62', accent: '#82663d', rule: '#547f7074' };
const DARK = { top: '#315955', bottom: '#192f36', ink: '#faefd6', sub: '#b9d5bd', accent: '#f1c981', rule: '#bad1ae70' };
const images = await Promise.all(VIEWS.map(({ id }) => loadImage(fileURLToPath(new URL(`./assets/view-${id}.jpg`, import.meta.url)))));
let fontReady = false;
function registerFonts() {
  if (fontReady) return;
  for (const face of ['Black', 'Medium']) {
    if (!GlobalFonts.registerFromPath(fileURLToPath(new URL(`../../fonts/Roboto-${face}.woff`, import.meta.url)), `Strizh${face}`)) {
      throw new Error(`Шрифт не загружен: ${face}`);
    }
  }
  fontReady = true;
}
function type(ctx, text, x, y, size, color, { align = 'left', medium = false, track = 0 } = {}) {
  ctx.font = `${size}px Strizh${medium ? 'Medium' : 'Black'}`;
  ctx.fillStyle = color;
  ctx.textBaseline = 'alphabetic';
  if (!track) { ctx.textAlign = align; ctx.fillText(text, x, y); return; }
  ctx.textAlign = 'left';
  const letters = [...text].map((ch) => [ch, ctx.measureText(ch).width + track]);
  const width = letters.reduce((sum, [, w]) => sum + w, -track);
  x -= align === 'right' ? width : align === 'center' ? width / 2 : 0;
  for (const [ch, w] of letters) { ctx.fillText(ch, x, y); x += w; }
}
function paper(ctx, palette, t) {
  const g = ctx.createLinearGradient(0, 0, W, H);
  g.addColorStop(0, palette.top); g.addColorStop(1, palette.bottom);
  fill(ctx, g, 0, 0, W, H);
  const light = palette === LIGHT;
  ctx.save(); ctx.globalAlpha = .22;
  for (let i = -2; i < 9; i++) {
    const y = 132 * i - (t * 7 % 132);
    path(ctx, [[-30, y + 128], [575, y]], null, palette.rule, 1.1);
  }
  ctx.restore();
  const edge = light ? '#69877b12' : '#add0b116';
  path(ctx, [[0, 713], [W, 611], [W, H], [0, H]], edge);
  for (let x = 16; x < W; x += 20) for (let y = 14; y < H; y += 24) fill(ctx, edge, x, y, 1.2, 1.2);
}
function rails(ctx, palette, left, right, t) {
  fill(ctx, palette.accent, 36, 48, 4, 21);
  type(ctx, left, 50, 64, 13, palette.ink, { track: 1.7 });
  type(ctx, right, 503, 64, 12, palette.sub, { align: 'right', track: 1.4 });
  line(ctx, 36, 85, 468, palette.rule);
  line(ctx, 36, 893, 468, palette.rule);
  line(ctx, 36, 893, 468 * t / DURATION, palette.accent, 2);
  const seconds = Math.floor(t);
  type(ctx, '«СТРИЖ»  /  ВИЗУАЛЬНЫЙ ОБЗОР', 36, 921, 12, palette.sub, { track: 1.35 });
  type(ctx, `${String(Math.floor(seconds / 60)).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')}`, 503, 921,
    12, palette.sub, { align: 'right', track: 1.25 });
}
function heading(ctx, palette, words, sizes = [76, 78]) {
  type(ctx, words[0], 33, 166, sizes[0], palette.ink);
  type(ctx, words[1], 33, 244, sizes[1], palette.accent);
}
function card(ctx, palette, { x, y, size, view, angle = 0, note = 'ФОТО' }) {
  const cream = palette === LIGHT ? '#f8eed8' : '#e8e3ca';
  ctx.save(); ctx.translate(x + size / 2, y + size / 2); ctx.rotate(angle);
  const left = -size / 2, top = -size / 2;
  rounded(ctx, '#142e3848', left - 7, top - 3, size + 20, size + 39, 5);
  rounded(ctx, cream, left - 8, top - 8, size + 16, size + 38, 4);
  ctx.drawImage(images[view], left, top, size, size);
  type(ctx, note, left + 2, top + size + 19, size > 370 ? 13 : 11, '#3a5a50', { track: .85 });
  ctx.restore();
}
// Flat paper-art silhouette. No annotations, internal parts or functional motion.
function silhouette(ctx, x, y, size, tilt, pale) {
  ctx.save(); ctx.translate(x, y); ctx.rotate(tilt); ctx.scale(size, size);
  const shade = pale ? '#7a8e71' : '#8da180';
  const edge = pale ? '#385d54' : '#c1ceb0';
  for (const flip of [-1, 1]) {
    ctx.save(); ctx.scale(flip, 1);
    path(ctx, [[19, -26], [112, -62], [121, -43], [46, 0], [23, 3]], shade, edge, 1.7);
    path(ctx, [[24, 24], [97, 73], [86, 88], [20, 62]], '#789476', edge, 1.7);
    path(ctx, [[86, -68], [96, -68], [137, -42], [132, -36], [119, -39]], '#375952');
    path(ctx, [[68, 67], [80, 65], [116, 91], [109, 97], [96, 95]], '#375952');
    ctx.restore();
  }
  path(ctx, [[-30, -83], [-13, -127], [6, -137], [26, -106], [36, -43], [32, 61], [13, 113], [-13, 114], [-33, 56]],
    '#a8b58e', edge, 1.8);
  path(ctx, [[6, -137], [26, -106], [36, -43], [32, 61], [13, 113], [11, 22], [12, -58]], '#738d73');
  path(ctx, [[-13, -127], [6, -137], [12, -58], [11, 22], [-13, 114], [-26, 15], [-21, -56]], '#c3c9a1');
  ctx.restore();
}
function art(ctx, palette, x, y, w, h, t, { tilt = -.23, small = false } = {}) {
  const pale = palette === LIGHT;
  rounded(ctx, pale ? '#d7d9bd' : '#3a645e', x, y, w, h, 6, palette.rule);
  ctx.save(); ctx.beginPath(); ctx.rect(x + 1, y + 1, w - 2, h - 2); ctx.clip();
  ellipse(ctx, pale ? '#e3c590' : '#c2a771', x + w * .77, y + h * .25, w * .14, w * .14);
  path(ctx, [[x, y + h * .83], [x + w, y + h * .59], [x + w, y + h], [x, y + h]], pale ? '#9eb49c' : '#547b6a');
  for (let i = 0; i < 4; i++) line(ctx, x + 15, y + h - 33 - i * 9, 27 + 11 * i, palette.rule, .9);
  const e = 1 - ease(t / .55);
  silhouette(ctx, x + w / 2 + 18 * e, y + h * .48, w * (small ? .0024 : .00275), tilt + .062 * e, pale);
  ctx.restore();
  type(ctx, 'РИСУНОК', x + w - 12, y + h - 14, small ? 11 : 13, palette.ink, { align: 'right', track: .85 });
}
function hero(ctx, t, abs, { view }) {
  const palette = view == null ? DARK : LIGHT;
  paper(ctx, palette, abs);
  rails(ctx, palette, 'ВНЕШНИЙ ВИД', 'ФОТО И ГРАФИКА', abs);
  type(ctx, '«Стриж»', 31, 206, 111, palette.ink);
  type(ctx, 'ДРОН-ПЕРЕХВАТЧИК', 39, 255, 19, palette.accent, { track: 2.1 });
  if (view == null) art(ctx, palette, 37, 299, 466, 454, t);
  else card(ctx, palette, { x: 55, y: 307 + 8 * (1 - ease(t / .56)), size: 430, view, note: 'ФОТО ВЛАДЕЛЬЦА' });
  type(ctx, 'Три ракурса одного аппарата.', 37, 838, 26, palette.ink, { medium: true });
}
function angle(ctx, t, abs, { view }) {
  const palette = view === 1 ? DARK : LIGHT;
  paper(ctx, palette, abs);
  rails(ctx, palette, 'ОБЩИЙ ВИД', `0${view + 1} / 03`, abs);
  heading(ctx, palette, VIEWS[view].title, view === 2 ? [82, 77] : undefined);
  const e = 1 - ease(t / .74), zoom = 8 * clamp(t / 5);
  card(ctx, palette, { x: 50 - zoom / 2 + (view === 1 ? 1 : -1) * 15 * e, y: 297 - zoom / 2 + 12 * e, size: 440 + zoom, view,
    angle: (view === 2 ? .022 : -.018) * e, note: 'ФОТО ВЛАДЕЛЬЦА / ОБЩИЙ ПЛАН' });
  type(ctx, VIEWS[view].note, 38, 835, 25, palette.ink, { medium: true });
}
function folio(ctx, t, abs, { view }) {
  const palette = view === 0 ? DARK : LIGHT;
  paper(ctx, palette, abs);
  rails(ctx, palette, 'ФОТО / РАКУРС', `0${view + 1} / 03`, abs);
  heading(ctx, palette, view === 0 ? ['Форма', 'и цвет.'] : ['Свет', 'и форма.']);
  card(ctx, palette, { x: 88, y: 291, size: 363, view, angle: (view === 0 ? -.053 : .044) + .055 * (1 - ease(t / .75)) });
  line(ctx, 37, 716, 466, palette.rule);
  const tones = view === 0 ? ['#958e5e', '#717557', '#414943'] : ['#beb996', '#969475', '#637466'];
  for (const [i, color] of tones.entries()) rounded(ctx, color, 37 + 57 * i, 740, 44, 42, 4, palette.rule);
  type(ctx, 'ТОНА НА СНИМКЕ', 220, 768, 14, palette.sub, { track: 1.35 });
  type(ctx, view === 0 ? 'Оливковый оттенок корпуса.' : 'Оттенки меняются при другом свете.', 37, 840, 25, palette.ink, { medium: true });
}
function print(ctx, t, abs) {
  const palette = LIGHT;
  paper(ctx, palette, abs);
  rails(ctx, palette, 'ИЛЛЮСТРАЦИЯ', 'ПЛОСКИЙ КОНТУР', abs);
  heading(ctx, palette, ['Общий', 'силуэт.']);
  art(ctx, palette, 37, 299, 466, 455, t, { tilt: .06 });
  type(ctx, 'Форма без мелких деталей.', 37, 839, 25, palette.ink, { medium: true });
}
function gallery(ctx, t, abs) {
  const palette = DARK;
  paper(ctx, palette, abs);
  rails(ctx, palette, 'ФОТО / СРАВНЕНИЕ', 'АРХИВ', abs);
  heading(ctx, palette, ['Три', 'ракурса.']);
  const layouts = [[46, 294, 204], [289, 294, 204], [164, 568, 212]];
  for (const [view, [x, y, size]] of layouts.entries()) card(ctx, palette, {
    x, y: y + 22 * (1 - ease((t - view * .12) / .5)), size, view, note: `ФОТО 0${view + 1}`,
  });
  type(ctx, 'Общий вид на трёх фотографиях.', 36, 849, 24, palette.ink, { medium: true });
}
function diptych(ctx, t, abs, { left }) {
  const palette = left === 2 ? DARK : LIGHT;
  paper(ctx, palette, abs);
  rails(ctx, palette, 'ФОТО И ИЛЛЮСТРАЦИЯ', 'ДВА ПЛАНА', abs);
  heading(ctx, palette, ['Фото', 'и рисунок.'], [78, 73]);
  card(ctx, palette, { x: 61, y: 307 + 6 * (1 - ease(t / .45)), size: 227, view: left, angle: -.06 });
  art(ctx, palette, 231, 481, 259, 274, t, { tilt: left === 2 ? -.34 : .23, small: true });
  type(ctx, 'Один аппарат — на фото и в рисунке.', 37, 837, 25, palette.ink, { medium: true });
}
function end(ctx, t, abs) {
  const palette = DARK;
  paper(ctx, palette, abs);
  rails(ctx, palette, 'ВИЗУАЛЬНЫЙ ОБЗОР', 'ТРИ ФОТО', abs);
  type(ctx, '«Стриж»', 31, 204, 111, palette.ink);
  type(ctx, 'ВНЕШНИЙ ВИД', 39, 250, 18, palette.accent, { track: 2.15 });
  const d = 136;
  for (let view = 0; view < VIEWS.length; view++) card(ctx, palette, {
    x: 43 + 158.5 * view, y: 436 - 65 * (view % 2) + 16 * (1 - ease((t - view * .13) / .55)),
    size: d, view, angle: (view - 1) * .06, note: `ФОТО 0${view + 1}`,
  });
  line(ctx, 36, 669, 468, palette.rule);
  type(ctx, 'Три ракурса.', 36, 750, 52, palette.ink);
  type(ctx, 'Фото владельца и рисованные перебивки.', 36, 807, 23, palette.sub, { medium: true });
}
function grain() {
  const canvas = createCanvas(139, 157), ctx = canvas.getContext('2d'), pixels = ctx.createImageData(139, 157);
  let seed = 926;
  for (let i = 0; i < pixels.data.length; i += 4) {
    seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0;
    const value = seed >>> 31 ? 236 : 31;
    pixels.data[i] = value; pixels.data[i + 1] = value; pixels.data[i + 2] = value - 5;
    pixels.data[i + 3] = (seed >>> 24) % 23;
  }
  ctx.putImageData(pixels, 0, 0);
  return canvas;
}
const frames = { hero, angle, folio, print, gallery, diptych, end };
export function createFilm(scale = 2) {
  registerFonts();
  const canvas = createCanvas(W * scale, H * scale), ctx = canvas.getContext('2d');
  const texture = ctx.createPattern(grain(), 'repeat');
  function draw(seconds) {
    const t = Math.min(DURATION, Math.max(0, seconds));
    const i = SHOTS.findLastIndex(({ start }) => t >= start), shot = SHOTS[i];
    const dt = t - shot.start;
    ctx.setTransform(scale, 0, 0, scale, 0, 0); ctx.lineCap = 'round'; ctx.lineJoin = 'round';
    frames[shot.kind](ctx, dt, t, shot);
    ctx.save(); ctx.globalAlpha = .27; fill(ctx, texture, 0, 0, W, H); ctx.restore();
    if (i && dt < WIPE) {
      const x = -96 + 784 * ease(dt / WIPE);
      path(ctx, [[x, 0], [x + 26, 0], [x - 89, H], [x - 119, H]], '#f4d69e52');
    }
    return canvas;
  }
  return { canvas, draw };
}
