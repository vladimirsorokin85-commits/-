import { createCanvas, GlobalFonts, loadImage } from '@napi-rs/canvas';
import { fileURLToPath } from 'node:url';
import QRCode from 'qrcode';
import { BEEP_AT, CHAPTERS, CONTACTS, DURATION, SITES, SLOGAN, chapterAt } from './story.mjs';
import { P, device, ease, ellipse, fill, line, path, rounded, siteArt, type } from './art.mjs';

export const WIDTH = 540;
export const HEIGHT = 960;
const W = WIDTH, H = HEIGHT;
const logo = await loadImage(fileURLToPath(new URL('./assets/v-okope-white.png', import.meta.url)));
let fontReady = false;
function fonts() {
  if (fontReady) return;
  for (const face of ['Black', 'Medium']) {
    const file = fileURLToPath(new URL(`../../fonts/Roboto-${face}.woff`, import.meta.url));
    if (!GlobalFonts.registerFromPath(file, `Bulat${face}`)) throw new Error(`Шрифт не загружен: ${face}`);
  }
  fontReady = true;
}
function stamp(ctx, value, x, y, w, bg, color) {
  rounded(ctx, bg, x, y, w, 29, 4);
  type(ctx, value, x + 10, y + 19, 11, color, { tracking: 1.45 });
}
function star(ctx, x, y, r, color) {
  path(ctx, [[x, y - r], [x + r * .19, y - r * .23], [x + r * .71, y], [x + r * .21, y + r * .19],
    [x, y + r], [x - r * .20, y + r * .19], [x - r * .71, y], [x - r * .21, y - r * .22]], color);
}
function base(ctx, i, label, bg = '#ede8d4', dark = false) {
  fill(ctx, bg, 0, 0, W, H);
  for (let y = 61; y < H; y += 24) for (let x = 18; x < W; x += 27) fill(ctx, dark ? '#b7cbbc2b' : '#24473d18', x, y, 1, 1);
  const color = dark ? P.mint : P.deep;
  fill(ctx, dark ? P.warm : P.teal, 37, 47, 5, 15);
  type(ctx, label, 51, 59, 12, color, { tracking: 1.8 });
  type(ctx, `0${i} / 05`, 502, 59, 12, color, { align: 'right', tracking: 1 });
  line(ctx, 37, 77, 466, dark ? '#73968b' : '#829d8c');
}
function headline(ctx, a, b, bg = P.dark, color = P.teal, first = 72, second = 72) {
  type(ctx, a, 36, 150, first, bg);
  type(ctx, b, 36, 219, second, color);
}
function footer(ctx, t, label, dark = false) {
  const ink = dark ? P.mint : P.teal;
  line(ctx, 37, 901, 466, dark ? '#547b72' : '#9ba996');
  line(ctx, 37, 901, 466 * t / DURATION, ink, 2);
  type(ctx, label, 37, 927, 10, ink, { tracking: 1.65 });
  type(ctx, `00:${String(Math.min(30, Math.floor(t))).padStart(2, '0')}`, 503, 927, 10, ink, { align: 'right', tracking: 1 });
}
function copy(ctx, key, lines, dark = false) {
  rounded(ctx, dark ? '#214b49' : '#dee5ce', 37, 768, 466, 101, 8, dark ? '#608b80' : '#a8b8a3');
  fill(ctx, dark ? P.warm : P.teal, 37, 788, 3, 53);
  type(ctx, key, 54, 790, 10, dark ? P.warm : P.teal, { tracking: 1.8 });
  lines.forEach((lineText, i) => type(ctx, lineText, 54, 819 + i * 25, 19, dark ? P.cream : P.dark, { medium: true }));
}
function glass(ctx, x, y, w, h, dark = false) {
  const gradient = ctx.createLinearGradient(x, y, x + w, y + h);
  gradient.addColorStop(0, dark ? '#47746b' : '#c9dbc0');
  gradient.addColorStop(.52, dark ? '#36605b' : '#a6ccba');
  gradient.addColorStop(1, dark ? '#2c5451' : '#8bb7aa');
  rounded(ctx, gradient, x, y, w, h, 12, dark ? '#719389' : '#789d90');
}
function hatch(ctx, x, y, w, rows, ink) {
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < 7; c++) fill(ctx, ink, x + c * w / 7 + r * .75, y + r * 7, 2 + (c + r) % 3, 1);
  }
}
function medallion(ctx, x, y, rx, ry, color, outline) {
  ellipse(ctx, color, x, y, rx, ry);
  ellipse(ctx, null, x, y, rx + 8, ry + 7, outline, 1);
  ellipse(ctx, null, x, y, rx + 24, ry + 19, outline, 1.25);
}
function productPlate(ctx, local, reverse = false) {
  glass(ctx, 37, 251, 466, 482);
  const amount = ease(local / .57);
  const cx = reverse ? 378 : 163;
  const detailX = reverse ? 55 : 280;
  const roll = (reverse ? .031 : -.035) + .017 * Math.sin(local * 1.45);
  medallion(ctx, cx, 509, 81, 167, '#c7dabe', '#7fb1a1');
  type(ctx, 'ВИД ЦЕЛИКОМ', reverse ? 324 : 109, 269, 11, P.deep, { tracking: 1.45 });
  hatch(ctx, cx - 94, 519, 16, 6, '#75a493');
  ellipse(ctx, '#2a615748', cx + 3, 685, 64, 12);
  device(ctx, cx, 614 + 4.2 * Math.sin(local * 1.27) + 13 * (1 - amount), .638, roll, reverse ? .5 : 0);
  const insetY = 320 + 10 * (1 - amount);
  const insetW = 201, insetH = 357;
  rounded(ctx, '#486b6244', detailX + 5, insetY + 6, insetW, insetH, 9);
  rounded(ctx, '#dbe5c7', detailX, insetY, insetW, insetH, 9, '#72998a');
  type(ctx, 'КОРПУС', detailX + 15, insetY + 23, 11, P.deep, { tracking: 1.3 });
  type(ctx, 'КРУПНЫЙ ПЛАН', detailX + insetW - 12, insetY + 23, 9.5, '#4c796c', { align: 'right', tracking: 1.1 });
  ctx.save();
  ctx.beginPath(); ctx.rect(detailX + 8, insetY + 36, insetW - 16, insetH - 45); ctx.clip();
  fill(ctx, '#b3cbb2', detailX + 8, insetY + 36, insetW - 16, insetH - 45);
  hatch(ctx, detailX + 20, insetY + 62, 147, 4, '#93ae99');
  device(ctx, detailX + 99, insetY + 208 + 2.6 * Math.sin(local * 1.4), 1.18, roll * .49, reverse ? .5 : 0);
  ctx.restore();
  star(ctx, reverse ? 462 : 239, 317, 12 * amount, '#ffdfa6');
  stamp(ctx, 'РИСУНОК ПО ФОТО', 54, 695, 164, '#365f57', P.cream);
}
function hero(ctx, t) {
  base(ctx, 1, 'БУЛАТ V4 / УСТРОЙСТВО');
  type(ctx, 'Булат', 34, 157, 106, P.dark);
  rounded(ctx, P.deep, 350, 99, 121, 61, 8);
  type(ctx, 'v4', 409, 141, 40, P.cream, { align: 'center' });
  type(ctx, 'Детектор дронов', 38, 217, 43, P.teal);
  productPlate(ctx, t);
  copy(ctx, 'НАЗНАЧЕНИЕ', ['Переносной прибор', 'для обнаружения дронов.']);
  footer(ctx, t, 'ОБНАРУЖЕНИЕ / ВВЕДЕНИЕ');
}
function speakerIcon(ctx, x, y, scale, color, wave) {
  ctx.save(); ctx.translate(x, y); ctx.scale(scale, scale);
  path(ctx, [[-47, -14], [-25, -14], [2, -37], [2, 38], [-25, 14], [-47, 14]], color);
  for (let r = 1; r <= 2; r++) {
    ctx.beginPath(); ctx.arc(3, 0, r * 18 + 16, -.76, .76);
    ctx.lineWidth = 4.3 + wave; ctx.strokeStyle = color; ctx.stroke();
  }
  ctx.restore();
}
function dronePictogram(ctx, x, y, tint) {
  ctx.save(); ctx.translate(x, y);
  path(ctx, [[-22, -9], [0, 3], [22, -9]], null, tint, 2.4);
  path(ctx, [[-22, 12], [0, 0], [22, 12]], null, tint, 2.4);
  rounded(ctx, tint, -9, -7, 18, 14, 4);
  for (const [sx, sy] of [[-21, -9], [21, -9], [-21, 12], [21, 12]]) {
    ellipse(ctx, null, sx, sy, 8, 3.7, tint, 1.4);
  }
  ctx.restore();
}
function alert(ctx, t) {
  const elapsed = t - BEEP_AT;
  const active = elapsed >= 0;
  const pulse = (1 - ease(elapsed / .76)) * (active ? 1 : 0);
  base(ctx, 2, 'БУЛАТ V4 / ПРЕДУПРЕЖДЕНИЕ', '#1e4141', true);
  headline(ctx, 'Сигнал', 'на месте.', P.cream, P.warm);
  glass(ctx, 37, 251, 466, 482, true);
  const aura = active ? '#d8b982' : '#8ab4a4';
  medallion(ctx, 269, 452, 109 + pulse * 8, 109 + pulse * 8, active ? '#739585' : '#5c897e', '#9dbaa5');
  if (active && elapsed < 1.0) {
    const r = 104 + 45 * ease(elapsed / .8);
    ellipse(ctx, null, 269, 452, r, r, `rgba(255,212,134,${pulse * .82})`, 3);
  }
  ctx.save(); ctx.globalAlpha *= active ? 1 : .64;
  speakerIcon(ctx, 269, 449, 1.36 + pulse * .055, active ? '#fee2a7' : '#d0e2c5', pulse);
  ctx.restore();
  dronePictogram(ctx, 429, 325 + 3 * Math.sin(t * 1.7), aura);
  hatch(ctx, 64, 350, 83, 7, '#79a095'); hatch(ctx, 406, 566, 66, 5, '#739d8e');
  stamp(ctx, 'ИЛЛЮСТРАЦИЯ СИГНАЛА', 56, 271, 181, '#244b4a', P.cream);
  rounded(ctx, '#254b48', 58, 619, 423, 81, 6, aura);
  ellipse(ctx, aura, 83, 659, 6.2, 6.2);
  type(ctx, active ? 'Дрон замечен' : 'Наблюдение', 105, 675, 42, active ? P.warm : '#d5e2ca');
  copy(ctx, 'ЧТО ПРОИСХОДИТ', ['Детектор подаёт звуковой сигнал.', 'Он предупреждает, а не глушит связь.'], true);
  footer(ctx, t, 'МЕСТНЫЙ ЗВУКОВОЙ СИГНАЛ', true);
}
function miniCards(ctx, t) {
  SITES.forEach((site, i) => {
    const y = 254 + 158 * i;
    const local = t - CHAPTERS[2].start;
    const enter = ease((local - i * .11) / .31);
    ctx.save(); ctx.translate(19 * (1 - enter), 0);
    rounded(ctx, i % 2 ? '#dedfc4' : '#d6e6d1', 37, y, 466, 143, 8, '#9fb19a');
    siteArt(ctx, i, 1.1 + local * .24, 46, y + 9, 166, 125);
    type(ctx, `0${i + 1} / СРЕДА`, 228, y + 38, 10, P.teal, { tracking: 1.45 });
    type(ctx, site.name, 228, y + 79, i === 2 ? 26 : 31, P.dark);
    line(ctx, 228, y + 112, 218, '#afbaa2');
    ctx.restore();
  });
}
function siteDetail(ctx, t, index) {
  const site = SITES[index];
  const local = t - site.start;
  const flash = .28 * (1 - ease(local / .17));
  const x = 38, y = 254, w = 464, h = 390;
  siteArt(ctx, index, .24 + local * 1.12, x, y, w, h);
  rounded(ctx, null, x, y, w, h, 0, '#83a794', 1.8);
  fill(ctx, `rgba(255,232,183,${flash})`, x, y, w, h);
  stamp(ctx, `ПЛАН / 0${index + 1}`, x + 13, y + 13, 105, '#365f57', P.cream);
  rounded(ctx, '#dfe5cb', 38, 644, 464, 85, 0, '#a1b7a1');
  type(ctx, site.name, 53, 683, index === 2 ? 37 : 44, P.dark);
  type(ctx, site.setting, 54, 708, 14, P.teal, { medium: true });
}
function civic(ctx, t) {
  const index = SITES.findLastIndex(({ start }) => t >= start);
  base(ctx, 3, 'БУЛАТ V4 / ГРАЖДАНСКИЕ ОБЪЕКТЫ', '#f1ead4');
  headline(ctx, 'Гражданские', 'задачи.', P.dark, P.teal, 65, 76);
  if (index < 0) miniCards(ctx, t);
  else siteDetail(ctx, t, index);
  copy(ctx, 'ПРИМЕРЫ', ['Склад, стройплощадка', 'или выездная бригада.']);
  footer(ctx, t, 'ПРИМЕРЫ ГРАЖДАНСКОГО ПРИМЕНЕНИЯ');
}
function recap(ctx, t) {
  const local = t - CHAPTERS[3].start;
  base(ctx, 4, 'БУЛАТ V4 / ГЛАВНОЕ', '#d6e3ca');
  headline(ctx, 'Заметить', 'вовремя.', P.dark, P.teal, 74, 80);
  productPlate(ctx, local, true);
  copy(ctx, 'КРАТКО', ['Замечает и предупреждает.', 'Не предназначен для подавления.']);
  footer(ctx, t, 'БУЛАТ V4 / ОБНАРУЖЕНИЕ И СИГНАЛ');
}

export const QR_X = [113, 270, 427];
export const QR_Y = 650;
const matrices = CONTACTS.map(({ href }) => QRCode.create(href, { errorCorrectionLevel: 'M' }).modules);
function contact(ctx, i) {
  const x = QR_X[i];
  const m = matrices[i];
  const step = Math.floor(106 / (m.size + 8));
  const size = step * (m.size + 8), left = Math.round(x - size / 2);
  rounded(ctx, '#274b49', x - 70, QR_Y - 11, 140, 156, 7, '#689089');
  fill(ctx, '#fffef0', left, QR_Y, size, size);
  for (let r = 0; r < m.size; r++) for (let c = 0; c < m.size; c++) {
    if (m.get(r, c)) fill(ctx, '#122e2d', left + (c + 4) * step, QR_Y + (r + 4) * step, step, step);
  }
  type(ctx, CONTACTS[i].label, x, QR_Y + 122, 14, P.cream, { align: 'center' });
  type(ctx, CONTACTS[i].handle, x, QR_Y + 138, 11, P.mint, { align: 'center', medium: true });
}
function finale(ctx, t) {
  const local = t - CHAPTERS[4].start;
  base(ctx, 5, 'В ОКОПЕ / КОНТАКТЫ', '#183b3c', true);
  const enter = ease(local / .48);
  rounded(ctx, '#204746', 38, 101, 464, 308, 10, '#567d75');
  ctx.save(); ctx.translate(0, (1 - enter) * 13);
  // Trim only transparent margins; preserve the artwork in the supplied white PNG.
  const src = [344, 202, 1016, 918], width = 310;
  const height = width * src[3] / src[2];
  ctx.drawImage(logo, ...src, (W - width) / 2, 113, width, height);
  ctx.restore();
  star(ctx, 445, 142, 13 * enter, P.warm);
  const stop = SLOGAN.indexOf('.') + 1;
  type(ctx, SLOGAN.slice(0, stop), 36, 499, 47, P.cream);
  type(ctx, SLOGAN.slice(stop + 1), 36, 572, 56, P.warm);
  line(ctx, 37, 619, 466, '#70968a');
  CONTACTS.forEach((_, i) => contact(ctx, i));
  footer(ctx, t, 'МАГАЗИН / 03 КОНТАКТА', true);
}

function grain() {
  const tile = createCanvas(137, 149), ctx = tile.getContext('2d');
  const image = ctx.createImageData(tile.width, tile.height);
  let seed = 1941;
  for (let i = 0; i < image.data.length; i += 4) {
    seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0;
    const light = seed >>> 31;
    image.data[i] = light ? 255 : 17;
    image.data[i + 1] = light ? 247 : 34;
    image.data[i + 2] = light ? 215 : 36;
    image.data[i + 3] = (seed >>> 23) % 27;
  }
  ctx.putImageData(image, 0, 0);
  return tile;
}

const scenes = [hero, alert, civic, recap, finale];
export function createFilm(scale = 2) {
  fonts();
  const canvas = createCanvas(W * scale, H * scale), ctx = canvas.getContext('2d');
  const pattern = ctx.createPattern(grain(), 'repeat');
  return {
    canvas, draw(time) {
      const t = Math.min(DURATION, Math.max(0, time));
      const i = chapterAt(t);
      ctx.setTransform(scale, 0, 0, scale, 0, 0);
      ctx.lineJoin = 'round'; ctx.lineCap = 'round';
      scenes[i](ctx, t);
      ctx.save(); ctx.globalAlpha *= .47; fill(ctx, pattern, 0, 0, W, H); ctx.restore();
      const local = t - CHAPTERS[i].start;
      if (i > 0 && local < .18) {
        fill(ctx, P.warm, 37, 78, 466 * (1 - ease(local / .18)), 3);
      }
      return canvas;
    },
  };
}
