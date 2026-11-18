import { createCanvas, GlobalFonts, Path2D } from '@napi-rs/canvas';
import { fileURLToPath } from 'node:url';
import QRCode from 'qrcode';
import { ALERT_AT, BEAT, CAT_AT, CHAPTERS, CONTACTS, DURATION, WIPE, chapterAt } from './story.mjs';

// Logical coordinates; the renderer scales this composition uniformly for HD or draft.
export const WIDTH = 540;
export const HEIGHT = 960;
const W = WIDTH;
const H = HEIGHT;
const TAU = 2 * Math.PI;
const C = {
  ink: '#203438', dark: '#172d33', cream: '#fff1d6', amber: '#f3c77c',
  coral: '#eb9072',
};

let fontsReady = false;
function registerFonts() {
  if (fontsReady) return;
  for (const weight of ['Black', 'Medium']) {
    const file = fileURLToPath(new URL(`../fonts/Roboto-${weight}.woff`, import.meta.url));
    if (!GlobalFonts.registerFromPath(file, `MaYak${weight}`)) {
      throw new Error(`Не удалось загрузить шрифт: ${file}`);
    }
  }
  fontsReady = true;
}

const clamp = (p) => Math.max(0, Math.min(1, p));
const ease = (p) => 1 - (1 - clamp(p)) ** 3;
const smooth = (p) => clamp(p) ** 2 * (3 - 2 * clamp(p));
const bounce = (p) => 1 + 2.25 * (clamp(p) - 1) ** 3 + 1.25 * (clamp(p) - 1) ** 2;
const mix = (a, b, n) => a + (b - a) * n;
const paths = new Map();
function svg(d) {
  if (!paths.has(d)) paths.set(d, new Path2D(d));
  return paths.get(d);
}
function shape(ctx, d, fill, stroke, width = 2) {
  const path = svg(d);
  if (fill) { ctx.fillStyle = fill; ctx.fill(path); }
  if (stroke) { ctx.strokeStyle = stroke; ctx.lineWidth = width; ctx.stroke(path); }
}
function poly(ctx, points, fill, stroke, width = 2) {
  ctx.beginPath();
  for (let i = 0; i < points.length; i += 2) {
    if (!i) ctx.moveTo(points[i], points[i + 1]);
    else ctx.lineTo(points[i], points[i + 1]);
  }
  if (fill) { ctx.closePath(); ctx.fillStyle = fill; ctx.fill(); }
  if (stroke) { ctx.strokeStyle = stroke; ctx.lineWidth = width; ctx.stroke(); }
}
function rect(ctx, x, y, w, h, fill) {
  ctx.fillStyle = fill;
  ctx.fillRect(x, y, w, h);
}
function rounded(ctx, x, y, w, h, radius, fill, stroke, width = 2) {
  ctx.beginPath(); ctx.roundRect(x, y, w, h, radius);
  if (fill) { ctx.fillStyle = fill; ctx.fill(); }
  if (stroke) { ctx.strokeStyle = stroke; ctx.lineWidth = width; ctx.stroke(); }
}
function oval(ctx, x, y, rx, ry, fill, stroke, width = 2) {
  ctx.beginPath(); ctx.ellipse(x, y, rx, ry, 0, 0, TAU);
  if (fill) { ctx.fillStyle = fill; ctx.fill(); }
  if (stroke) { ctx.strokeStyle = stroke; ctx.lineWidth = width; ctx.stroke(); }
}
function star(ctx, x, y, r, color) {
  poly(ctx, [x, y - r, x + r * .22, y - r * .22, x + r * .72, y,
    x + r * .22, y + r * .22, x, y + r, x - r * .22, y + r * .22,
    x - r * .72, y, x - r * .22, y - r * .22], color);
}
function text(ctx, value, x, y, size, color, opts = {}) {
  ctx.font = `${size}px MaYak${opts.medium ? 'Medium' : 'Black'}`;
  ctx.fillStyle = color;
  ctx.textBaseline = 'alphabetic';
  ctx.textAlign = opts.align ?? 'left';
  if (!opts.tracking) {
    ctx.fillText(value, x, y);
    return;
  }
  const chars = [...value];
  const lengths = chars.map((char) => ctx.measureText(char).width);
  const span = lengths.reduce((a, b) => a + b, 0) + opts.tracking * (chars.length - 1);
  if (opts.align === 'center') x -= span / 2;
  ctx.textAlign = 'left';
  chars.forEach((char, i) => {
    ctx.fillText(char, x, y);
    x += lengths[i] + opts.tracking;
  });
}
function hatch(ctx, x, y, w, rows, ink, drift = 0) {
  ctx.fillStyle = ink;
  for (let row = 0; row < rows; row++) {
    const n = 5 + (row % 3);
    for (let col = 0; col < n; col++) {
      ctx.fillRect(x + row * drift + (col + (row % 2) * .45) * w / n, y + row * 8,
        1 + ((row + col) % 3) * .9, 1.5);
    }
  }
}
function title(ctx, index, titleColor, accent, sizes) {
  const chapter = CHAPTERS[index];
  rect(ctx, 48, 56, 16, 3, accent);
  text(ctx, chapter.kicker, 74, 61, 12, accent, { tracking: 2 });
  text(ctx, `0${index + 1} / 0${CHAPTERS.length}`, 479, 61, 12, titleColor, { medium: true, align: 'right' });
  chapter.heading.forEach((line, i) => {
    text(ctx, line, 45, 147 + i * 76, sizes[i], i === chapter.heading.length - 1 ? accent : titleColor);
  });
}
function caption(ctx, index, t, bg, color, accent, y = 775) {
  const { body } = CHAPTERS[index];
  shape(ctx, 'M0 739 Q 198 761 540 731 L540 960 H0 Z', bg);
  const inAmount = ease((t - .28) / .6);
  ctx.save();
  ctx.globalAlpha *= inAmount;
  ctx.translate(0, 10 * (1 - inAmount));
  rect(ctx, 48, y - 16, 3, (body.length - 1) * 28 + 20, accent);
  body.forEach((line, i) => text(ctx, line, 64, y + i * 28, 21, color, { medium: true }));
  ctx.restore();
  // Three physical perforations tie the backing card to the other scenes.
  for (let i = 0; i < 3; i++) rect(ctx, 48 + 10 * i, 909, 5, 2, accent);
  rect(ctx, 420, 910, 58, 1, accent);
}

const FACTORY_COLORS = {
  a: { wall: '#aa9081', side: '#876f6c', roof: '#7b6566', cap: '#deb097', chimney: '#8a6b69' },
  b: { wall: '#a8b9a3', side: '#68877d', roof: '#527573', cap: '#c8c8a2', chimney: '#668982' },
};
function factory(ctx, x, y, size, side, lights = 1) {
  const c = FACTORY_COLORS[side];
  ctx.save(); ctx.translate(x, y); ctx.scale(size, size);
  oval(ctx, 131, 228, 150, 16, '#263c3e');
  for (const [sx, sy, sw] of (side === 'a' ? [[29, 2, 24], [67, 22, 21]] : [])) {
    poly(ctx, [sx, sy, sx + sw, sy, sx + sw + 5, 114, sx - 4, 114], c.chimney, C.ink, 2.8);
    poly(ctx, [sx + sw - 7, sy + 3, sx + sw, sy + 3, sx + sw + 5, 114, sx + sw - 3, 114], c.roof);
    rounded(ctx, sx - 3, sy - 4, sw + 6, 12, 2, c.cap, C.ink, 2.7);
  }
  poly(ctx, [0, 97, 211, 94, 211, 223, 0, 216], c.wall, C.ink, 3);
  poly(ctx, [211, 94, 270, 71, 270, 199, 211, 223], c.side, C.ink, 3);
  poly(ctx, [211, 205, 269, 182, 269, 198, 211, 222], c.roof);
  poly(ctx, [0, 201, 211, 207, 211, 222, 0, 216], c.side);
  shape(ctx, side === 'a' ? 'M-6 98 V70 L49 48 V71 L100 47 V70 L152 45 V68 L208 42 V65 L225 63 V96 Z' : 'M-6 98 V68 L225 63 V96 Z', c.roof, C.ink, 3.4);
  poly(ctx, [225, 63, 277, 43, 277, 73, 225, 96], c.side, C.ink, 3);
  poly(ctx, [-5, 81, 223, 79, 275, 60], null, c.cap, 2);
  poly(ctx, [-5, 99, 224, 96], null, C.ink, 3);
  rounded(ctx, 15, 108, 93, 24, 2, C.ink);
  text(ctx, side === 'a' ? 'ЗАВОД' : 'СКЛАД', 61.5, 125, 15, C.cream, { align: 'center', tracking: 1.7 });
  for (const [wx, ww] of [[16, 39], [66, 39], [116, 38]]) {
    poly(ctx, [wx, 146, wx + ww, 147, wx + ww, 192, wx, 191], '#53605e', C.ink, 2.6);
    ctx.save(); ctx.globalAlpha *= lights;
    poly(ctx, [wx + 1, 147, wx + ww - 1, 148, wx + ww - 1, 191, wx + 1, 190], '#eac27e');
    poly(ctx, [wx + 4, 149, wx + ww - 4, 151, wx + 4, 174], '#fde4a1');
    ctx.restore();
    poly(ctx, [wx, 175, wx + ww, 176], null, '#5c6159', 2);
    poly(ctx, [wx + ww * .49, 147, wx + ww * .49, 191], null, '#5c6159', 2);
  }
  poly(ctx, [164, 137, 201, 136, 201, 221, 164, 220], C.ink, C.ink, 3);
  poly(ctx, [169, 143, 196, 142, 196, 218, 169, 216], c.side);
  for (let i = 0; i < 5; i++) poly(ctx, [170, 153 + i * 12, 195, 152 + i * 12], null, c.roof, 1.8);
  poly(ctx, [226, 124, 257, 111, 257, 152, 226, 165], '#465859', C.ink, 2.6);
  ctx.save(); ctx.globalAlpha *= lights;
  poly(ctx, [228, 126, 255, 114, 255, 150, 228, 163], '#efd095');
  ctx.restore();
  poly(ctx, [227, 145, 256, 133], null, '#65685f', 1.8);
  hatch(ctx, 119, 115, 67, 2, c.side);
  hatch(ctx, 34, 210, 76, 1, c.roof);
  ctx.restore();
}

function drone(ctx, x, y, sc, t, tilt) {
  ctx.save(); ctx.translate(x, y); ctx.scale(sc, sc); ctx.rotate(tilt);
  // A generic, stylized quadcopter silhouette, not a model of any real equipment.
  const rotors = [[-59, -25, 20], [60, -22, 20], [-81, -4, 29], [81, -4, 29]];
  shape(ctx, 'M-17 -8 L-59 -27 M17 -8 L60 -24', null, '#40575a', 9);
  shape(ctx, 'M-24 1 L-76 -6 M25 1 L79 -6', null, C.dark, 11);
  for (const [rx, ry, rw] of rotors) {
    oval(ctx, rx, ry, rw, 5, '#fcf1d64f');
    oval(ctx, rx, ry, rw * (.69 + .08 * Math.cos(t * 22 + rx)), 1.6, '#31494b');
    rounded(ctx, rx - 5, ry - 3, 10, 9, 3, C.dark);
  }
  shape(ctx, 'M-39 0 Q-32 -18 -10 -20 L14 -20 Q33 -17 40 -1 L32 16 Q10 28 -18 20 Q-35 15 -39 0Z',
    C.dark, '#fcf1d687', 1.5);
  shape(ctx, 'M-30 -2 Q-25 -14 -8 -15 L12 -15 Q26 -14 30 -7 Q8 -12 -13 -6 Z', '#5c7775');
  rounded(ctx, -13, 6, 25, 12, 5, '#425f61');
  oval(ctx, 2, 12, 4.7, 4, C.amber);
  oval(ctx, 3, 11, 1.6, 1.6, C.cream);
  ctx.restore();
}

function pine(ctx, x, y, s, color, tilt) {
  ctx.save(); ctx.translate(x, y); ctx.scale(s, s); ctx.rotate(tilt);
  shape(ctx, 'M0 -120 Q-7 -96 -21 -82 L-11 -81 Q-24 -60 -34 -50 L-20 -48 Q-33 -28 -47 -17 L-5 -8 L-5 5 L5 5 L5 -8 L44 -16 Q33 -25 18 -46 L33 -49 Q20 -63 11 -82 L21 -83 Q8 -99 0 -120 Z', color);
  ctx.restore();
}

function outside(ctx, t) {
  const sky = ctx.createLinearGradient(0, 228, 0, 683);
  sky.addColorStop(0, '#29454d'); sky.addColorStop(.58, '#607d79'); sky.addColorStop(1, '#b6a27c');
  rect(ctx, 0, 0, W, H, sky);
  ctx.save();
  ctx.translate(270, 521);
  const push = 1 + .025 * smooth(t / 5);
  ctx.scale(push, push); ctx.translate(-270, -521);
  const mx = 390 - t * 1.6;
  oval(ctx, mx + 6, 375, 90, 89, '#ae7a65');
  oval(ctx, mx, 367, 90, 89, '#ecc383');
  hatch(ctx, mx - 60, 384, 121, 6, '#c6936a', 2.2);
  poly(ctx, [mx - 81, 399, mx + 73, 399], null, '#cd9e73', 1.8);
  shape(ctx, 'M-20 385 C44 376 68 357 117 363 Q141 368 183 368 Q222 366 261 379 Q169 398 -20 390 Z', '#a4b6a57c');
  shape(ctx, 'M235 438 Q322 413 372 421 Q427 434 540 414 V434 Q426 445 362 435 Q309 427 235 440Z', '#f0c89279');
  star(ctx, 143, 308, 7, '#e9cd9a');
  star(ctx, 485, 269, 9, '#e9cd9a');
  shape(ctx, 'M-14 516 Q72 448 157 452 Q218 455 272 491 Q324 520 405 466 Q477 430 558 460 V684 H-14 Z', '#85988a');
  shape(ctx, 'M-17 532 Q71 500 136 528 Q197 558 287 535 Q455 489 561 525 V708 H-17 Z', '#5b7772');
  for (let i = 0; i < 12; i++) {
    const x = 6 + i * 48;
    const h = 15 + i * 23 % 49;
    rect(ctx, x, 589 - h, 25 + i * 5 % 16, h + 13, '#4d6969');
    rect(ctx, x + 8, 597 - h, 5, 6, '#d2be8e');
  }
  hatch(ctx, 28, 494, 81, 4, '#a3b7a3', 3);
  hatch(ctx, 425, 488, 70, 3, '#9eb2a1', -2);
  shape(ctx, 'M-20 623 Q114 596 276 616 Q419 621 557 585 V780 H-20Z', '#43605f');
  shape(ctx, 'M-20 733 Q98 703 179 708 Q310 713 559 681 V727 Q348 758 178 743 Q71 735 -20 755Z', '#7b8a78');
  poly(ctx, [-6, 742, 177, 724, 357, 727, 540, 704], null, '#c6b18c', 1.8);
  factory(ctx, 38, 486, .82, 'a');
  factory(ctx, 280, 493, .82, 'b');
  pine(ctx, 12, 703, .82, '#2a4849', .08);
  pine(ctx, 518, 711, 1.07, '#2d4a4a', -.1);
  pine(ctx, 508, 740, .66, '#315451', .02);
  const approach = ease((t - .2) / 2.2);
  // The drone stays above the scene, with no flight path or strike shown.
  drone(ctx, mix(626, 352, approach) + 12 * Math.sin(t * 1.08), 341 + 5 * Math.sin(t * 2.4), .66 + .22 * approach, t, -.08 + .035 * Math.sin(t * 1.8));
  const clouds = smooth((t - 1.24) / 2.1);
  ctx.save(); ctx.globalAlpha *= clouds * .26;
  rect(ctx, -20, -30, 580, 850, '#454552');
  ctx.restore();
  ctx.restore();
  title(ctx, 0, C.cream, C.amber, [78, 82]);
  caption(ctx, 0, t, '#203a41', C.cream, C.amber);
}

const WINDOW = 'M65 526 V364 Q66 279 153 274 H269 Q344 278 352 363 V526 Z';
function attendant(ctx, t) {
  const lift = smooth((t - ALERT_AT - .13) / .65);
  const blink = Math.max(0, 1 - Math.abs(t - .82) / .11, 1 - Math.abs(t - 5.4) / .12);
  const notice = ease((t - ALERT_AT) / .43);
  ctx.save(); ctx.translate(187, 523 + 1.8 * Math.sin(t * 1.8)); ctx.scale(.95, .95);
  shape(ctx, 'M-103 74 C-130 88 -137 154 -125 237 H134 C136 163 120 105 93 93 L31 68 H-50 Z', '#cc7662', C.ink, 4);
  shape(ctx, 'M-122 235 V180 Q-115 129 -100 111 M-59 127 L-50 231 M85 109 Q99 161 94 231', null, '#a85f54', 3);
  shape(ctx, 'M-48 72 L27 69 L43 95 Q7 143 -40 105 L-60 91 Z', '#f3d8b0', C.ink, 3);
  shape(ctx, 'M-24 25 L27 36 L24 84 Q11 105 -22 84 Z', '#d88d73', C.ink, 3);
  ctx.save(); ctx.rotate(-.06 + .18 * notice);
  shape(ctx, 'M-76 35 C-114 -4 -96 -78 -52 -96 C-28 -115 31 -111 65 -82 Q101 -54 82 -3 Q83 35 56 62 L-57 61 Q-75 52 -76 35 Z', '#30373d', C.ink, 3);
  oval(ctx, -65, 5, 15, 19, '#e09b80', C.ink, 3);
  oval(ctx, 65, 9, 14, 19, '#e09b80', C.ink, 3);
  shape(ctx, 'M-66 -38 Q-45 -81 6 -77 Q67 -74 69 -25 L65 17 Q61 42 37 56 Q12 74 -16 65 Q-50 58 -62 32 Q-71 12 -66 -38 Z', '#f0ad8b', C.ink, 3);
  shape(ctx, 'M-66 -22 C-91 -54 -68 -91 -30 -99 Q25 -121 62 -88 Q84 -74 81 -38 Q75 -43 62 -39 Q42 -38 28 -56 Q7 -32 -31 -34 Q-46 -28 -66 -22 Z', '#313a40', C.ink, 3);
  shape(ctx, 'M-63 -66 Q-45 -89 -18 -91 M-39 -62 Q-4 -69 13 -87 M48 -81 Q65 -74 68 -59', null, '#61716d', 3);
  shape(ctx, 'M-77 -2 Q-73 -18 -63 -9 M70 -3 Q65 -10 61 1', null, '#a85f54', 2);
  oval(ctx, -65, 20, 3.5, 3.5, C.amber);
  for (const x of [-29, 28]) {
    ctx.save(); ctx.translate(x, -12 - notice * 3);
    shape(ctx, 'M-13 -12 Q-4 -19 9 -15', null, C.ink, 3);
    if (blink > .72) {
      shape(ctx, 'M-11 1 Q0 -2 10 1', null, C.ink, 2.5);
    } else {
      const height = (6 + notice * 3) * (1 - .75 * blink);
      oval(ctx, 0, 0, 10.6, height, C.cream, C.ink, 1.6);
      oval(ctx, -2 + 5.1 * notice, -.8 + 2.3 * lift, 3.25, height * .68, C.ink);
    }
    ctx.restore();
  }
  shape(ctx, 'M1 -10 Q-4 3 -6 10 Q0 15 7 10', null, '#ac6a59', 2.5);
  oval(ctx, -36, 18, 12, 5, '#df8b77'); oval(ctx, 39, 18, 10, 5, '#df8b77');
  if (notice > .28 && lift < .68) {
    oval(ctx, 1, 36, 5.2, 4.8, '#783c3c');
  } else {
    shape(ctx, 'M-7 36 Q2 39 12 35', null, '#8d514b', 2.5);
  }
  ctx.restore();

  const hx = mix(104, 100, lift);
  const hy = mix(188, 112, lift);
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  ctx.beginPath(); ctx.moveTo(102, 134); ctx.quadraticCurveTo(134, 187, hx + 7, hy + 19);
  ctx.lineWidth = 45; ctx.strokeStyle = C.ink; ctx.stroke();
  ctx.lineWidth = 38; ctx.strokeStyle = '#dc896f'; ctx.stroke();
  ctx.save(); ctx.translate(hx, hy); ctx.rotate(.15 - .33 * lift);
  rounded(ctx, -11, -34, 27, 48, 6, '#273941', '#162c32', 2.5);
  rounded(ctx, -7, -30, 19, 34, 3, lift > .1 ? '#efce8e' : '#73968d');
  rect(ctx, -4, -27, 11, 2, lift > .1 ? '#fff1c4' : '#b8c8b2');
  shape(ctx, 'M-12 16 Q-20 5 -14 -5 Q-9 -12 -6 -1 L-3 4 L11 3 Q21 7 14 18 L7 24 L-7 22 Z', '#f0ad8b', C.ink, 2.5);
  ctx.restore();
  ctx.restore();
}

function alertCard(ctx, t) {
  const pop = bounce((t - ALERT_AT) / .58);
  if (pop <= .005) return;
  ctx.save(); ctx.translate(373 + (1 - pop) * 97, 454 - (1 - pop) * 33);
  ctx.rotate(-.065 + (1 - pop) * .12); ctx.scale(pop, pop);
  rounded(ctx, -126 + 9, -65 + 10, 252, 130, 14, '#213f3d');
  rounded(ctx, -126 + 5, -65 + 5, 252, 130, 14, '#da967b');
  rounded(ctx, -126, -65, 252, 130, 14, '#f6e6bd', '#264c45', 3.2);
  ctx.save(); ctx.beginPath(); ctx.roundRect(-124, -63, 248, 126, 12); ctx.clip();
  rect(ctx, -124, -63, 248, 32, '#e4c18a');
  rect(ctx, -124, -32, 248, 2, '#ba9b73');
  ctx.restore();
  oval(ctx, -104, -47, 4.2, 4.2, '#b76756');
  text(ctx, 'УВЕДОМЛЕНИЕ', -91, -42, 13, '#5c5246', { tracking: 1.5 });
  text(ctx, 'Обнаружен', -106, 5, 29, '#294c47');
  text(ctx, 'дрон', -106, 44, 37, '#294c47');
  ctx.save(); ctx.translate(82, 23);
  oval(ctx, 0, 0, 28, 28, '#cfd7aa');
  shape(ctx, 'M-13 9 Q-8 6 -8 1 V-4 Q-8 -12 0 -12 Q8 -12 8 -4 V1 Q8 6 13 9 Z M-4 13 Q0 18 4 13', null, '#47726a', 2.6);
  ctx.restore();
  ctx.restore();
}

function inside(ctx, t) {
  rect(ctx, 0, 0, W, H, '#345451');
  shape(ctx, 'M0 263 L540 280 V734 L0 709Z', '#668075');
  shape(ctx, 'M0 384 L540 248 V381 L0 517Z', '#738f7f');
  shape(ctx, WINDOW, '#3c5a56', '#3d615d', 17);
  ctx.save(); ctx.clip(svg(WINDOW));
  rect(ctx, 65, 275, 287, 251, '#597c7a');
  oval(ctx, 114, 375, 52, 52, '#dbb77f');
  shape(ctx, 'M59 459 Q118 411 190 458 Q255 494 352 430 V529 H59 Z', '#829c88');
  factory(ctx, 112, 380, .58, 'b');
  poly(ctx, [131, 274, 66, 439, 66, 462, 164, 274], '#fff0d432');
  ctx.restore();
  shape(ctx, WINDOW, null, '#e4cb9d', 6);
  rect(ctx, 207, 277, 6, 248, '#e4cb9d');
  rounded(ctx, 52, 520, 315, 15, 4, '#d8bf91', C.ink, 3);
  shape(ctx, 'M0 570 L540 559 V718 H0 Z', '#55766c');
  rect(ctx, 0, 565, W, 5, '#83a08a');
  hatch(ctx, 410, 315, 69, 5, '#93ab94', -2);
  // Warm personal details keep this a staffed civilian site.
  shape(ctx, 'M452 673 Q448 621 430 607 M453 647 Q468 617 482 606 M452 645 Q452 612 455 591', null, '#284f46', 4);
  shape(ctx, 'M446 629 Q424 639 413 601 Q439 602 446 629 Z M458 639 Q477 589 494 599 Q490 627 458 639 Z M453 623 Q434 595 456 585 Q474 604 453 623 Z', '#b2c19b', C.ink, 2.5);
  poly(ctx, [432, 655, 472, 655, 467, 698, 437, 698], '#cf9376', C.ink, 3);
  attendant(ctx, t);
  const ping = (t - ALERT_AT) / .68;
  if (ping > 0 && ping < 1) {
    ctx.save(); ctx.globalAlpha *= .55 * (1 - ping);
    oval(ctx, 288, 617, 16 + 28 * ping, 17 + 28 * ping, null, '#fff1c0', 2.5);
    ctx.restore();
  }
  poly(ctx, [-12, 687, 503, 668, 550, 709, 550, 762, -12, 761], '#b19d7c', C.ink, 4);
  poly(ctx, [-15, 726, 552, 711, 552, 770, -15, 772], '#7e826b', C.ink, 4);
  poly(ctx, [303, 689, 407, 681, 442, 700, 335, 713], '#587c70', C.ink, 2);
  poly(ctx, [309, 687, 403, 680, 432, 696, 334, 707], '#f9dfb7', C.ink, 2);
  poly(ctx, [356, 685, 381, 701], null, '#908169', 1.5);
  rounded(ctx, 72, 672, 23, 14, 6, null, '#3a5253', 4);
  rounded(ctx, 51, 657, 35, 37, 6, '#8eab96', C.ink, 2.5);
  oval(ctx, 68.5, 658, 16, 4.8, '#554443', '#233f42', 2);
  alertCard(ctx, t);
  title(ctx, 1, C.cream, '#f4d287', [87, 82]);
  caption(ctx, 1, t, '#314d49', C.cream, '#f4d287');
}

function paperBox(ctx, x, y, s, tint = '#edc88b') {
  ctx.save(); ctx.translate(x, y); ctx.scale(s, s);
  poly(ctx, [0, 10, 28, 0, 88, 4, 60, 15], '#f6d9a4', C.ink, 2.5);
  poly(ctx, [60, 15, 88, 4, 88, 60, 60, 72], '#be936e', C.ink, 2.5);
  poly(ctx, [0, 10, 60, 15, 60, 72, 0, 67], tint, C.ink, 2.5);
  poly(ctx, [24, 12, 30, 13, 58, 2, 52, 2], '#b78665');
  poly(ctx, [24, 13, 31, 14, 31, 37, 24, 36], '#bf9570');
  rect(ctx, 10, 48, 21, 3, '#987e63');
  rect(ctx, 10, 54, 16, 2, '#ac9068');
  ctx.restore();
}

function packer(ctx, x, y, s, t, jacket) {
  const reach = .5 + .5 * Math.sin(t * TAU / (8 * BEAT));
  ctx.save(); ctx.translate(x, y + 2 * Math.sin(t * 2)); ctx.scale(s, s);
  shape(ctx, 'M-63 45 Q-82 72 -84 146 H89 Q77 67 57 46 Q13 25 -63 45Z', jacket, C.ink, 3.5);
  shape(ctx, 'M-18 18 H21 V56 Q2 69 -18 56Z', '#cf8e73', C.ink, 2.5);
  shape(ctx, 'M-52 -29 Q-54 -65 -15 -77 Q18 -86 44 -52 L49 -13 Q49 21 24 32 Q-6 47 -32 24 Q-53 7 -52 -29Z', '#eeb18c', C.ink, 3);
  shape(ctx, 'M-56 -23 L-55 -59 Q-40 -88 2 -86 Q42 -83 52 -51 L49 -19 Q30 -40 24 -48 Q10 -25 -12 -31 Q-35 -20 -56 -23Z', '#37484a', C.ink, 3);
  shape(ctx, 'M-62 -43 Q-58 -78 -21 -92 Q17 -104 43 -75 Q51 -65 53 -49Z', '#dcab73', C.ink, 3);
  shape(ctx, 'M-69 -47 Q-10 -56 60 -52 L63 -41 Q-6 -32 -64 -38Z', '#f0cd8a', C.ink, 3);
  for (const i of [-1, 1]) {
    const blink = Math.abs(Math.sin(t * .95 + i * .01)) < .07;
    if (blink) poly(ctx, [i * 16 - 5, -8, i * 16 + 5, -8], null, C.ink, 2.2);
    else oval(ctx, i * 16 + 1, -7, 3, 4.3, C.ink);
  }
  shape(ctx, 'M-8 13 Q0 17 8 13', null, '#895748', 2.4);
  shape(ctx, 'M-48 85 Q-31 108 4 120', null, '#314a4b', 22);
  shape(ctx, 'M-48 85 Q-31 108 4 120', null, jacket, 16);
  ctx.beginPath(); ctx.moveTo(48, 80); ctx.quadraticCurveTo(49 + 19 * reach, 98, 15 + 58 * reach, 128 - 14 * reach);
  ctx.lineWidth = 27; ctx.strokeStyle = C.ink; ctx.stroke();
  ctx.lineWidth = 21; ctx.strokeStyle = jacket; ctx.stroke();
  oval(ctx, 15 + 58 * reach, 128 - 14 * reach, 13, 9, '#f3d4a0', C.ink, 2.6);
  ctx.restore();
}

function workshop(ctx, t) {
  rect(ctx, 0, 0, W, H, '#34544f');
  shape(ctx, 'M0 257 L540 275 V762 L0 744 Z', '#7d9c8b', '#2c514d', 3);
  poly(ctx, [0, 369, 540, 345, 540, 363, 0, 387], '#597e71');
  for (const x of [50, 182, 313, 444]) {
    rounded(ctx, x, 296, 92, 202, 4, '#d7d5a4', '#4f7269', 5);
    poly(ctx, [x + 3, 416, x + 89, 333, x + 89, 360, x + 3, 444], '#eee3b2');
    rect(ctx, x + 3, 380, 86, 8, '#658b7c');
    rect(ctx, x + 43, 299, 6, 196, '#658b7c');
  }
  shape(ctx, 'M0 548 L540 501 V735 L0 773 Z', '#68897c');
  hatch(ctx, 408, 531, 57, 4, '#9bb6a0', -2);
  packer(ctx, 150, 489, 1.04, t + .74, '#c67b65');
  packer(ctx, 375, 485, .98, t + .12, '#517770');
  poly(ctx, [-8, 640, 547, 600, 557, 660, -9, 707], '#93a496', C.ink, 4);
  const travel = t * 88;
  for (let i = 0; i < 6; i++) {
    const x = (i * 146 + travel) % (146 * 6) - 148;
    paperBox(ctx, x, 626 - x * .071 - 63, .92, i % 2 ? '#e4b990' : '#f0cd93');
  }
  poly(ctx, [-9, 681, 549, 635, 552, 672, -9, 727], '#40635b', C.ink, 4.2);
  for (let i = 0; i < 21; i++) {
    const x = 9 + 27 * i;
    const y = 700 - x * .091;
    oval(ctx, x, y, 8, 8, '#88a292', C.ink, 1.8);
    poly(ctx, [x - 4 * Math.cos(t * 3), y - 4 * Math.sin(t * 3), x + 4 * Math.cos(t * 3), y + 4 * Math.sin(t * 3)], null, '#536e65', 1.2);
  }
  title(ctx, 2, C.cream, '#f4d393', [81, 91]);
  caption(ctx, 2, t, '#34544f', C.cream, '#f4d393');
}

function officeCat(ctx, t) {
  rect(ctx, 0, 0, W, H, '#4c4750');
  shape(ctx, 'M0 271 L540 242 V759 L0 744 Z', '#696268');
  oval(ctx, 276, 481, 172, 181, '#866d70');
  oval(ctx, 276, 481, 157, 164, '#b79b8c');
  oval(ctx, 291, 427, 63, 65, '#e9c593');
  shape(ctx, 'M112 516 Q166 482 217 521 Q268 560 308 526 Q369 486 433 524 Q427 585 396 614 Q327 661 276 645 Q163 627 112 516Z', '#9ba592');
  poly(ctx, [129, 548, 421, 548], null, '#a0aa95', 4);
  hatch(ctx, 61, 311, 75, 5, '#a28689', 1.7);
  hatch(ctx, 414, 584, 62, 4, '#9e8384', -3);
  const wake = ease((t - CAT_AT) / .3);
  const blink = 1 - .66 * smooth((t - CAT_AT - 1.05) / .42);
  ctx.save(); ctx.translate(250, 587 + 2.6 * Math.sin(t * 2.5));
  oval(ctx, 34, 92, 185, 16, '#48474e');
  ctx.save(); ctx.translate(130, 37); ctx.rotate(-.1 * wake + .075 * Math.sin(t * 2.4));
  shape(ctx, 'M0 20 Q46 33 62 9 Q75 -10 53 -23 Q45 -29 38 -20', null, C.ink, 24);
  shape(ctx, 'M0 20 Q46 33 62 9 Q75 -10 53 -23 Q45 -29 38 -20', null, '#596868', 18);
  ctx.restore();
  shape(ctx, 'M-114 30 Q-76 -39 1 -48 Q85 -59 133 -12 Q170 22 128 63 Q93 91 -36 84 Q-116 77 -114 30Z', '#566767', C.ink, 4);
  shape(ctx, 'M-110 54 Q-59 45 -17 61 Q33 78 76 51 Q72 77 51 80 Q-43 91 -110 68 Z', '#ced1ad');
  oval(ctx, -89, 69, 35, 17, '#dfcfa9', C.ink, 3);
  oval(ctx, -25, 74, 32, 14, '#dfcfa9', C.ink, 3);
  ctx.save(); ctx.translate(-89, 22 - 5 * wake); ctx.rotate(.045 - .10 * wake);
  shape(ctx, 'M-62 -4 L-67 -63 Q-46 -59 -29 -36 Q-3 -47 19 -34 Q34 -57 52 -58 L60 -3 Q63 34 31 49 Q-12 67 -44 38 Q-63 23 -62 -4Z', '#637273', C.ink, 3.7);
  poly(ctx, [-60, -51, -38, -30, -58, -19], '#c89184');
  poly(ctx, [45, -47, 27, -28, 53, -17], '#c89184');
  shape(ctx, 'M-26 3 Q-12 5 -6 16 Q3 7 18 10 Q44 12 36 32 Q24 58 -8 54 Q-35 52 -43 29 Q-49 10 -26 3Z', '#dfd4b4');
  shape(ctx, 'M-41 -4 Q-29 6 -17 -2', null, C.ink, 3.4);
  if (wake > .03) {
    oval(ctx, 25, -5, 13, 8.6 * wake * blink, '#e8c581', C.ink, 2.4);
    oval(ctx, 29, -5, 3, Math.max(1, 5.6 * wake * blink), C.ink);
  } else {
    shape(ctx, 'M11 -3 Q23 6 36 -2', null, C.ink, 3.4);
  }
  poly(ctx, [-10, 15, 5, 14, -1, 23], '#a46866');
  shape(ctx, 'M-1 23 Q-11 34 -19 24 M-1 23 Q8 35 16 24', null, '#75615a', 2);
  shape(ctx, 'M-42 16 L-69 11 M-38 23 L-69 25 M34 16 L62 12 M33 24 L63 30', null, '#d4c2a1', 2.2);
  ctx.restore(); ctx.restore();
  const bowl = ease((t - CAT_AT + .12) / .55);
  if (bowl > 0) {
    ctx.save(); ctx.translate(410 + 157 * (1 - bowl), 677);
    oval(ctx, 0, 21, 47, 11, '#464750');
    shape(ctx, 'M-46 -8 Q-37 28 0 30 Q39 27 45 -8 Z', '#ca927d', C.ink, 3);
    oval(ctx, 0, -8, 45, 12, '#efcc92', C.ink, 3);
    for (let i = 0; i < 7; i++) oval(ctx, -28 + 8.5 * i, -9 + 3 * Math.sin(i), 3.6, 2.6, '#987058');
    ctx.restore();
  }
  const glint = ease((t - CAT_AT) / .36) * (1 - ease((t - CAT_AT - .44) / .44));
  star(ctx, 113, 525, 21 * glint, '#f8dda1');
  title(ctx, 3, C.cream, '#f2b892', [80, 82]);
  caption(ctx, 3, t, '#4b444f', C.cream, '#f2b892');
}

const TICKET = 'M-198 -105 H198 Q208 -105 208 -95 V-24 C172 -24 172 24 208 24 V95 Q208 105 198 105 H-198 Q-208 105 -208 95 V24 C-172 24 -172 -24 -208 -24 V-95 Q-208 -105 -198 -105 Z';
const qrCodes = CONTACTS.map(({ href }) => QRCode.create(href, { errorCorrectionLevel: 'M' }).modules);
function socialCode(ctx, index, x, y) {
  const modules = qrCodes[index];
  const step = Math.floor(104 / (modules.size + 8));
  const artSize = step * (modules.size + 8);
  const left = Math.round(x - artSize / 2);
  // Integer module dimensions and a four-module quiet zone survive MP4 encoding.
  rounded(ctx, x - 69, y - 8, 138, 155, 7, '#304f4f', '#7a9382', 1.6);
  rect(ctx, left, y, artSize, artSize, '#fffdf0');
  for (let row = 0; row < modules.size; row++) {
    for (let col = 0; col < modules.size; col++) {
      if (modules.get(row, col)) rect(ctx, left + (col + 4) * step, y + (row + 4) * step, step, step, '#192828');
    }
  }
  text(ctx, CONTACTS[index].label, x, y + 119, 14, C.amber, { align: 'center' });
  text(ctx, CONTACTS[index].handle, x, y + 136, 12, C.cream, { align: 'center', medium: true });
}

function endCard(ctx, t) {
  rect(ctx, 0, 0, W, H, '#244246');
  oval(ctx, 270, 458, 181, 181, '#2f5557');
  oval(ctx, 270, 458, 191, 191, null, '#466e6d', 2);
  oval(ctx, 270, 458, 210, 210, null, '#496f6d', 1.5);
  hatch(ctx, 354, 705, 95, 7, '#638581', 2);
  hatch(ctx, 53, 335, 95, 6, '#638581', -.3);
  const progress = bounce((t - .2) / 1.18);
  ctx.save();
  ctx.translate(270, 437 + (1 - progress) * 158);
  ctx.rotate(-.065 + .12 * (1 - progress));
  ctx.scale(.78 + .15 * progress, .78 + .15 * progress);
  ctx.save(); ctx.translate(8, 11); shape(ctx, TICKET, '#122e35'); ctx.restore();
  ctx.save(); ctx.translate(4, 4); shape(ctx, TICKET, '#d5836b'); ctx.restore();
  shape(ctx, TICKET, '#f4dbab', '#203a41', 3);
  rect(ctx, -172, -84, 344, 2, '#a0846b');
  rect(ctx, -172, 80, 344, 2, '#a0846b');
  star(ctx, -157, -68, 6, '#a05d4c'); star(ctx, 157, -68, 6, '#a05d4c');
  text(ctx, 'МАГАЗИН', 0, -33, 18, '#704e44', { align: 'center', tracking: 5 });
  text(ctx, 'В ОКОПЕ', 0, 43, 72, '#203a41', { align: 'center' });
  ctx.restore();
  star(ctx, 437, 317, 23 * ease((t - .7) / .7), C.amber);
  star(ctx, 98, 570, 16 * ease((t - 1) / .7), C.coral);
  title(ctx, 4, C.cream, C.amber, [86, 85]);
  const tag = ease((t - .78) / .46);
  ctx.save(); ctx.globalAlpha *= tag;
  text(ctx, 'АВТОМАТИЧЕСКОЕ ОПОВЕЩЕНИЕ', 270, 592, 15, C.cream, { align: 'center', tracking: 1.8 });
  CONTACTS.forEach((_, index) => socialCode(ctx, index, 115 + 155 * index, 639));
  ctx.restore();
}

const scenes = [outside, inside, workshop, officeCat, endCard];

function paperTile() {
  const tile = createCanvas(173, 157);
  const ctx = tile.getContext('2d');
  const image = ctx.createImageData(tile.width, tile.height);
  let state = 4061;
  for (let i = 0; i < image.data.length; i += 4) {
    state = (Math.imul(state, 1664525) + 1013904223) >>> 0;
    const light = (state >>> 30) > 1;
    image.data[i] = light ? 255 : 20;
    image.data[i + 1] = light ? 246 : 31;
    image.data[i + 2] = light ? 219 : 33;
    image.data[i + 3] = (state >>> 23) % (light ? 38 : 45);
  }
  ctx.putImageData(image, 0, 0);
  return tile;
}

export function createFilm(scale = 2) {
  registerFonts();
  const canvas = createCanvas(W * scale, H * scale);
  const ctx = canvas.getContext('2d');
  const texture = ctx.createPattern(paperTile(), 'repeat');
  function draw(time) {
    const t = Math.min(DURATION, Math.max(0, time));
    const i = chapterAt(t);
    const local = t - CHAPTERS[i].start;
    ctx.setTransform(scale, 0, 0, scale, 0, 0);
    ctx.lineCap = 'round'; ctx.lineJoin = 'round';
    if (i > 0 && local < WIPE) {
      scenes[i - 1](ctx, t - CHAPTERS[i - 1].start);
      // A single cut-paper edge carries the next drawing in from the right.
      const x = mix(W + 124, -96, smooth(local / WIPE));
      function edge(offset) {
        ctx.beginPath(); ctx.moveTo(x + offset + 87, 0); ctx.lineTo(W + 185, 0);
        ctx.lineTo(W + 185, H); ctx.lineTo(x + offset - 80, H); ctx.closePath();
      }
      edge(-9); ctx.fillStyle = '#dc9274'; ctx.fill();
      edge(16); ctx.fillStyle = '#f5d9a6'; ctx.fill();
      ctx.save(); edge(30); ctx.clip(); scenes[i](ctx, local); ctx.restore();
    } else {
      scenes[i](ctx, local);
    }
    ctx.save(); ctx.globalAlpha = .46; rect(ctx, 0, 0, W, H, texture); ctx.restore();
    return canvas;
  }
  return { canvas, draw };
}
