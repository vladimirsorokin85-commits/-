import { createCanvas, GlobalFonts, loadImage } from '@napi-rs/canvas';
import { fileURLToPath } from 'node:url';
import { clamp, ease, ellipse, fill, line, path, rounded } from '../bulat/art.mjs';
import { badge, BPM, BRANDS, DURATION, SHOTS, STATIONS, WIPE } from './story.mjs';

export const WIDTH = 540;
export const HEIGHT = 960;
const W = WIDTH, H = HEIGHT, LEFT = 36, SPAN = W - 2 * LEFT;
const LIGHT = { top: '#f6e9ce', bottom: '#c8ceb2', ink: '#1d3b3c', sub: '#4c6e62', line: '#6c938277', tile: '#fbefd8', well: '#c1cab2' };
const DARK = { top: '#345b56', bottom: '#182f38', ink: '#fff0d2', sub: '#bdd6bc', line: '#bad3b478', tile: '#25494b', well: '#37625b' };
const ACCENTS = { amber: '#f0be78', blue: '#98d1d4', leaf: '#bbd58e' };
const CASES = [
  ['#455651', '#6d7e65', '#f0ba71'], ['#486c72', '#77969b', '#83beca'],
  ['#4c665b', '#79917d', '#bad489'], ['#546c71', '#819e9c', '#9bd0d0'],
  ['#425b65', '#668789', '#96c9d2'], ['#4f6158', '#7d8e76', '#edb770'],
  ['#4e6b55', '#789276', '#b4cc83'],
];
const STYLES = [
  { w: 204, h: 116, handle: .77, stripe: true }, { w: 195, h: 123, handle: .84, stripe: false },
  { w: 228, h: 98, handle: .57, stripe: false }, { w: 220, h: 104, handle: .74, stripe: true },
  { w: 220, h: 123, handle: .82, stripe: true }, { w: 209, h: 130, handle: .58, stripe: true },
  { w: 224, h: 120, handle: .7, stripe: false },
];
const logo = await loadImage(fileURLToPath(new URL('../bulat/assets/v-okope-white.png', import.meta.url)));
let registered = false;
function prepareFonts() {
  if (registered) return;
  for (const face of ['Black', 'Medium']) {
    if (!GlobalFonts.registerFromPath(fileURLToPath(new URL(`../../fonts/Roboto-${face}.woff`, import.meta.url)), `Power${face}`)) {
      throw new Error(`Не удалось зарегистрировать шрифт Roboto ${face}.`);
    }
  }
  registered = true;
}
function text(ctx, value, x, y, size, color, { medium = false, align = 'left', track = 0, max = Infinity } = {}) {
  const face = `Power${medium ? 'Medium' : 'Black'}`;
  ctx.font = `${size}px ${face}`;
  const measure = (value) => ctx.measureText(value).width;
  const natural = measure(value) + Math.max(0, value.length - 1) * track;
  if (natural > max) ctx.font = `${size * max / natural}px ${face}`;
  ctx.textBaseline = 'alphabetic'; ctx.fillStyle = color;
  if (!track) { ctx.textAlign = align; ctx.fillText(value, x, y); return; }
  ctx.textAlign = 'left';
  const letters = [...value].map((ch) => [ch, measure(ch) + track]);
  const width = letters.reduce((sum, [, w]) => sum + w, -track);
  x -= align === 'right' ? width : align === 'center' ? width / 2 : 0;
  for (const [ch, w] of letters) { ctx.fillText(ch, x, y); x += w; }
}
function surface(ctx, palette, t, accent) {
  const g = ctx.createLinearGradient(0, 0, W, H);
  g.addColorStop(0, palette.top); g.addColorStop(1, palette.bottom);
  fill(ctx, g, 0, 0, W, H);
  const light = palette === LIGHT;
  path(ctx, [[0, 444], [W, 324], [W, 344], [0, 469]], light ? '#64897727' : '#92bfaa22');
  path(ctx, [[0, 770], [W, 662], [W, H], [0, H]], light ? '#9ab09734' : '#45777034');
  ctx.save(); ctx.globalAlpha = .31;
  for (let i = -2; i < 10; i++) {
    const y = i * 119 - (t * 17 % 119);
    path(ctx, [[0, y + 122], [W, y]], null, palette.line, 1.15);
  }
  ctx.restore();
  for (let x = 15; x < W; x += 21) for (let y = 17; y < H; y += 28) fill(ctx, palette.line, x, y, .88, .88);
  fill(ctx, accent, 36, 49, 4.5, 18);
}
function metadata(ctx, palette, left, right, time, accent) {
  text(ctx, left, 49, 64, 12, palette.ink, { track: 1.35 });
  text(ctx, right, 503, 64, 12, palette.sub, { track: 1.2, align: 'right' });
  line(ctx, LEFT, 86, SPAN, palette.line);
  line(ctx, LEFT, 893, SPAN, palette.line);
  line(ctx, LEFT, 892.5, SPAN * time / DURATION, palette === LIGHT ? palette.sub : accent, 2);
  text(ctx, 'КАТАЛОГ  /  В ОКОПЕ', LEFT, 921, 11.5, palette.sub, { track: 1.4 });
  const n = Math.floor(time);
  text(ctx, `${String(Math.floor(n / 60)).padStart(2, '0')}:${String(n % 60).padStart(2, '0')}`, 503, 921, 12, palette.sub,
    { align: 'right', track: 1.2 });
}
function glint(ctx, x, y, size, color) {
  path(ctx, [[x, y - size], [x + 2.6, y - 2.1], [x + size * .82, y], [x + 2.6, y + 2.1], [x, y + size],
    [x - 2.6, y + 2.1], [x - size * .82, y], [x - 2.6, y - 2.1]], color);
}
// A stylized family of fictional cases. These silhouettes are not product photos
// or depictions of the exact connectors, buttons or included accessories of a SKU.
function station(ctx, x, y, scale, style, roll = 0) {
  const [front, lid, accent] = CASES[style], { w, h, handle, stripe } = STYLES[style];
  const l = -w / 2, r = w / 2, top = -h / 2, bot = h / 2;
  ctx.save(); ctx.translate(x, y); ctx.scale(scale, scale); ctx.rotate(roll);
  ellipse(ctx, '#192f3860', 13, bot + 12, w * .66, 18);
  for (const k of [l + 15, r - 33]) rounded(ctx, '#223b3a', k, bot - 5, 28, 16, 4);
  path(ctx, [[l + 7, top + 4], [l + 41, top - 23], [r + 23, top - 23], [r + 45, top - 8], [r + 41, bot - 20],
    [r - 8, bot + 3]], '#233f43', '#1c383d', 2.5);
  path(ctx, [[l + 10, top + 4], [l + 41, top - 23], [r + 23, top - 23], [r + 41, top - 11], [r - 5, top + 5]], lid, '#2a4a46', 2.2);
  const grip = w * handle * .51;
  rounded(ctx, '#314946', -grip / 2 + 11, top - 43, grip + 17, 32, 8, '#254240', 2.8);
  rounded(ctx, lid, -grip / 2 + 17, top - 37, grip + 5, 10, 4);
  rounded(ctx, front, l, top, w, h, 13, '#203a3f', 3);
  rounded(ctx, '#2c4246', l + 12, top + 16, w - 24, h - 33, 8, '#809988', 1.55);
  const insetX = l + 22, insetY = top + 29;
  rounded(ctx, '#98b7a4', insetX, insetY, 57, 25, 4, '#172f33', 1.8);
  for (const i of [0, 1, 2]) rounded(ctx, '#527868', insetX + 9 + i * 14, insetY + 6, 9, 12, 1.6);
  for (const i of [0, 1, 2]) {
    rounded(ctx, '#1c3438', r - 91 + i * 24, insetY + 3, 17, 19, 4, '#6d8c80', 1);
    line(ctx, r - 88 + i * 24, insetY + 11, 11, '#a3bdab', 1.9);
  }
  for (const i of [0, 1, 2]) line(ctx, l + 23 + 47 * i, bot - 28, 34, '#91a89c', 1.8);
  if (stripe) rounded(ctx, accent, l + 11, top + 16, 3.8, h - 33, 2.1);
  for (let k = 0; k < 5; k++) path(ctx, [[r + 14, bot - 42 + k * 5], [r + 33, bot - 52 + k * 5]], null, '#607c74', 1.5);
  ctx.restore();
}
function showroom(ctx, palette, x, y, w, h, t, accent, style = null, flip = false) {
  const paper = palette === LIGHT;
  rounded(ctx, palette.well, x, y, w, h, 10, palette.line, 1.5);
  ctx.save(); ctx.beginPath(); ctx.rect(x + 2, y + 2, w - 4, h - 4); ctx.clip();
  const diskX = x + (flip ? .29 : .77) * w, diskY = y + h * .31;
  ellipse(ctx, accent, diskX, diskY, Math.min(77, h * .30), Math.min(77, h * .30));
  ellipse(ctx, null, diskX, diskY, Math.min(92, h * .35), Math.min(92, h * .35), paper ? '#6f917734' : '#b5d1ad58', 1.35);
  path(ctx, [[x, y + h * .70], [x + w, y + h * .56], [x + w, y + h], [x, y + h]], paper ? '#97af94' : '#507869');
  path(ctx, [[x, y + h * .88], [x + w, y + h * .75], [x + w, y + h], [x, y + h]], paper ? '#aab997' : '#436a61');
  const time = t * BPM / 60;
  for (let i = 0; i < 5; i++) {
    const k = (i * 41 + t * 36) % (w + 42);
    path(ctx, [[x + k, y + h * .80 - k * .115], [x + k + 19, y + h * .80 - k * .115 - 2.18]], null,
      paper ? '#637e6957' : '#b4cd9c6b', 1.2);
  }
  const e = 1 - ease(t / .57), pop = -2.5 * (1 - Math.cos(time * Math.PI * .5));
  if (style == null) {
    station(ctx, x + w * .28 - 37 * e, y + h * .52 + pop, 1.03, 1, -.075);
    station(ctx, x + w * .72 + 35 * e, y + h * .53 - pop, .90, 2, .09);
    station(ctx, x + w * .48, y + h * .68 + 39 * e, 1.18, 0, -.028);
  } else {
    const drift = Math.sin(t * 1.3) * 6;
    station(ctx, x + w * .46 + (flip ? 46 : -46) * e + drift, y + h * .51 + pop + 8 * e,
      (h / 300) * (style === 3 || style === 4 ? 1.23 : 1.22), style, flip ? -.043 : .016);
  }
  glint(ctx, x + w * .12, y + h * .29, 12 + Math.sin(time * 1.2) * 4, paper ? '#f2ead0' : '#f8d798');
  glint(ctx, x + w * .86, y + h * .65, 10 + Math.cos(time) * 3, paper ? '#e6e6c1' : '#e8dfba');
  ctx.restore();
  rounded(ctx, paper ? '#edf0cfdf' : '#24484bef', x + 12, y + h - 35, 101, 23, 4);
  text(ctx, 'ИЛЛЮСТРАЦИЯ', x + 22, y + h - 19, 11, palette.ink, { track: .75 });
}
function intro(ctx, t, time, { alternate }) {
  const palette = alternate ? LIGHT : DARK, accent = alternate ? ACCENTS.blue : ACCENTS.amber;
  surface(ctx, palette, time, accent);
  metadata(ctx, palette, 'ПОРТАТИВНАЯ ЭНЕРГИЯ', 'ОБЗОР НАЛИЧИЯ', time, accent);
  text(ctx, 'Электростанции', 33, 174, 64, palette.ink, { max: 474 });
  text(ctx, 'в наличии.', 33, 255, 86, alternate ? '#446b60' : accent, { max: 474 });
  showroom(ctx, palette, LEFT, 298, SPAN, 378, t, accent, null, alternate);
  for (const [i, [number, label]] of [[String(BRANDS.length), 'БРЕНДОВ'], [String(STATIONS), 'СТАНЦИЯ']].entries()) {
    const x = LEFT + 241 * i;
    rounded(ctx, palette.tile, x, 710, 227, 95, 8, palette.line);
    text(ctx, number, x + 17, 778, 55, palette.ink);
    text(ctx, label, x + 92, 769, 16.5, palette.sub, { track: 1.05 });
  }
  text(ctx, '+ 1 дополнительный аккумулятор', LEFT, 855, 25, palette.ink, { medium: true });
}
function tile(ctx, palette, accent, item, index, y, h, t) {
  const reveal = (1 - ease((t - index * .065) / .46)) * 33;
  const x = LEFT + reveal;
  const isBattery = !!item.battery, tint = isBattery ? '#dce5b7' : palette.tile;
  rounded(ctx, tint, x, y, SPAN, h, 7, palette.line, 1.45);
  if (isBattery) {
    fill(ctx, '#64856b', x, y + 10, 4.4, h - 20);
    text(ctx, 'ДОПОЛНИТЕЛЬНЫЙ АККУМУЛЯТОР', x + 15, y + 24, 12.5, '#49664e', { track: .95 });
    text(ctx, item.model, x + 14, y + h - 14, 31, '#203b3d', { max: SPAN - 31 });
    return;
  }
  rounded(ctx, accent, x + 12, y + (h - 29) / 2, 33, 29, 4.5);
  text(ctx, String(index + 1).padStart(2, '0'), x + 28.5, y + h / 2 + 5.2, 13.2, '#234046', { align: 'center' });
  const info = badge(item);
  const tagW = item.wattHours ? 136 : 118;
  const modelMax = info ? SPAN - tagW - 75 : SPAN - 69;
  text(ctx, item.model, x + 57, y + (h + 23) / 2, (item.model.length < 11 ? 40 : 34), palette.ink, { max: modelMax });
  if (!info) return;
  const qx = x + SPAN - tagW - 10;
  rounded(ctx, accent, qx, y + (h - 57) / 2, tagW, 57, 5);
  text(ctx, info.caption, qx + 10, y + h / 2 - 9, 10.8, '#3c5752', { track: 1.1 });
  text(ctx, info.value, qx + 9, y + h / 2 + 16, 24, '#203c3f', { max: tagW - 17 });
}
function catalogue(ctx, t, time, { page }) {
  const palette = page.shape % 2 === 0 ? DARK : LIGHT, accent = ACCENTS[page.accent];
  surface(ctx, palette, time, accent);
  metadata(ctx, palette, 'ПОЗИЦИИ В НАЛИЧИИ', page.part ? `КАРТОЧКА ${page.part} / 2` : `БРЕНД ${BRANDS.indexOf(page.brand) + 1} / ${BRANDS.length}`, time, accent);
  text(ctx, page.brand, 32, 165, 91, palette.ink, { max: 474 });
  text(ctx, page.brand === 'DJI' ? '3 СТАНЦИИ + 1 АККУМУЛЯТОР' : page.part ? 'СЕРИЯ DELTA' : '3 МОДЕЛИ', LEFT, 205, 17,
    palette === LIGHT ? palette.sub : accent, { track: 1.65 });
  showroom(ctx, palette, LEFT, 232, SPAN, 291, t, accent, page.shape, page.shape % 2 === 1);
  const many = page.items.length > 3, y = many ? 543 : 558, h = many ? 74 : 85, gap = many ? 7 : 10;
  for (const [i, item] of page.items.entries()) tile(ctx, palette, accent, item, i, y + i * (h + gap), h, t);
}
function outro(ctx, t, time) {
  const palette = DARK, accent = ACCENTS.amber;
  surface(ctx, palette, time, accent);
  metadata(ctx, palette, 'ПОРТАТИВНЫЕ ЭЛЕКТРОСТАНЦИИ', 'В НАЛИЧИИ', time, accent);
  const rise = (1 - ease(t / .54)) * 19;
  rounded(ctx, '#23454b', LEFT, 156 + rise, SPAN, 430, 12, '#93b59c');
  ellipse(ctx, '#416a5f', W / 2, 357 + rise, 151, 151);
  const h = 276, w = logo.width * h / logo.height;
  ctx.drawImage(logo, (W - w) / 2, 224 + rise, w, h);
  text(ctx, 'Электростанции', 34, 665, 63, palette.ink, { max: 470 });
  text(ctx, 'в наличии.', 34, 748, 82, accent, { max: 470 });
  text(ctx, '6 брендов  ·  21 станция  ·  1 аккумулятор', LEFT, 827, 24, palette.ink, { medium: true, max: 468 });
}
function grain() {
  const canvas = createCanvas(131, 137), ctx = canvas.getContext('2d'), im = ctx.createImageData(131, 137);
  let seed = 711;
  for (let i = 0; i < im.data.length; i += 4) {
    seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0;
    const value = seed >>> 31 ? 235 : 29;
    im.data[i] = value; im.data[i + 1] = value; im.data[i + 2] = value - 7; im.data[i + 3] = (seed >>> 24) % 25;
  }
  ctx.putImageData(im, 0, 0);
  return canvas;
}
const scenes = { intro, catalogue, outro };
export function createFilm(scale = 2) {
  prepareFonts();
  const canvas = createCanvas(W * scale, H * scale), ctx = canvas.getContext('2d');
  const texture = ctx.createPattern(grain(), 'repeat');
  function draw(seconds) {
    const t = Math.max(0, Math.min(DURATION, seconds));
    const i = SHOTS.findLastIndex(({ start }) => t >= start), shot = SHOTS[i];
    const dt = t - shot.start;
    ctx.setTransform(scale, 0, 0, scale, 0, 0); ctx.lineJoin = 'round'; ctx.lineCap = 'round';
    scenes[shot.kind](ctx, dt, t, shot);
    ctx.save(); ctx.globalAlpha = .30; fill(ctx, texture, 0, 0, W, H); ctx.restore();
    if (i && dt < WIPE) {
      const q = ease(clamp(dt / WIPE)), x = -134 + 865 * q;
      path(ctx, [[x, 0], [x + 25, 0], [x - 80, H], [x - 107, H]], '#f2d39d51');
    }
    return canvas;
  }
  return { canvas, draw };
}
