import { createCanvas, GlobalFonts, Path2D } from '@napi-rs/canvas';
import { fileURLToPath } from 'node:url';
import QRCode from 'qrcode';
import { BEEP_AT, BEAT, CAT_AT, CHAPTERS, CONTACTS, DURATION, WIPE, WORK_CUTS, chapterAt } from './story.mjs';

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

function soundSignal(ctx, t) {
  rect(ctx, 0, 0, W, H, '#493e49');
  shape(ctx, 'M-20 362 L555 274 V687 L-20 766Z', '#6d545a');
  shape(ctx, 'M-14 521 L560 401 V466 L-14 586Z', '#89655f');
  hatch(ctx, 55, 296, 81, 5, '#b0867b', 3);
  hatch(ctx, 409, 664, 63, 5, '#b0867b', -3);
  const since = Math.max(0, t - BEEP_AT);
  const pulse = ease((t - BEEP_AT) / .16) * (1 - ease((t - BEEP_AT - .15) / .65));
  const reveal = bounce((t - BEEP_AT) / .44);
  ctx.save(); ctx.translate(264, 514); ctx.rotate(-.055 + .025 * pulse);
  ctx.scale(1 + .033 * pulse, 1 + .033 * pulse);
  rounded(ctx, -211 + 8, -159 + 12, 422, 337, 9, '#322c39');
  rounded(ctx, -211, -159, 422, 337, 9, '#e1b494', '#493447', 4);
  rounded(ctx, -200, -147, 400, 314, 4, '#f2ce98', '#a26f66', 2.4);
  shape(ctx, 'M-200 94 L200 70 V165 H-200Z', '#dbac83');
  hatch(ctx, -187, 115, 117, 4, '#b1846a', 3);
  oval(ctx, -43, 0, 103, 100, '#d59582', '#a4776a', 2.4);
  oval(ctx, -43, 0, 91, 88, '#edbf94');
  // An editorial sound icon, not a depiction of a device or its controls.
  shape(ctx, 'M-100 -23 H-69 L-33 -54 Q-24 -61 -24 -49 V51 Q-24 64 -34 55 L-69 25 H-100Z', '#29484a', '#304448', 4);
  shape(ctx, 'M-19 -26 Q14 0 -19 26 M-5 -43 Q46 0 -5 43', null, '#d67463', 5.7 + 2 * pulse);
  rounded(ctx, -137, 128, 274, 25, 4, '#815956');
  text(ctx, 'КОРОТКИЙ СИГНАЛ', 0, 146, 13, C.cream, { align: 'center', tracking: 2.2 });
  ctx.restore();
  if (reveal > .015) {
    ctx.save(); ctx.translate(371 + 79 * (1 - reveal), 438 - 31 * (1 - reveal));
    ctx.rotate(.07); ctx.scale(reveal, reveal);
    shape(ctx, 'M-41 -56 L56 -64 L104 -30 L94 45 L23 68 L-11 62 L-85 90 L-63 48 L-97 20 L-81 -33Z', '#472e3a');
    shape(ctx, 'M-45 -61 L52 -69 L99 -35 L88 40 L19 63 L-16 58 L-84 85 L-64 43 L-104 14 L-85 -38Z', '#eb9075', '#5b3948', 3.5);
    text(ctx, 'БИП!', -3, 22, 51, '#fff1d2', { align: 'center' });
    ctx.restore();
  }
  const rays = .45 + .55 * pulse;
  star(ctx, 439, 336, 17 * rays, '#ffe6a2');
  star(ctx, 98, 675, 13 * (1 - .2 * ease(since)), '#f5b28c');
  title(ctx, 1, C.cream, '#f4bb8e', [87, 82]);
  caption(ctx, 1, t, '#493e49', C.cream, '#f4bb8e');
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

function workWide(ctx, t) {
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
}

function packingClose(ctx, t, angle) {
  rect(ctx, 0, 264, W, 510, '#6c8c80');
  poly(ctx, [-20, 463, 555, 277, 555, 370, -20, 558], '#9fb69f');
  poly(ctx, [-20, 638, 560, 506, 560, 750, -20, 792], '#55766d');
  hatch(ctx, 415, 577, 77, 6, '#9ab29a', 1.1);
  ctx.save(); ctx.translate(272, 518); ctx.rotate(angle);
  oval(ctx, 5, 143, 196, 39, '#45665f');
  paperBox(ctx, -145, -115, 3.25);
  const travel = smooth(t / (3.4 * BEAT));
  ctx.translate(-157 + 308 * travel, -25 + 22 * travel);
  shape(ctx, 'M-160 -19 Q-64 -58 -33 -36 L-2 -12 Q18 8 -7 33 L-27 47 Q-74 43 -120 30 L-162 29Z', '#a85f55', C.ink, 5);
  shape(ctx, 'M-46 -29 Q-20 -53 14 -38 L48 -23 Q63 -7 42 7 L21 10 L24 26 Q17 44 -9 33 L-30 18Z', '#f0d3a0', C.ink, 4);
  oval(ctx, 37, -13, 31, 30, '#a8b99d', C.ink, 4);
  oval(ctx, 37, -13, 13, 13, '#5a746a', C.ink, 2.5);
  ctx.restore();
  star(ctx, 427, 408, 15 * ease(t / .35), '#fae2ad');
}

function beltClose(ctx, t, tint) {
  rect(ctx, 0, 264, W, 500, tint);
  poly(ctx, [-15, 533, 548, 359, 551, 457, -19, 640], '#a1b69c');
  poly(ctx, [-22, 611, 547, 511, 555, 620, -20, 743], '#486d64', C.ink, 4.5);
  poly(ctx, [-18, 615, 548, 513, 548, 542, -19, 655], '#91a38f', C.ink, 4);
  for (let i = 0; i < 9; i++) {
    const x = 13 + i * 68;
    const y = 670 - .19 * x;
    ctx.save(); ctx.translate(x, y); ctx.rotate(t * 4 + i * .46);
    oval(ctx, 0, 0, 24, 24, '#7d9b89', '#274e48', 3.6);
    oval(ctx, 0, 0, 8.5, 8.5, '#496d63');
    poly(ctx, [-13, 0, -8, 0, 8, 0, 13, 0], null, '#b3c0a2', 3);
    ctx.restore();
  }
  for (const [i, tint] of [[-1, '#d8ac88'], [0, '#ebbf90'], [1, '#ecc892']]) {
    const x = i * 211 + 66 + 97 * t;
    paperBox(ctx, x, 454 - .18 * x, 2.15, tint);
  }
  hatch(ctx, 55, 342, 74, 4, '#90a999', 2);
}

function boxesInStore(ctx, t) {
  rect(ctx, 0, 264, W, 502, '#597e73');
  shape(ctx, 'M0 345 L540 294 V729 L0 771Z', '#7f9c89');
  for (let i = 0; i < 3; i++) {
    const x = 50 + i * 159;
    rounded(ctx, x, 321, 126, 125, 3, '#c5c9a2', '#5c7d71', 4);
    poly(ctx, [x + 8, 407, x + 117, 339, x + 117, 356, x + 8, 424], '#e4d9ab');
  }
  const drift = 12 * smooth(t / (4 * BEAT));
  ctx.save(); ctx.translate(-drift, 0);
  poly(ctx, [-20, 630, 559, 569, 561, 714, -20, 774], '#597c70');
  oval(ctx, 242, 683, 224, 31, '#41675f');
  paperBox(ctx, 68, 548, 1.58, '#c99f81');
  paperBox(ctx, 184, 519, 1.62, '#edcb94');
  paperBox(ctx, 326, 555, 1.4, '#d6ae89');
  paperBox(ctx, 92, 458, 1.38, '#e3b88b');
  paperBox(ctx, 232, 435, 1.35, '#ebc990');
  paperBox(ctx, 340, 484, 1.23, '#ecc68b');
  ctx.restore();
  hatch(ctx, 408, 664, 81, 6, '#93ab95', -3);
}

function paperCheck(ctx, t) {
  rect(ctx, 0, 263, W, 508, '#7c9a88');
  shape(ctx, 'M-14 405 L552 293 V376 L-14 521Z', '#a4b99f');
  hatch(ctx, 63, 507, 89, 8, '#b1bea0', 2);
  paperBox(ctx, 306, 456, 2.02, '#dcb78b');
  const lay = ease(t / .45);
  ctx.save(); ctx.translate(226, 510 + 21 * (1 - lay)); ctx.rotate(mix(-.15, -.055, lay));
  rounded(ctx, -127 + 7, -158 + 11, 253, 326, 8, '#4c6c61');
  rounded(ctx, -127, -158, 253, 326, 8, '#f3ddb0', '#365b55', 3.8);
  rounded(ctx, -43, -173, 86, 26, 7, '#c19472', '#596e60', 3);
  const marks = [3, 4, 6];
  for (let row = 0; row < marks.length; row++) {
    const y = -103 + row * 81;
    rounded(ctx, -91, y - 8, 41, 42, 4, '#e1cf9e', '#6d897a', 3.2);
    const reveal = ease((t + .09 - row * BEAT * .65) / .23);
    poly(ctx, [-83, y + 12, -75, y + 21, -56, y + 1], null, `rgba(81,112,95,${reveal})`, 4.3);
    for (let i = 0; i < 2; i++) rect(ctx, -30, y + 4 + 15 * i, 97 + marks[row] * 4 - 23 * i, 3, '#a69270');
  }
  ctx.restore();
}

const workShots = [
  ['ЦЕХ', (ctx, t) => workWide(ctx, t)],
  ['ЛЕНТА', (ctx, t) => beltClose(ctx, t, '#729181')],
  ['УПАКОВКА', (ctx, t) => packingClose(ctx, t, -.1)],
  ['ПРОВЕРКА', paperCheck],
  ['СКЛАД', boxesInStore],
  ['УПАКОВКА', (ctx, t) => packingClose(ctx, t + .18, .1)],
  ['ЛЕНТА', (ctx, t) => beltClose(ctx, t + .42, '#8aa18a')],
  ['СМЕНА ИДЁТ', (ctx, t) => workWide(ctx, t + 3.16)],
];

function workshop(ctx, t) {
  rect(ctx, 0, 0, W, H, '#30534e');
  const index = WORK_CUTS.findLastIndex((cut) => t >= cut);
  const local = t - WORK_CUTS[index];
  const [label, draw] = workShots[index];
  ctx.save(); ctx.beginPath(); ctx.rect(0, 258, W, 486); ctx.clip();
  const impact = (1 - ease(local / .24)) * .032;
  ctx.translate(270, 516); ctx.scale(1 + impact, 1 + impact); ctx.translate(-270, -516);
  draw(ctx, local);
  ctx.restore();
  rounded(ctx, 48, 276, 171, 30, 3, '#32574e');
  text(ctx, label, 61, 295.5, 12, '#f5db9f', { tracking: 2 });
  title(ctx, 2, C.cream, '#f4d393', [81, 91]);
  caption(ctx, 2, t, '#34544f', C.cream, '#f4d393');
  for (let n = 0; n < WORK_CUTS.length; n++) {
    rect(ctx, 49 + n * 24, 872, 15, 3, n === index ? '#f9d590' : '#8da493');
  }
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
  title(ctx, 4, C.cream, C.amber, [47, 56]);
  const tag = ease((t - .78) / .46);
  ctx.save(); ctx.globalAlpha *= tag;
  text(ctx, 'ДЕТЕКТОРЫ ДРОНОВ', 270, 592, 15, C.cream, { align: 'center', tracking: 1.8 });
  CONTACTS.forEach((_, index) => socialCode(ctx, index, 115 + 155 * index, 639));
  ctx.restore();
}

const scenes = [outside, soundSignal, workshop, officeCat, endCard];

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
