import { createCanvas, GlobalFonts, loadImage } from '@napi-rs/canvas';
import { fileURLToPath } from 'node:url';
import { DURATION, PHYSICAL, SHOTS, WIPE } from './story.mjs';

export const WIDTH = 540;
export const HEIGHT = 960;
const W = WIDTH, H = HEIGHT;
const PAPER = '#f3ebd7';
const BLUE = '#183b9b';
const INK = '#1b2d5e';
const RED = '#cd3c29';
const files = { face: 'face.png', lid: 'case.jpg', label: 'label.jpg', tray: 'tray.jpg', passport: 'passport.jpg' };
const assets = Object.fromEntries(await Promise.all(Object.entries(files).map(async ([key, file]) => [
  key, await loadImage(fileURLToPath(new URL(`./assets/${file}`, import.meta.url))),
])));
for (const face of ['Black', 'Medium']) {
  const path = fileURLToPath(new URL(`../../fonts/Roboto-${face}.woff`, import.meta.url));
  if (!GlobalFonts.registerFromPath(path, `Incubator${face}`)) throw new Error(`Не загружен шрифт: ${face}`);
}

const bound = (n, min, max) => Math.max(min, Math.min(max, n));
const ease = (t) => { const x = bound(t, 0, 1); return x * x * (3 - 2 * x); };
const drift = (t, seconds = 4) => ease(t / seconds);
function rect(ctx, color, x = 0, y = 0, w = W, h = H) {
  ctx.fillStyle = color;
  ctx.fillRect(x, y, w, h);
}
function path(ctx, points) {
  ctx.beginPath();
  ctx.moveTo(...points[0]);
  for (const point of points.slice(1)) ctx.lineTo(...point);
  ctx.closePath();
}
function print(ctx, points, color) {
  path(ctx, points);
  ctx.fillStyle = color;
  ctx.fill();
}
function clipped(ctx, points, paint) {
  ctx.save();
  path(ctx, points);
  ctx.clip();
  paint();
  ctx.restore();
}
function text(ctx, label, x, y, size, color, max = 446, face = 'Black') {
  ctx.save();
  ctx.font = `${size}px Incubator${face}`;
  ctx.textBaseline = 'alphabetic';
  ctx.translate(x, y);
  ctx.scale(Math.min(1, max / ctx.measureText(label).width), 1);
  ctx.fillStyle = color;
  ctx.fillText(label, 0, 0);
  ctx.restore();
}
function caption(ctx, label, x, y, color = INK, spacing = 1.8) {
  ctx.font = '16px IncubatorMedium';
  ctx.textBaseline = 'alphabetic';
  ctx.fillStyle = color;
  for (const letter of label) {
    ctx.fillText(letter, x, y);
    x += ctx.measureText(letter).width + spacing;
  }
}

// The trapezoid arms, center notch and point follow the V molded in the supplied lid photo.
const mold = [[0, 0], [.31, 0], [.50, .39], [.69, 0], [1, 0], [.50, 1]];
const trace = (x, y, w, h) => mold.map(([u,v]) => [x + w * u, y + h * v]);
function impression(ctx, x, y, w, h, color = BLUE, offset = RED) {
  const cut = trace(x,y,w,h);
  print(ctx, cut.map(([u,v]) => [u+5,v+5]), offset);
  print(ctx, cut, color);
}
function face(ctx, x, y, w) {
  const im = assets.face;
  ctx.drawImage(im, x, y, w, w * im.height / im.width);
}
function stockGrain() {
  const tile = createCanvas(193, 211);
  const ctx = tile.getContext('2d');
  const pixels = ctx.createImageData(tile.width, tile.height);
  let seed = 898717;
  for (let i = 0; i < pixels.data.length; i += 4) {
    seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0;
    const value = seed >>> 24;
    const light = value > 122;
    pixels.data[i] = light ? 253 : 33;
    pixels.data[i+1] = light ? 244 : 31;
    pixels.data[i+2] = light ? 224 : 54;
    pixels.data[i+3] = value % 13 + (value < 18 ? 13 : 0);
  }
  ctx.putImageData(pixels, 0, 0);
  return tile;
}
const stock = stockGrain();
function printedDetail() {
  const swatch = createCanvas(420, 440);
  const ctx = swatch.getContext('2d');
  ctx.drawImage(assets.face, 275, 278, 440, 461, 0, 0, 420, 440);
  const image = ctx.getImageData(0, 0, 420, 440), data = image.data;
  const dark = [24,43,94], light = [245,232,202];
  for (let i = 0; i < data.length; i += 4) {
    const luminance = (data[i] * .3 + data[i+1] * .59 + data[i+2] * .11) / 255;
    const amount = bound((luminance - .15) * 1.3, 0, 1);
    for (let c = 0; c < 3; c++) data[i+c] = dark[c] + (light[c] - dark[c]) * amount;
  }
  ctx.putImageData(image, 0, 0);
  return swatch;
}
const texture = printedDetail();

function hero(ctx, t, cover = false) {
  rect(ctx, PAPER);
  const a = cover ? .6 : drift(t, 3.6);
  impression(ctx, -111, 438 + 11 * a, 756, 388);
  // Shift the object independently of the inks: a photographic plate placed over a printed impression.
  face(ctx, 83 + 16 * a, 339 - 8 * a, 429);
  caption(ctx, 'ФОТООБЗОР', 47, 133);
  text(ctx, 'ИНКУБАТОР', 42, 231, 92, INK);
  text(ctx, '3.30', 39, 375, 167, RED, 410);
  caption(ctx, 'УСИЛИТЕЛЬ СИГНАЛА', 47, 844);
}
function purpose(ctx, t) {
  rect(ctx, BLUE);
  const a = drift(t);
  const form = trace(-49, 417, 629, 359);
  print(ctx, form.map(([x,y]) => [x+6,y+8]), RED);
  clipped(ctx, form, () => ctx.drawImage(texture, -42 + a * 18, 337 - a * 16, 650, 523));
  caption(ctx, 'НАЗНАЧЕНИЕ', 47, 142, PAPER);
  text(ctx, 'УСИЛИВАЕТ', 42, 247, 92, PAPER);
  text(ctx, 'РАДИОСИГНАЛ', 42, 327, 71, PAPER);
}
function materials(ctx, t) {
  rect(ctx, PAPER);
  const a = drift(t);
  impression(ctx, 57, 396, 551, 342, BLUE, '#ba3625');
  face(ctx, 142 - 15 * a, 309 + 14 * a, 425);
  print(ctx, [[0,635], [179,635], [331,839], [0,839]], RED);
  text(ctx, 'КОРПУС', 42, 220, 108, BLUE);
  text(ctx, 'Анодированный', 48, 281, 36, INK, 400, 'Medium');
  text(ctx, 'алюминий', 48, 325, 36, INK, 400, 'Medium');
  text(ctx, 'КОЖУХ', 46, 711, 43, PAPER, 171);
  text(ctx, 'пластиковый', 46, 755, 35, PAPER, 210, 'Medium');
  caption(ctx, 'ПО КАРТОЧКЕ ИЗДЕЛИЯ', 46, 810, PAPER, 1.1);
}
function dimensions(ctx, t) {
  rect(ctx, PAPER);
  const a = drift(t);
  impression(ctx, 4, 246, 483, 282);
  face(ctx, 133 - 12 * a, 158 - 4 * a, 377);
  print(ctx, [[0,546], [271,546], [299,579], [W,579], [W,H], [0,H]], BLUE);
  caption(ctx, 'ГАБАРИТЫ БЛОКА', 47, 143);
  text(ctx, PHYSICAL.size, 44, 664, 68, PAPER);
  text(ctx, PHYSICAL.mass, 39, 778, 112, PAPER, 405);
  caption(ctx, 'ПО КАРТОЧКЕ ИЗДЕЛИЯ', 46, 826, PAPER, 1.35);
}
function suitcase(ctx, t) {
  rect(ctx, PAPER);
  const a = drift(t), w = W + 12 * a, x = (W - w)/2, y = 323 - 4 * a;
  const h = w * assets.lid.height / assets.lid.width;
  ctx.drawImage(assets.lid, x, y, w, h);
  // Track the real relief so the print motif visibly comes from this specific case.
  ctx.save();
  ctx.globalAlpha = ease((t - .14) / .55);
  path(ctx, trace(x + .355 * w, y + .103 * h, .295 * w, .247 * h));
  ctx.strokeStyle = '#ed694c';
  ctx.lineWidth = 2.7;
  ctx.stroke();
  ctx.restore();
  text(ctx, 'КЕЙС', 42, 226, 132, INK);
  caption(ctx, 'ДЛЯ ПЕРЕВОЗКИ', 48, 280);
}
function tray(ctx, t) {
  rect(ctx, BLUE);
  caption(ctx, 'ВНУТРИ КЕЙСА', 46, 142, PAPER);
  text(ctx, 'ЛОЖЕМЕНТ', 42, 242, 100, PAPER);
  const a = drift(t, 3.3);
  const cut = [[-9,370], [116,327], [223,327], [288,398], [353,327], [547,327], [547,685], [415,776], [-9,776]];
  print(ctx, cut.map(([x,y]) => [x+6,y+6]), RED);
  clipped(ctx, cut, () => {
    const h = 476 + 12 * a, w = h * assets.tray.width / assets.tray.height;
    ctx.drawImage(assets.tray, (W - w)/2 - 28 * a, 317 - 5 * a, w, h);
  });
}
function mark(ctx, t) {
  rect(ctx, PAPER);
  const a = drift(t, 2.8);
  impression(ctx, -92, 385, 714, 412);
  caption(ctx, 'МАРКИРОВКА НА КРЫШКЕ', 47, 142);
  text(ctx, 'ЯЩИК № 1', 41, 247, 102, INK);
  const strip = [[-1,444], [475,444], [550,543], [550,573], [-1,573]];
  print(ctx, strip.map(([x,y]) => [x+6,y+6]), RED);
  clipped(ctx, strip, () => ctx.drawImage(assets.label, -75 - 5*a, 440 - a*4, 693, 138));
}
function passport(ctx, t) {
  rect(ctx, PAPER);
  const a = drift(t, 2.8);
  impression(ctx, -153, 362 + 8 * a, 767, 418);
  ctx.save();
  ctx.translate(26 + 12 * a, 476 - 8 * a);
  ctx.rotate(-.095 + .018 * a);
  // An enlarged strip of the actual cover, not the contents of the passport or manual.
  rect(ctx, '#17224455', 0, 7, 517, 91);
  rect(ctx, '#f5f0e9', 0, 0, 517, 91);
  ctx.drawImage(assets.passport, 0, 0, 424, 39, 30, 20, 462, 43);
  ctx.restore();
  caption(ctx, 'ДОКУМЕНТЫ', 47, 142);
  text(ctx, 'ТЕХПАСПОРТ', 42, 242, 95, INK);
  text(ctx, 'Инкубатор 3.30', 46, 839, 33, INK, 437, 'Medium');
}

const scenes = { hero, purpose, materials, dimensions, case: suitcase, tray, mark, passport };
const renderScene = (ctx, { kind, start }, seconds) => scenes[kind](ctx, Math.max(0, seconds - start));
function opening(ctx, t, paint) {
  // The same center notch travels down the shot boundary instead of a generic crossfade.
  const edge = -129 + (H + 151) * ease(t / WIPE);
  const seam = [[-15, edge], [W * .38, edge], [W * .52, edge + 110], [W * .66, edge], [W + 15, edge]];
  clipped(ctx, [[-16, -140], [W + 16, -140], ...seam.toReversed()], paint);
  ctx.beginPath();
  ctx.moveTo(...seam[0]);
  for (const [x,y] of seam.slice(1)) ctx.lineTo(x,y);
  ctx.lineWidth = 6;
  ctx.strokeStyle = RED;
  ctx.stroke();
}

export function createFilm(scale = 1) {
  const canvas = createCanvas(Math.round(W * scale), Math.round(H * scale));
  const ctx = canvas.getContext('2d');
  ctx.setTransform(canvas.width / W, 0, 0, canvas.height / H, 0, 0);
  ctx.imageSmoothingQuality = 'high';
  const grain = ctx.createPattern(stock,'repeat');
  const finish = () => { rect(ctx, grain); return canvas; };
  function draw(seconds) {
    const now = bound(seconds, 0, DURATION);
    const i = SHOTS.findLastIndex(({ start }) => now >= start);
    const shot = SHOTS[i], local = now - shot.start;
    if (i > 0 && local < WIPE) {
      renderScene(ctx, SHOTS[i - 1], shot.start);
      opening(ctx, local, () => renderScene(ctx, shot, now));
    } else {
      renderScene(ctx, shot, now);
    }
    return finish();
  }
  function drawCover() {
    hero(ctx, 0, true);
    return finish();
  }
  return { canvas, draw, drawCover };
}
