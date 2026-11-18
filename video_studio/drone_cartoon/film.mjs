import { createCanvas, GlobalFonts, Path2D } from '@napi-rs/canvas';
import { fileURLToPath } from 'node:url';
import { CHAPTERS, DURATION, WIPE, chapterAt } from './story.mjs';

// Logical coordinates; the renderer scales this composition uniformly for HD or draft.
export const WIDTH = 540;
export const HEIGHT = 960;
const W = WIDTH;
const H = HEIGHT;
const TAU = 2 * Math.PI;
const C = {
  ink: '#203438', dark: '#172d33', cream: '#fff1d6', amber: '#f3c77c',
  coral: '#eb9072', moss: '#a8c1a7', rim: '#94b2a7',
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
  text(ctx, `0${index + 1} / 04`, 479, 61, 12, titleColor, { medium: true, align: 'right' });
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

const ROOF = 'M-13 72 L126 33 L427 43 L286 83 Z';
function building(ctx, x, y, size) {
  ctx.save(); ctx.translate(x, y); ctx.scale(size, size);
  oval(ctx, 211, 231, 225, 18, '#263c3e');
  poly(ctx, [0, 79, 278, 90, 278, 228, 0, 217], '#a2b7a6', C.ink, 3);
  poly(ctx, [278, 90, 417, 52, 417, 182, 278, 228], '#648681', C.ink, 3);
  poly(ctx, [1, 199, 276, 210, 276, 227, 1, 216], '#587673');
  poly(ctx, [279, 210, 416, 169, 416, 181, 279, 226], '#4c6a69');
  shape(ctx, ROOF, '#719790', C.ink, 3);
  poly(ctx, [-13, 72, 286, 83, 286, 100, -13, 89], '#456c6a', C.ink, 3);
  poly(ctx, [286, 83, 427, 43, 427, 60, 286, 100], '#3d5c60', C.ink, 3);
  poly(ctx, [-3, 73, 282, 83, 410, 48], null, '#b1bda0', 2);
  // The entrance and its warm light are the visual motif shared between shots.
  ctx.save(); ctx.translate(101, 105); ctx.rotate(.034);
  rounded(ctx, 0, 0, 96, 27, 3, C.ink);
  text(ctx, 'МАЯК', 48, 20, 17, C.cream, { align: 'center', tracking: 2 });
  ctx.restore();
  poly(ctx, [105, 145, 195, 150, 195, 225, 105, 220], '#3a5355', C.ink, 3);
  poly(ctx, [118, 154, 180, 157, 180, 224, 118, 220], '#ecb176', C.ink, 3);
  poly(ctx, [149, 157, 149, 222], null, '#56605b', 2);
  poly(ctx, [122, 166, 145, 168, 122, 191], '#f8ce8c');
  poly(ctx, [153, 167, 175, 168, 153, 193], '#f9ce8c');
  poly(ctx, [139, 194, 139, 205], null, C.ink, 2);
  poly(ctx, [157, 195, 157, 206], null, C.ink, 2);
  poly(ctx, [98, 220, 196, 225, 202, 232, 87, 227], '#d5bb8d', C.ink);
  for (const [wx, wy, ww] of [[16, 119, 32], [55, 121, 35], [210, 125, 50]]) {
    poly(ctx, [wx, wy, wx + ww, wy + 2, wx + ww, wy + 50, wx, wy + 48], C.amber, C.ink, 3);
    poly(ctx, [wx + 4, wy + 4, wx + ww - 5, wy + 6, wx + 4, wy + 29], '#fbe0a0');
    poly(ctx, [wx + ww / 2, wy + 2, wx + ww / 2, wy + 47], null, '#566360', 2);
    poly(ctx, [wx + 1, wy + 31, wx + ww - 1, wy + 32], null, '#566360', 2);
  }
  for (const [wx, wy] of [[293, 119], [339, 106], [382, 94]]) {
    poly(ctx, [wx, wy, wx + 25, wy - 8, wx + 25, wy + 37, wx, wy + 44], '#e4ac6f', C.ink, 3);
    poly(ctx, [wx + 4, wy + 5, wx + 21, wy - 2, wx + 4, wy + 25], '#f9d290');
    poly(ctx, [wx + 1, wy + 25, wx + 24, wy + 19], null, '#5a655c', 2);
  }
  hatch(ctx, 31, 184, 51, 2, '#7d9d91', 0);
  hatch(ctx, 225, 191, 37, 2, '#7d9d91', 0);
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
  const sky = ctx.createLinearGradient(0, 215, 0, 633);
  sky.addColorStop(0, '#294650'); sky.addColorStop(.51, '#557577'); sky.addColorStop(1, '#b3a078');
  rect(ctx, 0, 0, W, H, sky);
  ctx.save();
  ctx.translate(270, 506); ctx.scale(1 + .035 * smooth(t / 5), 1 + .035 * smooth(t / 5)); ctx.translate(-270, -506);
  const mx = 392 - t * 1.4;
  oval(ctx, mx + 7, 354, 81, 81, '#bb8568');
  oval(ctx, mx, 348, 81, 81, '#eac081');
  hatch(ctx, mx - 63, 370, 121, 5, '#c99068', 3);
  poly(ctx, [mx - 72, 385, mx + 67, 385], null, '#c9926c', 2);
  shape(ctx, 'M-20 364 C47 358 61 326 114 334 C149 341 147 348 194 348 Q216 350 238 358 C157 367 58 376 -20 369 Z', '#98a99b7c');
  shape(ctx, 'M276 402 Q343 392 381 401 Q425 413 515 389 L551 397 V416 Q447 421 385 414 Q330 409 276 412Z', '#f3ca8e7b');
  star(ctx, 197, 281, 7, '#e9cd9a');
  star(ctx, 489, 269, 6, '#e9cd9a');
  shape(ctx, 'M-20 503 Q68 433 149 431 Q225 429 284 487 Q340 510 417 455 Q482 427 562 439 V668 H-20 Z', '#789189');
  shape(ctx, 'M-20 497 Q86 475 162 516 Q217 554 326 518 Q460 470 559 512 V731 H-20 Z', '#537270');
  hatch(ctx, 28, 473, 82, 5, '#9ab1a2', 4);
  hatch(ctx, 405, 475, 71, 4, '#9ab1a2', -3);
  for (let i = 0; i < 11; i++) {
    const x = 6 + i * 51;
    const h = 18 + (i * 17) % 40;
    rect(ctx, x, 572 - h, 26 + (i * 11) % 16, h + 20, '#456363');
    for (let j = 0; j < 2; j++) rect(ctx, x + 7 + 11 * j, 581 - h, 5, 7, '#d2be8e');
  }
  shape(ctx, 'M-20 622 Q165 574 322 600 Q470 623 559 582 V772 H-20 Z', '#496764');
  shape(ctx, 'M-15 743 Q45 687 133 674 L230 677 Q183 701 172 747 Z', '#8d9280');
  poly(ctx, [4, 754, 82, 715, 157, 689], null, '#d2bf92', 2);
  building(ctx, 63, 466, .99);
  pine(ctx, 35, 680, 1.04, '#2d494a', .08);
  pine(ctx, 498, 676, 1.56, '#2e4a49', -.06);
  pine(ctx, 469, 701, .92, '#345654', -.14);
  pine(ctx, 0, 738, 1.03, '#253f42', -.17);
  ctx.save(); ctx.translate(440, 675);
  shape(ctx, 'M0 18 L1 -88 Q0 -111 24 -110 L37 -110', null, '#293f43', 4);
  rounded(ctx, 25, -113, 26, 8, 4, C.amber, '#293f43', 2);
  ctx.restore();
  shape(ctx, 'M-20 725 Q65 702 123 730 Q192 751 241 728 Q333 694 396 724 Q468 750 560 712 V774 H-20 Z', '#304c4d');
  const approach = ease((t - .06) / 2.55);
  const dx = mix(651, 323, approach) + 12 * Math.sin(t * 1.2);
  const dy = mix(313, 375, approach) + 6 * Math.sin(t * 2.55);
  drone(ctx, dx, dy, .85 + .26 * approach, t, -.16 * (1 - approach) + .05 * Math.sin(t * 2));
  ctx.restore();
  title(ctx, 0, C.cream, C.amber, [72, 79]);
  caption(ctx, 0, t, '#203a41', C.cream, C.amber);
}

const WINDOW = 'M65 526 V364 Q66 279 153 274 H269 Q344 278 352 363 V526 Z';
function attendant(ctx, t) {
  const lift = smooth((t - 1) / 1.28);
  const talk = smooth((t - 2.35) / .3) * (1 - smooth((t - 4.75) / .5));
  const blink = Math.max(0, 1 - Math.abs(t - .78) / .11, 1 - Math.abs(t - 4.08) / .12);
  const notice = ease((t - .34) / .68);
  ctx.save(); ctx.translate(304, 509 + 2 * Math.sin(t * 2.1));
  shape(ctx, 'M-103 74 C-130 88 -137 154 -125 237 H134 C136 163 120 105 93 93 L31 68 H-50 Z', '#cc7662', C.ink, 4);
  shape(ctx, 'M-122 235 V180 Q-115 129 -100 111 M-59 127 L-50 231 M85 109 Q99 161 94 231', null, '#a85f54', 3);
  shape(ctx, 'M-48 72 L27 69 L43 95 Q7 143 -40 105 L-60 91 Z', '#f3d8b0', C.ink, 3);
  shape(ctx, 'M-24 25 L27 36 L24 84 Q11 105 -22 84 Z', '#d88d73', C.ink, 3);
  ctx.save(); ctx.rotate(-.13 * notice + .15 * lift);
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
      oval(ctx, -2 - 3.5 * notice + 5 * lift, -.75, 3.25, height * .72, C.ink);
    }
    ctx.restore();
  }
  shape(ctx, 'M1 -10 Q-4 3 -6 10 Q0 15 7 10', null, '#ac6a59', 2.5);
  oval(ctx, -36, 18, 12, 5, '#df8b77'); oval(ctx, 39, 18, 10, 5, '#df8b77');
  if (talk > .06) {
    const open = 2.5 + 3.3 * talk * (.5 + .5 * Math.sin(t * 15));
    oval(ctx, 0, 35, 7.5, open, '#783c3c');
  } else if (notice > .65 && lift < .25) {
    oval(ctx, 0, 35, 5.2, 4.8, '#783c3c');
  } else {
    shape(ctx, 'M-8 34 Q1 39 10 33', null, '#8d514b', 2.5);
  }
  ctx.restore();

  const hx = mix(103, 77, lift);
  const hy = mix(188, 24, lift);
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  ctx.beginPath(); ctx.moveTo(102, 134); ctx.quadraticCurveTo(134, 187, hx + 7, hy + 19);
  ctx.lineWidth = 45; ctx.strokeStyle = C.ink; ctx.stroke();
  ctx.lineWidth = 38; ctx.strokeStyle = '#dc896f'; ctx.stroke();
  ctx.save(); ctx.translate(hx, hy); ctx.rotate(.15 - .33 * lift);
  rounded(ctx, -11, -34, 27, 48, 6, '#273941', '#162c32', 2.5);
  rounded(ctx, -7, -30, 19, 34, 3, '#73968d');
  rect(ctx, -4, -27, 11, 2, '#b8c8b2');
  shape(ctx, 'M-12 16 Q-20 5 -14 -5 Q-9 -12 -6 -1 L-3 4 L11 3 Q21 7 14 18 L7 24 L-7 22 Z', '#f0ad8b', C.ink, 2.5);
  ctx.restore();
  ctx.restore();
}

function inside(ctx, t) {
  rect(ctx, 0, 0, W, H, '#4c404c');
  shape(ctx, 'M0 264 L540 279 V725 L0 704 Z', '#6a5058');
  shape(ctx, 'M0 407 L540 222 V366 L0 529 Z', '#77575c');
  shape(ctx, WINDOW, '#263f49', '#314348', 19);
  ctx.save(); ctx.clip(svg(WINDOW));
  rect(ctx, 65, 275, 287, 251, '#4c6a72');
  oval(ctx, 116, 368, 49, 49, '#dbab77');
  shape(ctx, 'M59 421 Q108 411 137 420 Q178 427 201 420 L219 431 Q142 446 57 437 Z', '#a8ab8f');
  shape(ctx, 'M55 471 Q140 437 197 473 Q260 500 356 445 V528 H55 Z', '#6e8b81');
  const drift = 4 * Math.sin(t * 1.7);
  drone(ctx, 164 + 9 * Math.sin(t * .7), 386 + drift, .48, t + 5.6, -.04);
  poly(ctx, [126, 275, 66, 433, 66, 459, 170, 275], '#f6e2cf2e');
  ctx.restore();
  shape(ctx, WINDOW, null, '#d5b68f', 6);
  rect(ctx, 210, 276, 7, 250, '#d5b68f');
  rounded(ctx, 51, 518, 313, 16, 4, '#d0a980', C.ink, 3);
  shape(ctx, 'M0 571 L540 556 V714 H0 Z', '#624e53');
  rect(ctx, 0, 564, W, 6, '#96706d');
  hatch(ctx, 408, 303, 63, 5, '#a47979', -2);
  // Little potted plant, mug and notebook establish an ordinary staffed building.
  shape(ctx, 'M101 675 Q99 631 80 601 M99 657 Q108 622 131 603 M98 649 Q97 619 102 589', null, '#233f42', 4);
  shape(ctx, 'M92 626 Q66 634 59 598 Q85 598 92 626 Z M106 635 Q127 589 147 598 Q142 622 106 635 Z M98 620 Q80 595 102 582 Q121 604 98 620 Z', '#a1b49b', C.ink, 2.5);
  poly(ctx, [79, 654, 123, 654, 118, 697, 84, 697], '#cc8a72', C.ink, 3);
  attendant(ctx, t);
  const cue = bounce((t - 2.5) / .44);
  if (cue > .01) {
    ctx.save(); ctx.translate(422, 393); ctx.scale(cue, cue);
    shape(ctx, 'M-27 -18 Q-41 -17 -41 -3 V9 Q-41 22 -27 22 H-7 L-18 35 L5 22 H29 Q43 22 43 8 V-5 Q43 -18 28 -18Z',
      C.cream, C.ink, 3);
    for (let i = -1; i <= 1; i++) oval(ctx, i * 15 + 1, 3, 2.8, 3.4 + 1.2 * Math.sin(7 * t - i), '#b46e5b');
    ctx.restore();
  }
  poly(ctx, [-12, 687, 505, 665, 550, 716, 550, 759, -12, 762], '#b98573', C.ink, 4);
  poly(ctx, [-15, 727, 552, 711, 552, 770, -15, 772], '#8a6363', C.ink, 4);
  poly(ctx, [177, 695, 289, 685, 324, 704, 211, 717], '#637e73', C.ink, 2);
  poly(ctx, [183, 692, 285, 683, 314, 700, 210, 710], '#f9dfb7', C.ink, 2);
  poly(ctx, [234, 688, 266, 706], null, '#8d7765', 1.5);
  poly(ctx, [218, 697, 248, 694, 255, 694], null, '#b59b7f', 1.5);
  rounded(ctx, 72, 672, 23, 14, 6, null, '#3a5253', 4);
  rounded(ctx, 51, 657, 35, 37, 6, '#8eab96', C.ink, 2.5);
  oval(ctx, 68.5, 658, 16, 4.8, '#554443', '#233f42', 2);
  title(ctx, 1, C.cream, '#f5ab8d', [72, 72]);
  caption(ctx, 1, t, '#493d4a', C.cream, '#f5ab8d');
}

const SHIELD = 'M0 -157 Q59 -127 125 -126 L125 -42 C123 36 58 104 0 133 C-63 102 -123 36 -125 -42 L-125 -126 Q-65 -128 0 -157 Z';
function shield(ctx, t) {
  rect(ctx, 0, 0, W, H, '#bfd0b3');
  oval(ctx, 266, 500, 184, 204, '#cdd9b9');
  oval(ctx, 266, 500, 188, 209, null, '#91aa98', 2);
  oval(ctx, 266, 500, 200, 225, null, '#a8baa3', 1.6);
  hatch(ctx, 46, 451, 73, 9, '#889e8b', 0);
  hatch(ctx, 399, 437, 69, 10, '#889e8b', -1);
  const reveal = bounce((t - .15) / .95);
  ctx.save(); ctx.translate(270, 499 + 57 * (1 - reveal) + 4 * Math.sin(t * 1.45));
  ctx.scale(.81 + .19 * reveal, .81 + .19 * reveal);
  ctx.rotate(-.06 * (1 - reveal));
  ctx.save(); ctx.translate(11, 15); shape(ctx, SHIELD, '#47736b'); ctx.restore();
  shape(ctx, SHIELD, '#f2dfad', '#315451', 4);
  ctx.save(); ctx.translate(0, -3); ctx.scale(.9, .9); shape(ctx, SHIELD, null, '#b3ae87', 2); ctx.restore();
  ctx.save(); ctx.clip(svg(SHIELD));
  oval(ctx, 4, -61, 55, 52, '#e3ba7e');
  shape(ctx, 'M-128 24 Q-74 -9 -2 24 Q58 39 128 4 V146 H-128 Z', '#a0b298');
  shape(ctx, 'M-128 59 Q-57 88 4 51 Q58 18 128 59 V146 H-128 Z', '#759487');
  hatch(ctx, -94, 76, 174, 5, '#9fb39a', -2.5);
  ctx.restore();
  const rise = ease((t - .73) / .65);
  ctx.save(); ctx.globalAlpha *= rise;
  building(ctx, -122, -47 + 19 * (1 - rise), .59);
  ctx.restore();
  ctx.restore();
  const glint = ease((t - .9) / .8);
  star(ctx, 116, 351, 23 * glint, '#f9e5a6');
  star(ctx, 415, 606, 19 * glint, '#f9e5a6');
  star(ctx, 450, 362, 8 * glint, '#607f72');
  star(ctx, 81, 626, 8 * glint, '#607f72');
  title(ctx, 2, '#243f3d', '#39645b', [71, 83]);
  caption(ctx, 2, t, '#d4dec0', '#263f3e', '#527d6c', 774);
}

const TICKET = 'M-198 -105 H198 Q208 -105 208 -95 V-24 C172 -24 172 24 208 24 V95 Q208 105 198 105 H-198 Q-208 105 -208 95 V24 C-172 24 -172 -24 -208 -24 V-95 Q-208 -105 -198 -105 Z';
function endCard(ctx, t) {
  rect(ctx, 0, 0, W, H, '#244246');
  oval(ctx, 270, 519, 181, 181, '#2f5557');
  oval(ctx, 270, 519, 191, 191, null, '#466e6d', 2);
  oval(ctx, 270, 519, 210, 210, null, '#496f6d', 1.5);
  hatch(ctx, 354, 705, 95, 7, '#638581', 2);
  hatch(ctx, 53, 335, 95, 6, '#638581', -.3);
  const progress = bounce((t - .2) / 1.18);
  ctx.save();
  ctx.translate(270, 510 + (1 - progress) * 204);
  ctx.rotate(-.065 + .12 * (1 - progress));
  ctx.scale(.86 + .14 * progress, .86 + .14 * progress);
  ctx.save(); ctx.translate(8, 11); shape(ctx, TICKET, '#122e35'); ctx.restore();
  ctx.save(); ctx.translate(4, 4); shape(ctx, TICKET, '#d5836b'); ctx.restore();
  shape(ctx, TICKET, '#f4dbab', '#203a41', 3);
  rect(ctx, -172, -84, 344, 2, '#a0846b');
  rect(ctx, -172, 80, 344, 2, '#a0846b');
  star(ctx, -157, -68, 6, '#a05d4c'); star(ctx, 157, -68, 6, '#a05d4c');
  text(ctx, 'МАГАЗИН', 0, -33, 18, '#704e44', { align: 'center', tracking: 5 });
  text(ctx, 'В ОКОПЕ', 0, 43, 72, '#203a41', { align: 'center' });
  ctx.restore();
  star(ctx, 435, 367, 23 * ease((t - .7) / .7), C.amber);
  star(ctx, 103, 655, 17 * ease((t - 1) / .7), C.coral);
  star(ctx, 463, 641, 7, '#8ea894');
  title(ctx, 3, C.cream, C.amber, [62, 70, 72]);
  text(ctx, 'КОНЕЦ', 270, 813, 13, '#ebc994', { align: 'center', tracking: 4 });
  rect(ctx, 241, 834, 58, 1, '#a79f7c');
}

const scenes = [outside, inside, shield, endCard];

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
