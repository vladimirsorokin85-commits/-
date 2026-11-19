import { createCanvas, GlobalFonts } from '@napi-rs/canvas';
import { fileURLToPath } from 'node:url';
import QRCode from 'qrcode';
import { BEEP_AT, CHAPTERS, CONTACTS, DURATION, GAME_OVER_AT, POV_SHOTS, SITE_SHOTS, SLOGAN, chapterAt } from './story.mjs';
import { CAMERAS, PANORAMA, renderWorld } from './world.mjs';

export const WIDTH = 540;
export const HEIGHT = 960;
const W = WIDTH, H = HEIGHT;
const C = {
  base: '#0d1b23', block: '#122832', line: '#385e64', faint: '#7faaa9', white: '#eff9e8',
  mint: '#9df2c5', deep: '#384c4f', amber: '#ffd088', red: '#ff7d76',
};
const dialogue = [
  ['Так, в кадре склад.', 'Теперь площадка. А вот и офис.'],
  ['Стоп, что это за звук?', 'Это часть уровня?'],
  ['А, всё. Конец игры.'],
];
const clamp = (x) => Math.max(0, Math.min(1, x));
const ease = (x) => 1 - (1 - clamp(x)) ** 3;
const sCurve = (x) => clamp(x) ** 2 * (3 - 2 * clamp(x));
const hash = (n) => ((Math.imul(n + 131, 1208211839) >>> 0) % 1049) / 1049;
const blend = (a, b, t) => a + (b - a) * t;
let fontReady = false;
function registerFonts() {
  if (fontReady) return;
  for (const face of ['Black', 'Medium']) {
    const url = new URL(`../../fonts/Roboto-${face}.woff`, import.meta.url);
    if (!GlobalFonts.registerFromPath(fileURLToPath(url), `Arcade${face}`)) throw new Error(`Шрифт не загружен: ${face}`);
  }
  fontReady = true;
}
function fill(ctx, x, y, w, h, color) { ctx.fillStyle = color; ctx.fillRect(x, y, w, h); }
function rule(ctx, points, stroke, lw = 1) {
  ctx.beginPath(); ctx.moveTo(...points[0]);
  points.slice(1).forEach((p) => ctx.lineTo(...p));
  ctx.strokeStyle = stroke; ctx.lineWidth = lw; ctx.stroke();
}
function shape(ctx, points, color, stroke, lw = 1) {
  ctx.beginPath(); ctx.moveTo(...points[0]);
  points.slice(1).forEach((p) => ctx.lineTo(...p));
  ctx.closePath(); ctx.fillStyle = color; ctx.fill();
  if (stroke) { ctx.strokeStyle = stroke; ctx.lineWidth = lw; ctx.stroke(); }
}
function tile(ctx, x, y, w, h, cut, color, stroke) {
  shape(ctx, [[x, y], [x + w - cut, y], [x + w, y + cut], [x + w, y + h],
    [x + cut, y + h], [x, y + h - cut]], color, stroke);
}
function txt(ctx, word, x, y, size, color, options = {}) {
  ctx.font = `${size}px Arcade${options.medium ? 'Medium' : 'Black'}`;
  ctx.textAlign = options.align || 'left'; ctx.textBaseline = 'alphabetic'; ctx.fillStyle = color;
  if (!options.track) { ctx.fillText(word, x, y); return; }
  const chars = [...word];
  const widths = chars.map((ch) => ctx.measureText(ch).width + options.track);
  const width = widths.reduce((a, b) => a + b, -options.track);
  if (options.align === 'center') x -= width / 2;
  if (options.align === 'right') x -= width;
  ctx.textAlign = 'left';
  chars.forEach((ch, i) => { ctx.fillText(ch, x, y); x += widths[i]; });
}
function circle(ctx, x, y, r, fillColor, stroke, line = 1) {
  ctx.beginPath(); ctx.arc(x, y, r, 0, 2 * Math.PI);
  if (fillColor) { ctx.fillStyle = fillColor; ctx.fill(); }
  if (stroke) { ctx.strokeStyle = stroke; ctx.lineWidth = line; ctx.stroke(); }
}
function chip(ctx, label, x, y, width, color, bg = C.block) {
  tile(ctx, x, y, width, 29, 6, bg, color);
  txt(ctx, label, x + 10, y + 19, 11, color, { track: 1.4 });
}
function screenBase(ctx, color = C.base) {
  fill(ctx, 0, 0, W, H, color);
  for (let y = 29; y < H; y += 22) {
    for (let x = 19; x < W; x += 23) fill(ctx, x, y, 1, 1, '#81baad28');
  }
}
function rail(ctx, index, title, accent = C.mint) {
  fill(ctx, 37, 48, 5, 15, accent);
  fill(ctx, 44, 48, 2, 15, accent);
  txt(ctx, title, 55, 60, 12, accent, { track: 1.8 });
  txt(ctx, `02 / 0${index}`, 504, 60, 12, C.faint, { align: 'right', track: 2 });
  rule(ctx, [[36, 80], [503, 80]], C.line, 1);
}
function frame(ctx, x, y, w, h, color) {
  for (const [sx, sy] of [[1, 1], [1, -1], [-1, 1], [-1, -1]]) {
    const xx = sx > 0 ? x : x + w, yy = sy > 0 ? y : y + h;
    rule(ctx, [[xx, yy + sy * 21], [xx, yy], [xx + sx * 25, yy]], color, 2);
  }
}
function footer(ctx, time, label, accent = C.mint) {
  fill(ctx, 36, 904, 467, 1, C.line);
  fill(ctx, 36, 904, Math.min(467, 467 * time / DURATION), 1.6, accent);
  txt(ctx, label, 37, 928, 11, C.faint, { track: 1.8 });
  const ss = String(Math.floor(time)).padStart(2, '0');
  const frame = String(Math.floor((time - Math.floor(time)) * 30 + 1e-8)).padStart(2, '0');
  txt(ctx, `00:${ss}:${frame}`, 503, 928, 11, C.faint, { align: 'right', track: 1.1 });
}
function voiceBox(ctx, title, lines, accent = C.mint) {
  tile(ctx, 36, 789, 468, 92, 9, '#12262f', '#355058');
  fill(ctx, 36, 805, 3, 45, accent);
  txt(ctx, title, 54, 810, 11, accent, { track: 1.7 });
  lines.forEach((line, i) => txt(ctx, line, 54, 836 + i * 23, 18, C.white, { medium: true }));
}
function tabs(ctx, labels, index, y) {
  labels.forEach((site, i) => {
    const x = 36 + i * 158, selected = index === i;
    fill(ctx, x, y, 152, 44, selected ? '#294640' : '#172d36');
    fill(ctx, x, y, 152, selected ? 2 : 1, selected ? C.mint : C.line);
    txt(ctx, site.id, x + 9, y + 25, 11, selected ? C.mint : C.faint, { track: .6 });
    txt(ctx, site.map, x + 34, y + 26, 12, selected ? C.white : C.faint, { track: .8 });
  });
}
function cameraMotion(shot, local, early) {
  const v = local - .7;
  return {
    ...shot,
    x: shot.x + 6.2 * v,
    y: shot.y - 3.1 * v,
    yaw: shot.yaw + .06 * v,
    zoom: shot.zoom + .12 * v + (early ? 0 : .25),
  };
}
function windowView(ctx, cam, t, bounds, morning) {
  const [x, y, w, h] = bounds;
  ctx.save(); ctx.beginPath(); ctx.rect(x, y, w, h); ctx.clip();
  renderWorld(ctx, cam, t, morning);
  const shade = ctx.createLinearGradient(0, y, 0, y + h);
  shade.addColorStop(0, '#08162077'); shade.addColorStop(.24, '#08162000');
  shade.addColorStop(.77, '#08162000'); shade.addColorStop(1, '#081620a5');
  fill(ctx, x, y, w, h, shade);
  if (!morning) {
    for (let py = y; py < y + h; py += 5) fill(ctx, x, py, w, 1, '#94ffe012');
  }
  ctx.restore();
}
function povWindow(ctx, t, index, fragment = false) {
  const scene = POV_SHOTS[index];
  const local = Math.min(2.5, t - scene.start);
  const cam = cameraMotion(CAMERAS[scene.id], local, true);
  const [x, y, w, h] = [36, 174, 468, 538];
  windowView(ctx, cam, t, [x, y, w, h], false);
  if (fragment) return;
  frame(ctx, x, y, w, h, C.mint);
  chip(ctx, 'ИГРОВАЯ КАМЕРА', x + 12, y + 12, 149, C.mint, '#10252dea');
  fill(ctx, x + w - 78, y + 13, 66, 28, '#152932db');
  circle(ctx, x + w - 65, y + 27, 3.2, t % 1 < .75 ? C.red : C.line);
  txt(ctx, 'POV', x + w - 53, y + 31, 11, C.white, { track: 1.5 });
  const ruler = 178;
  for (let i = 0; i < 19; i++) {
    const px = ruler + i * 10;
    fill(ctx, px, y + h - 26, 1, i % 3 ? 4 : 8, i === 9 ? C.mint : C.faint);
  }
  txt(ctx, `${scene.id} / КАДР`, x + 13, y + h - 16, 11, C.mint, { track: 1.4 });
  for (let i = 0; i <= 4; i++) {
    const bh = 4 + 3 * i;
    fill(ctx, x + w - 42 + 6 * i, y + h - 16 - bh, 3, bh,
      i < 3 + Math.round(Math.sin(t * 4) / 2) ? C.mint : C.line);
  }
  const flash = .16 * (1 - ease(local / .23));
  fill(ctx, x, y, w, h, `rgba(157,242,197,${flash})`);
}
function camera(ctx, t) {
  const index = POV_SHOTS.findLastIndex(({ start }) => t >= start);
  screenBase(ctx);
  rail(ctx, 1, 'В ОКОПЕ  /  ИГРОВАЯ СЦЕНА');
  txt(ctx, 'Режим POV', 35, 137, 52, C.white);
  chip(ctx, 'ПРОМЗОНА', 389, 107, 114, C.faint);
  povWindow(ctx, t, index);
  tabs(ctx, POV_SHOTS, index, 728);
  voiceBox(ctx, 'ГОЛОС ИЗ ИГРЫ', dialogue[0]);
  footer(ctx, t, 'КАМЕРА / ОБЗОР');
}
function splitPixels(ctx, t, level, tint = false) {
  const key = Math.floor(t * 11);
  const colors = tint ? [C.red, C.amber, '#c95362', '#342638', '#ff9c8b'] :
    [C.mint, '#398587', '#375664', '#1a3f4a', C.amber];
  ctx.save(); ctx.globalAlpha *= .59 * level;
  for (let i = 0; i < 61; i++) {
    const n = key * 67 + i * 3;
    const x = 36 + 7 * Math.floor(hash(n) * 61);
    const y = 168 + 7 * Math.floor(hash(n + 1) * 76);
    fill(ctx, x, y, 7 + 7 * Math.floor(hash(n + 2) * 8), i % 6 ? 7 : 14, colors[i % colors.length]);
  }
  for (let i = 0; i < 9; i++) {
    fill(ctx, 36, 202 + hash(key * 11 + i + 51) * 465, 468, 2 + i % 3, colors[i % colors.length]);
  }
  ctx.restore();
}
function soundIcon(ctx, x, y, amount) {
  circle(ctx, x, y, 48, '#18282f', C.red, 1.5);
  shape(ctx, [[x - 23, y - 9], [x - 10, y - 9], [x + 5, y - 21], [x + 5, y + 21],
    [x - 10, y + 9], [x - 23, y + 9]], C.amber);
  for (let i = 0; i < 2; i++) {
    ctx.save(); ctx.globalAlpha *= (.50 + .50 * amount) * (1 - .20 * i);
    ctx.beginPath(); ctx.arc(x + 2, y, 14 + 8 * i, -.88, .88);
    ctx.strokeStyle = C.amber; ctx.lineWidth = 3; ctx.stroke();
    ctx.restore();
  }
  if (amount > 0) circle(ctx, x, y, 50 + 14 * (1 - amount), null, `rgba(255,125,118,${amount * .55})`, 2);
}
function gameEnd(ctx, t) {
  const over = t >= GAME_OVER_AT;
  const cue = t - BEEP_AT;
  const flip = sCurve((t - 6.08) / .46);
  screenBase(ctx, over ? '#191925' : C.base);
  rail(ctx, 2, 'АРКАДА  /  СМЕНА СЦЕНЫ', C.red);
  txt(ctx, 'Сигнал', 35, 137, 52, C.white);
  chip(ctx, 'ИГРОВАЯ СЦЕНА', 340, 106, 164, C.red, '#30272e');
  if (!over) {
    ctx.save(); ctx.globalAlpha *= 1 - flip * .74;
    povWindow(ctx, t, 2, true);
    ctx.restore();
    fill(ctx, 36, 174, 468, 538, `rgba(21,23,32,${.37 + .46 * flip})`);
    splitPixels(ctx, t, cue < .3 ? .9 - .45 * flip : .14, true);
    if (cue >= 0) {
      const enter = ease(cue / .25);
      ctx.save(); ctx.globalAlpha *= enter;
      soundIcon(ctx, 270, 306, 1 - ease(cue / .66));
      txt(ctx, 'ДРОН', 270, 453, 77, C.white, { align: 'center' });
      txt(ctx, 'ЗАМЕЧЕН', 270, 527, 74, C.red, { align: 'center' });
      txt(ctx, 'КОРОТКИЙ ЗВУКОВОЙ СИГНАЛ', 270, 574, 13, C.red, { align: 'center', track: 2.0 });
      ctx.restore();
    }
  } else {
    const local = t - GAME_OVER_AT;
    tile(ctx, 36, 174, 468, 538, 22, '#272734');
    splitPixels(ctx, t, Math.max(.14, .89 * (1 - ease(local / .5))), true);
    const pulse = ease(local / .20);
    ctx.save(); ctx.translate(0, 9 * (1 - pulse));
    txt(ctx, 'GAME', 270 + (1 - pulse) * 15, 380, 128, C.white, { align: 'center' });
    txt(ctx, 'OVER', 270 - (1 - pulse) * 15, 500, 133, C.amber, { align: 'center' });
    rule(ctx, [[129, 548], [410, 548]], '#a26b6c');
    txt(ctx, 'КОНЕЦ ИГРОВОГО УРОВНЯ', 270, 585, 14, C.red, { align: 'center', track: 2.4 });
    ctx.restore();
  }
  frame(ctx, 36, 174, 468, 538, C.red);
  const revealed = over ? 'УРОВЕНЬ ЗАВЕРШЁН' : cue >= 0 ? 'ЗВУКОВОЙ СИГНАЛ' : 'СМЕНА СЦЕНЫ';
  chip(ctx, revealed, 36, 734, 223, C.red, '#30272e');
  voiceBox(ctx, 'ГОЛОС ИЗ ИГРЫ', dialogue[over ? 2 : 1], C.red);
  footer(ctx, t, 'АРКАДА / УРОВЕНЬ 02', C.red);
}
function panorama(ctx, t) {
  const local = t - 13;
  const arc = sCurve(local / 9.0);
  const cam = {
    ...PANORAMA, x: blend(-4, 10, arc), y: blend(5, -2, arc),
    yaw: blend(-.43, .20, arc), zoom: blend(2.02, 1.84, arc), yAt: 462, horizonY: 303,
  };
  screenBase(ctx, '#14282f');
  rail(ctx, 3, 'ВНЕ ИГРЫ  /  НАБЛЮДЕНИЕ');
  txt(ctx, 'Заметить', 34, 148, 68, C.white);
  txt(ctx, 'вовремя.', 34, 214, 70, C.mint);
  windowView(ctx, cam, t, [36, 247, 468, 436], true);
  frame(ctx, 36, 247, 468, 436, C.amber);
  chip(ctx, 'ПРОМЗОНА', 49, 261, 108, C.amber, '#263932ed');
  if (local < .25) fill(ctx, 36, 247, 468, 436, `rgba(255,228,171,${.42 * (1 - ease(local / .25))})`);
  tabs(ctx, POV_SHOTS, -1, 704);
  voiceBox(ctx, 'ДЕТЕКТОР', ['Заметить дрон на подлёте.', 'Подать звуковой сигнал на месте.']);
  footer(ctx, t, 'НАБЛЮДЕНИЕ / ПРОМЗОНА');
}
function details(ctx, t) {
  const index = SITE_SHOTS.findLastIndex(({ start }) => t >= start);
  const item = SITE_SHOTS[index];
  const local = t - item.start;
  screenBase(ctx);
  rail(ctx, 4, 'ОБЪЕКТЫ  /  ОБЗОР');
  txt(ctx, item.name, 35, 146, item.id === '02' ? 63 : 75, C.white);
  const cam = cameraMotion(CAMERAS[item.id], local + .38, false);
  windowView(ctx, cam, t, [36, 190, 468, 475], true);
  frame(ctx, 36, 190, 468, 475, C.amber);
  chip(ctx, `ПЛАН ${item.id}`, 49, 204, 105, C.amber, '#293931dd');
  const flash = .27 * (1 - ease(local / .19));
  fill(ctx, 36, 190, 468, 475, `rgba(255,232,169,${flash})`);
  tabs(ctx, SITE_SHOTS, index, 690);
  voiceBox(ctx, 'МАГАЗИН «В ОКОПЕ»', ['Детекторы дронов.']);
  footer(ctx, t, 'ОФИС / СКЛАД / ПЛОЩАДКА');
}

export const QR_Y = 646;
export const QR_X = [113, 270, 427];
const qr = CONTACTS.map(({ href }) => QRCode.create(href, { errorCorrectionLevel: 'M' }).modules);
function contact(ctx, i) {
  const x = QR_X[i], matrix = qr[i];
  const step = Math.floor(104 / (matrix.size + 8));
  const side = step * (matrix.size + 8), left = Math.round(x - side / 2);
  tile(ctx, x - 70, QR_Y - 11, 140, 160, 9, '#162d36', '#68908a');
  fill(ctx, left, QR_Y, side, side, '#fcffee');
  for (let r = 0; r < matrix.size; r++) for (let c = 0; c < matrix.size; c++) {
    if (matrix.get(r, c)) fill(ctx, left + (c + 4) * step, QR_Y + (r + 4) * step, step, step, '#11262c');
  }
  txt(ctx, CONTACTS[i].label, x, QR_Y + 121, 15, C.white, { align: 'center' });
  txt(ctx, CONTACTS[i].handle, x, QR_Y + 139, 12, C.mint, { align: 'center', medium: true });
}
function endCard(ctx, t) {
  const p = ease((t - 25) / .39);
  screenBase(ctx);
  rail(ctx, 5, 'ВЫХОД  /  МАГАЗИН');
  ctx.save(); ctx.translate(0, 14 * (1 - p));
  tile(ctx, 39, 150, 462, 175, 28, '#244e46', '#557e70');
  tile(ctx, 33, 143, 462, 175, 28, C.mint);
  fill(ctx, 57, 160, 117, 2, '#4a7b6c');
  for (let i = 0; i < 6; i++) fill(ctx, 427 + 7 * i, 295, 3, 8, '#4a7b6c');
  txt(ctx, 'МАГАЗИН', 266, 200, 18, '#254b44', { align: 'center', track: 5 });
  txt(ctx, 'В ОКОПЕ', 266, 280, 79, C.base, { align: 'center' });
  ctx.restore();
  const dot = SLOGAN.indexOf('.') + 1;
  txt(ctx, SLOGAN.slice(0, dot), 36, 435, 47, C.white);
  txt(ctx, SLOGAN.slice(dot + 1), 35, 507, 56, C.amber);
  chip(ctx, 'ДЕТЕКТОРЫ ДРОНОВ', 37, 553, 200, C.mint);
  rule(ctx, [[37, 603], [503, 603]], C.line);
  CONTACTS.forEach((_, i) => contact(ctx, i));
  footer(ctx, t, 'КОНТАКТЫ / 03');
}

const scenes = [camera, gameEnd, panorama, details, endCard];
export function createFilm(scale = 2) {
  registerFonts();
  const canvas = createCanvas(W * scale, H * scale);
  const ctx = canvas.getContext('2d');
  return {
    canvas, draw(time) {
      const t = Math.min(DURATION, Math.max(0, time));
      const i = chapterAt(t);
      ctx.setTransform(scale, 0, 0, scale, 0, 0);
      ctx.lineCap = 'butt'; ctx.lineJoin = 'round';
      scenes[i](ctx, t);
      // A short single-layer scan on hard cuts, not a strobe.
      const dt = t - CHAPTERS[i].start;
      if (i > 1 && dt < .23) {
        ctx.save(); ctx.globalAlpha *= (1 - ease(dt / .23)) * .24;
        fill(ctx, 0, 0, W, 9, C.mint);
        fill(ctx, 0, H - 14, W, 6, C.mint);
        ctx.restore();
      }
      return canvas;
    },
  };
}
