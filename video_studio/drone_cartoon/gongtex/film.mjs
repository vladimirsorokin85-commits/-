import { createCanvas, GlobalFonts, loadImage, Path2D } from '@napi-rs/canvas';
import { fileURLToPath } from 'node:url';
import { clamp, ease, ellipse, fill, line, path, rounded } from '../bulat/art.mjs';
import { BPM, DURATION, PHOTOS, SHOTS, SPECS, WIPE } from './story.mjs';

export const WIDTH = 540;
export const HEIGHT = 960;
const W = WIDTH, H = HEIGHT, L = 36, SPAN = 468;
const DARK = { top: '#385751', bot: '#192f36', ink: '#fbefd9', sub: '#c0d0b3', accent: '#f0c788', rule: '#b9ceb080', card: '#2c4a49' };
const LIGHT = { top: '#f2e8d0', bot: '#cdd0b6', ink: '#263d3c', sub: '#4e6b5c', accent: '#8b6141', rule: '#6c8a767e', card: '#faf0d8' };
const images = Object.fromEntries(await Promise.all(PHOTOS.map(async (name) => [
  name, await loadImage(fileURLToPath(new URL(`./assets/${name}.jpg`, import.meta.url))),
])));
const logo = await loadImage(fileURLToPath(new URL('../bulat/assets/v-okope-white.png', import.meta.url)));
const FRONT = [
  { title: 'Мультикам.', photo: 'camo-front', crop: [.11, .235, .78, .765] },
  { title: 'Койот.', photo: 'coyote-front', crop: [.125, .244, .75, .735] },
];
let registered = false;
function fonts() {
  if (registered) return;
  for (const face of ['Black', 'Medium']) {
    if (!GlobalFonts.registerFromPath(fileURLToPath(new URL(`../../fonts/Roboto-${face}.woff`, import.meta.url)), `Gongtex${face}`)) {
      throw new Error(`Шрифт не загружен: Roboto ${face}.`);
    }
  }
  registered = true;
}
function type(ctx, value, x, y, size, color, { track = 0, max = Infinity, align = 'left', medium = false } = {}) {
  const face = `Gongtex${medium ? 'Medium' : 'Black'}`;
  ctx.font = `${size}px ${face}`;
  const width = ctx.measureText(value).width;
  if (width + track * (value.length - 1) > max) ctx.font = `${size * (max - track * (value.length - 1)) / width}px ${face}`;
  ctx.textBaseline = 'alphabetic'; ctx.fillStyle = color;
  if (!track) { ctx.textAlign = align; ctx.fillText(value, x, y); return; }
  ctx.textAlign = 'left';
  const letters = [...value].map((ch) => [ch, ctx.measureText(ch).width + track]);
  const span = letters.reduce((sum, [, w]) => sum + w, -track);
  x -= align === 'right' ? span : align === 'center' ? span / 2 : 0;
  for (const [ch, w] of letters) { ctx.fillText(ch, x, y); x += w; }
}
function paper(ctx, pal, t) {
  const g = ctx.createLinearGradient(0, 0, W, H);
  g.addColorStop(0, pal.top); g.addColorStop(1, pal.bot);
  fill(ctx, g, 0, 0, W, H);
  const shade = pal === DARK ? '#87aa8f1d' : '#6f967521';
  path(ctx, [[0, 414], [W, 287], [W, 321], [0, 451]], shade);
  path(ctx, [[0, 753], [W, 640], [W, H], [0, H]], shade);
  for (let x = 14; x <= W; x += 24) for (let y = 16; y <= H; y += 26) fill(ctx, shade, x, y, 1.25, 1.25);
  ctx.save(); ctx.globalAlpha = .27;
  for (let i = -2; i < 10; i++) {
    const y = i * 125 - (t * 12 % 125);
    path(ctx, [[-5, y + 140], [W + 5, y]], null, pal.rule, 1.15);
  }
  ctx.restore();
}
function rails(ctx, p, label, chapter, t) {
  fill(ctx, p.accent, L, 49, 4.5, 19);
  type(ctx, label, 49, 64, 12.5, p.ink, { track: 1.4 });
  type(ctx, chapter, 504, 64, 12.5, p.sub, { track: 1.4, align: 'right' });
  line(ctx, L, 86, SPAN, p.rule);
  line(ctx, L, 897, SPAN, p.rule);
  line(ctx, L, 896, SPAN * t / DURATION, p.accent, 1.8);
  type(ctx, 'GONGTEX   /   REVERSIBLE JACKET', L, 924, 12, p.sub, { track: 1.25 });
  type(ctx, `00:${String(Math.floor(t)).padStart(2, '0')}`, 504, 924, 12, p.sub, { align: 'right', track: 1.1 });
}
function heading(ctx, pal, a, b, sizes = [75, 82]) {
  type(ctx, a, 32, 169, sizes[0], pal.ink, { max: 476 });
  type(ctx, b, 32, 249, sizes[1], pal.accent, { max: 476 });
}
function cropInto(ctx, name, x, y, w, h, [rx, ry, rw, rh]) {
  const image = images[name];
  let sx = rx * image.width, sy = ry * image.height, sw = rw * image.width, sh = rh * image.height;
  const aspect = w / h;
  if (sw / sh > aspect) { sx += (sw - sh * aspect) / 2; sw = sh * aspect; }
  else { sy += (sh - sw / aspect) / 2; sh = sw / aspect; }
  ctx.drawImage(image, sx, sy, sw, sh, x, y, w, h);
}
function photo(ctx, pal, name, crop, x, y, w, h, { label = 'ФОТО', tilt = 0 } = {}) {
  ctx.save(); ctx.translate(x + w / 2, y + h / 2); ctx.rotate(tilt);
  const l = -w / 2, top = -h / 2;
  rounded(ctx, '#182d3941', l - 5, top - 2, w + 16, h + 36, 5);
  rounded(ctx, pal === DARK ? '#e8e3cb' : '#f8efd9', l - 6, top - 6, w + 12, h + 33, 5);
  cropInto(ctx, name, l, top, w, h, crop);
  type(ctx, label, l + 3, top + h + 17.3, w > 250 ? 12.4 : 11, '#3e5d4e', { track: .95, max: w - 6 });
  ctx.restore();
}
function tag(ctx, pal, x, y, w, label, value) {
  rounded(ctx, pal.card, x, y, w, 113, 8, pal.rule, 1.35);
  type(ctx, value, x + 15, y + 63, 54, pal.ink);
  type(ctx, label, x + 16, y + 92, 14, pal.sub, { track: 1.18 });
}
function drop(ctx, x, y, rx, ry, seed) {
  ctx.beginPath();
  for (let i = 0; i <= 32; i++) {
    const a = i * Math.PI / 16, v = 1 + Math.sin(a * 3 + seed) * .16 + Math.cos(a * 5 - seed) * .13;
    const p = [x + Math.cos(a) * rx * v, y + Math.sin(a) * ry * v];
    if (i) ctx.lineTo(...p); else ctx.moveTo(...p);
  }
  ctx.closePath(); ctx.fill();
}
const marks = (() => {
  let seed = 1200;
  const next = () => ((seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0) / 2 ** 32);
  return Array.from({ length: 98 }, () => [-172 + next() * 344, -168 + next() * 322, 7 + next() * 26, 4 + next() * 15, next() * 10]);
})();
const hood = new Path2D('M -60 -70 C -65 -120 -35 -163 0 -166 C 39 -166 67 -123 62 -72 L 34 -57 L 0 -62 L -34 -56 Z');
const body = new Path2D('M -47 -91 C -76 -87 -109 -77 -131 -51 L -173 92 Q -177 112 -161 119 L -118 123 L -107 85 L -102 137 Q -71 149 0 147 Q 71 149 102 137 L 107 85 L 118 123 L 161 119 Q 177 112 173 92 L 131 -51 C 109 -77 76 -87 47 -91 Q 22 -70 -1 -68 Q -20 -72 -47 -91 Z');
function cloth(ctx, shape, camo, tone, outline) {
  ctx.fillStyle = tone; ctx.fill(shape);
  ctx.save(); ctx.clip(shape);
  if (camo) {
    const swatches = ['#a39067', '#646f52', '#d3bb87', '#4b5141', '#aeb28b', '#d8c493'];
    for (const [i, [x, y, rx, ry, seed]] of marks.entries()) {
      ctx.fillStyle = swatches[i % swatches.length]; drop(ctx, x, y, rx, ry, seed);
    }
  } else {
    for (let q = -160; q <= 170; q += 5) path(ctx, [[q, -180], [q - 39, 150]], null, '#e8ca8c44', .74);
  }
  ctx.restore(); ctx.strokeStyle = outline; ctx.lineWidth = 2.25; ctx.stroke(shape);
}
function jacket(ctx, x, y, size, camo, squash) {
  ctx.save(); ctx.translate(x, y); ctx.scale(size * squash, size);
  ellipse(ctx, '#153c365f', 0, 155, 146, 14);
  cloth(ctx, hood, camo, camo ? '#a78f67' : '#a77c4b', '#354e44');
  path(ctx, [[-36, -82], [-24, -136], [0, -148], [28, -135], [38, -81], [6, -68]], '#554d38', '#55614c', 2);
  cloth(ctx, body, camo, camo ? '#b0a274' : '#b58c57', '#35594e');
  path(ctx, [[-131, -50], [-106, -5], [-105, 84]], null, '#5c6349', 2.1);
  path(ctx, [[131, -50], [106, -5], [105, 84]], null, '#5c6349', 2.1);
  path(ctx, [[-42,-88],[-17,-68],[1,-66],[34,-82]], null, '#e2c993', 2.8);
  rounded(ctx, '#634f38', -3.6, -68, 7.2, 211, 2);
  line(ctx, -2.8, -62, 5.6, '#e7cf9d', 3);
  rounded(ctx, '#d4b47b', -6, -67, 12, 17, 2.5, '#5d654e');
  rounded(ctx, '#74583b', 27, -29, 5.5, 52, 2);
  path(ctx, [[-60, 51], [-80, 113]], null, '#71593c', 5.3);
  path(ctx, [[60, 51], [80, 113]], null, '#71593c', 5.3);
  path(ctx, [[-169,104],[-121,110]], null, '#d1bc88', 2.2);
  path(ctx, [[169,104],[121,110]], null, '#d1bc88', 2.2);
  ctx.restore();
}
function opener(ctx, t, abs) {
  const pal = DARK;
  paper(ctx, pal, abs); rails(ctx, pal, 'ДВУСТОРОННЯЯ КУРТКА', '01 / 05', abs);
  type(ctx, 'GONGTEX', 33, 188, 102, pal.ink, { max: 475 });
  type(ctx, 'Reversible Jacket', L, 256, 50, pal.accent, { max: 468 });
  const e = 1 - ease(t / .56), turn = t - 4 * 60 / BPM, camo = turn < 0;
  rounded(ctx, '#456b60', L, 300, SPAN, 435, 9, pal.rule);
  ellipse(ctx, camo ? '#dcc086' : '#a8c4a3', 345, 469, 91, 91);
  path(ctx, [[L, 647], [504, 546], [504, 727], [L, 727]], '#608374');
  jacket(ctx, 270, 530 + 18 * e, 1.13, camo, .085 + .915 * clamp(Math.abs(turn) / .21));
  type(ctx, 'РИСОВАННАЯ СЦЕНА', 50, 713, 11.8, pal.ink, { track: 1.25 });
  rounded(ctx, '#2d4e4c', L, 769, SPAN, 84, 8, pal.rule);
  type(ctx, 'МУЛЬТИКАМ  /  КОЙОТ', 270, 822, 31, pal.ink, { align: 'center', track: 1.2 });
}
function colour(ctx, t, abs, { side }) {
  const pal = side ? LIGHT : DARK, { title, photo: img, crop } = FRONT[side];
  paper(ctx, pal, abs); rails(ctx, pal, 'ДВЕ СТОРОНЫ', '01 / 05', abs);
  type(ctx, `Сторона 0${side + 1}`, L, 161, 46, pal.ink, { max: SPAN });
  type(ctx, title, 32, 251, 82, pal.accent, { max: 474 });
  const e = 1 - ease(t / .53);
  photo(ctx, pal, img, crop, 44 + (side ? 1 : -1) * e * 29, 292 + 9 * e, 452, 456, { label: 'ФОТО / ВИД СПЕРЕДИ', tilt: e * (side ? .040 : -.044) });
  type(ctx, 'GONGTEX Reversible Jacket', L, 837, 33, pal.ink, { max: SPAN });
}
function shell(ctx, t, abs) {
  const pal = LIGHT;
  paper(ctx, pal, abs); rails(ctx, pal, 'ТКАНЬ И УТЕПЛИТЕЛЬ', '02 / 05', abs);
  heading(ctx, pal, 'Верх', 'куртки.');
  photo(ctx, pal, 'coyote-detail', [.25,.22,.73,.65], 44, 296 + 9 * (1 - ease(t / .59)), 452, 280, { label: 'ФОТО ТКАНИ' });
  tag(ctx, pal, L, 635, 228, 'ПОЛИЭСТЕР', `${SPECS.polyester}%`);
  tag(ctx, pal, 276, 635, 228, 'СПАНДЕКС', `${SPECS.spandex}%`);
  type(ctx, `${SPECS.shell} г/м²`, L, 835, 43, pal.ink);
  type(ctx, 'ПЛОТНОСТЬ ВЕРХА', 241, 831, 16, pal.sub, { track: 1.25 });
}
function fibers(ctx, x, y, t) {
  const e = 1 - ease(t / .62);
  for (let i = 0; i < 3; i++) {
    const a = y + i * (66 - 25 * e);
    path(ctx, [[x-167,a],[x+79,a-61],[x+167,a-21],[x-70,a+43]], ['#b69660','#d8d5ad','#6f8b74'][i], '#c1c898', 2);
    path(ctx, [[x-167,a],[x-70,a+43],[x+167,a-21],[x+167,a-9],[x-70,a+55],[x-167,a+12]], ['#9c7c51','#bdbf9c','#547562'][i]);
    for (let j=0;j<7;j++) path(ctx, [[x-122+31*j,a-2-j*7],[x-75+32*j,a+17-j*7]], null, i === 1 ? '#a7ad8b' : '#d3bc8a7d', 1.5);
  }
}
function insulation(ctx, t, abs, config) {
  const pal = config.photo ? LIGHT : DARK;
  paper(ctx, pal, abs); rails(ctx, pal, 'ТКАНЬ И УТЕПЛИТЕЛЬ', '02 / 05', abs);
  heading(ctx, pal, 'Утеплитель', `${SPECS.insulationBrand}.`, [66, 88]);
  if (config.photo) photo(ctx, pal, 'coyote-back', [.16,.18,.71,.81], 45, 302, 450, 370, { label: 'КОЙОТ / ВИД СО СПИНЫ' });
  else {
    rounded(ctx, '#456b60', L, 300, SPAN, 381, 9, pal.rule);
    ellipse(ctx, '#86a488', 271, 490, 128, 127);
    fibers(ctx, 268, 430, t);
    type(ctx, 'СХЕМА СЛОЁВ', 50, 660, 12, pal.ink, { track: 1.35 });
  }
  type(ctx, `${SPECS.insulation} г/м²`, L, 792, 71, pal.ink, { max: SPAN });
  type(ctx, 'ПЛОТНОСТЬ УТЕПЛИТЕЛЯ', L + 3, 839, 15.5, pal.sub, { track: 1.25 });
}
function zip(ctx, t, abs) {
  const pal = DARK;
  paper(ctx, pal, abs); rails(ctx, pal, 'ДЕТАЛИ КУРТКИ', '03 / 05', abs);
  heading(ctx, pal, 'Молния', `${SPECS.zipper}.`);
  photo(ctx, pal, 'coyote-detail', [.12,0,.76,.85], 44, 293 + 9 * (1 - ease(t / .50)), 452, 451, { label: 'ФОТО / КРУПНЫЙ ПЛАН' });
  type(ctx, 'Центральная застёжка', L, 838, 37, pal.ink, { max: SPAN });
}
function details(ctx, t, abs) {
  const pal = LIGHT;
  paper(ctx, pal, abs); rails(ctx, pal, 'ДЕТАЛИ КУРТКИ', '03 / 05', abs);
  heading(ctx, pal, 'Воротник', 'и карман.', [72, 79]);
  const slide = 14 * (1 - ease(t / .55));
  photo(ctx, pal, 'camo-collar', [.075,.505,.67,.49], 43, 309 + slide, 214, 348, { label: 'ВОРОТ И КАПЮШОН', tilt: -.015 });
  photo(ctx, pal, 'camo-pocket', [.36,.24,.25,.71], 283, 309 + slide, 214, 348, { label: 'БОКОВОЙ КАРМАН', tilt: .012 });
  for (const [i, [a, b]] of [['Стойка', 'Липучка'], ['Боковой', 'На молнии']].entries()) {
    const x = L + i * 241;
    rounded(ctx, pal.card, x, 737, 227, 112, 7, pal.rule);
    type(ctx, a, x + 14, 785, 29, pal.ink);
    type(ctx, b, x + 15, 822, 23, pal.sub, { medium: true });
  }
}
function cuff(ctx, t, abs) {
  const pal = DARK;
  paper(ctx, pal, abs); rails(ctx, pal, 'РЕГУЛИРОВКА ПОСАДКИ', '04 / 05', abs);
  heading(ctx, pal, 'Эластичные', 'манжеты.', [67, 84]);
  photo(ctx, pal, 'camo-pocket', [.553,.53,.425,.456], 44, 296, 452, 437, { label: 'ФОТО / МАНЖЕТА', tilt: -.018 * (1 - ease(t / .60)) });
  type(ctx, 'Прилегают к запястьям.', L, 833, 36, pal.ink, { max: SPAN });
}
function hem(ctx, t, abs) {
  const pal = LIGHT;
  paper(ctx, pal, abs); rails(ctx, pal, 'РЕГУЛИРОВКА ПОСАДКИ', '04 / 05', abs);
  heading(ctx, pal, 'Утяжка', 'по низу.');
  photo(ctx, pal, 'coyote-side', [.18,.21,.57,.78], 44, 297, 263, 461, { label: 'ФОТО / ВИД СБОКУ' });
  const dy=13*(1-ease(t/.6));
  rounded(ctx, '#d3d7ba', 327, 436+dy, 177, 238, 8, pal.rule, 1.55);
  path(ctx, [[342,489+dy],[492,489+dy],[492,542+dy],[342,542+dy]], '#b99862', '#7d8f70', 1.4);
  path(ctx, [[351,527+dy],[475,527+dy],[486,563+dy],[463,578+dy],[454,549+dy],[460,527+dy]], null, '#486855', 4.7);
  rounded(ctx, '#567569', 452, 550+dy, 22, 12, 4, '#375e54');
  type(ctx, 'СХЕМА', 343, 648+dy, 13, pal.ink, { track: 1.4 });
  type(ctx, 'Эластичный шнурок по низу.', L, 835, 34, pal.ink, { max: SPAN });
}
function season(ctx, t, abs) {
  const pal = LIGHT;
  paper(ctx, pal, abs); rails(ctx, pal, 'GONGTEX REVERSIBLE', '05 / 05', abs);
  heading(ctx, pal, 'Демисезон', 'и зима.', [72, 86]);
  photo(ctx, pal, 'camo-side', [.208,.228,.53,.761], 43, 301, 214, 440, { label: 'МУЛЬТИКАМ', tilt: -.014 * (1 - ease(t / .62)) });
  photo(ctx, pal, 'coyote-back', [.166,.17,.691,.824], 283, 301, 214, 440, { label: 'КОЙОТ' });
  type(ctx, 'Две стороны одной куртки.', L, 838, 34, pal.ink, { max: SPAN });
}
function end(ctx, t, abs) {
  const pal = DARK;
  paper(ctx, pal, abs); rails(ctx, pal, 'ДВУСТОРОННЯЯ КУРТКА', '05 / 05', abs);
  type(ctx, 'GONGTEX', 32, 192, 103, pal.ink, { max: 474 });
  type(ctx, 'Reversible Jacket', L, 255, 49, pal.accent, { max: SPAN });
  rounded(ctx, '#2c4e4d', L, 300, SPAN, 379, 10, pal.rule);
  ellipse(ctx, '#50776a', W / 2, 486, 132, 132);
  // Trim transparent margins in the original lock-up, not the artwork.
  const h = 184, w = h * 1008 / 908;
  ctx.drawImage(logo, 347, 207, 1008, 908, (W - w) / 2, 394 + 17 * (1 - ease(t / .55)), w, h);
  type(ctx, 'Мультикам  /  Койот', L, 768, 44, pal.ink, { max: SPAN });
  type(ctx, SPECS.season, L, 824, 31, pal.sub, { medium: true });
}
function grain() {
  const canvas = createCanvas(133, 149), ctx = canvas.getContext('2d'), d = ctx.createImageData(133,149);
  let seed=701;
  for(let i=0;i<d.data.length;i+=4){
    seed=(Math.imul(seed,1664525)+1013904223)>>>0;
    const v=seed>>>31?236:28;
    d.data[i]=v; d.data[i+1]=v; d.data[i+2]=v-5; d.data[i+3]=(seed>>>24)%25;
  }
  ctx.putImageData(d,0,0); return canvas;
}
const scenes = { opener, colour, shell, insulation, zip, details, cuff, hem, season, end };
export function createFilm(scale = 2) {
  fonts();
  const canvas = createCanvas(W * scale,H * scale), ctx = canvas.getContext('2d');
  const texture=ctx.createPattern(grain(),'repeat');
  function drawCover() {
    const pal = DARK;
    ctx.setTransform(scale, 0, 0, scale, 0, 0);
    paper(ctx, pal, 0);
    fill(ctx, pal.accent, L, 67, 4.5, 21);
    type(ctx, 'МУЖСКАЯ ДВУСТОРОННЯЯ КУРТКА', 49, 83, 14, pal.ink, { track: 1.2 });
    line(ctx, L, 108, SPAN, pal.rule);
    type(ctx, 'GONGTEX', 32, 220, 103, pal.ink, { max: 474 });
    type(ctx, 'Reversible Jacket', L, 282, 50, pal.accent, { max: SPAN });
    // Crops centered on the same area of each jacket for the comparison.
    for (const [i, front] of FRONT.entries()) {
      photo(ctx, pal, front.photo, front.crop, 43 + i * 240, 333, 214, 439, {
        label: i ? '02  /  КОЙОТ' : '01  /  МУЛЬТИКАМ', tilt: i ? .012 : -.012,
      });
    }
    type(ctx, 'Демисезон и зима', L, 870, 36, pal.ink, { max: SPAN });
    line(ctx, L, 902, SPAN, pal.rule);
    type(ctx, 'В ОКОПЕ  /  ОБЗОР', L, 929, 12.5, pal.sub, { track: 1.3 });
    return canvas;
  }
  function draw(seconds) {
    const t = Math.min(DURATION,Math.max(0,seconds));
    const i=SHOTS.findLastIndex(({start})=>t>=start), shot=SHOTS[i], dt=t-shot.start;
    ctx.setTransform(scale,0,0,scale,0,0); ctx.lineJoin='round'; ctx.lineCap='round';
    scenes[shot.kind](ctx,dt,t,shot);
    ctx.save(); ctx.globalAlpha=.29; fill(ctx,texture,0,0,W,H); ctx.restore();
    if (i && dt<WIPE) {
      const x=-120+840*ease(dt/WIPE);
      path(ctx,[[x,0],[x+25,0],[x-81,H],[x-110,H]],'#f6d9a253');
    }
    return canvas;
  }
  return { canvas, draw, drawCover };
}
