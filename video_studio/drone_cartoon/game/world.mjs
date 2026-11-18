// A fictional, hand-built low-poly set. All positions are in local drawing units.
const W = 540;
const PI = Math.PI;
const night = {
  sky: ['#101e2b', '#315063', '#13252b'], horizon: '#213a48', tower: '#1a3040',
  ground: '#243e42', turf: '#2c4547', asphalt: '#152a32', edge: '#557578',
  paint: '#c2ba84', treetop: '#29494a', trunk: '#264348', window: '#b5e6cc',
  stock: ['#538895', '#406d80', '#254452'], office: ['#76a5ab', '#2d5867', '#214250'],
  plant: ['#456d77', '#345561', '#263f50'], roofDetail: ['#82a3aa', '#50727d', '#355262'],
  truck: ['#f5c682', '#c4925e', '#805c48'], shadow: 'rgba(5,18,27,.52)',
};
const day = {
  sky: ['#244453', '#eaa979', '#c49277'], horizon: '#6c776d', tower: '#7f7e71',
  ground: '#5c7c6f', turf: '#6b8978', asphalt: '#3d5355', edge: '#a8b793',
  paint: '#ebca85', treetop: '#537866', trunk: '#3e5d56', window: '#f6df9e',
  stock: ['#94b9ae', '#658d88', '#436966'], office: ['#a4c5b5', '#719d91', '#567d75'],
  plant: ['#b4bba2', '#788f84', '#506e6c'], roofDetail: ['#c6c7a7', '#8ea496', '#6b8d85'],
  truck: ['#f3cd8e', '#c58d63', '#825d53'], shadow: 'rgba(23,39,40,.3)',
};

const stock = { x: -72, y: -22, w: 67, d: 33, h: 18, kind: 'stock' };
const office = { x: 20, y: -18, w: 36, d: 30, h: 26, kind: 'office' };
const workshops = [
  { x: -106, y: -64, w: 32, d: 21, h: 17, kind: 'plant' },
  { x: -60, y: -65, w: 41, d: 21, h: 15, kind: 'plant' },
  { x: -8, y: -69, w: 28, d: 28, h: 23, kind: 'plant' },
  { x: 38, y: -63, w: 62, d: 22, h: 13, kind: 'plant' },
  { x: 75, y: -9, w: 24, d: 29, h: 11, kind: 'plant' },
  stock, office,
];
const smallParts = [
  [-59, -12, 9, 6, 2.4, 18], [-44, -12, 9, 6, 2.4, 18], [-29, -12, 9, 6, 2.4, 18],
  [29, -11, 16, 11, 2.8, 26], [49, -10, 4, 8, 1.4, 26], [-1, -63, 6, 7, 4, 23],
];

export const CAMERAS = {
  '01': { x: -37, y: -4, zoom: 2.84, yaw: -.42, tilt: .67, yAt: 462 },
  '02': { x: -19, y: 43, zoom: 2.96, yaw: -.08, tilt: .61, yAt: 455 },
  '03': { x: 38, y: 0, zoom: 3.0, yaw: .34, tilt: .62, yAt: 456 },
};
export const PANORAMA = { x: -1, y: 1, zoom: 1.94, yaw: -.38, tilt: .65, yAt: 479 };
const TAU = 2 * PI;
const hash = (n) => ((Math.imul(n ^ 12345, 2246822519) >>> 0) % 1009) / 1009;

function projector(c) {
  const cos = Math.cos(c.yaw), sin = Math.sin(c.yaw);
  function depth(x, y) { return (x - c.x) * sin + (y - c.y) * cos; }
  function point([x, y, z = 0]) {
    const v = depth(x, y);
    const k = c.zoom * (1 + .0007 * v);
    return [W / 2 + ((x - c.x) * cos - (y - c.y) * sin) * k, c.yAt + (v * c.tilt - z) * k];
  }
  return { depth, point, east: sin > 0, scale: c.zoom };
}
function path(ctx, points, fill, outline, line = 1) {
  ctx.beginPath();
  ctx.moveTo(...points[0]);
  for (const p of points.slice(1)) ctx.lineTo(...p);
  if (fill) { ctx.closePath(); ctx.fillStyle = fill; ctx.fill(); }
  if (outline) { ctx.strokeStyle = outline; ctx.lineWidth = line; ctx.stroke(); }
}
function poly(ctx, p, vertices, fill, outline, line) {
  path(ctx, vertices.map(p.point), fill, outline, line);
}
function slab(ctx, p, x, y, w, d, fill, z = 0) {
  poly(ctx, p, [[x, y, z], [x + w, y, z], [x + w, y + d, z], [x, y + d, z]], fill);
}
function box(ctx, p, dims, colors) {
  const [x, y, w, d, h, z = 0] = dims;
  const f = y + d, top = z + h;
  const s = p.east ? x + w : x;
  poly(ctx, p, [[s, y, top], [s, f, top], [s, f, z], [s, y, z]], colors[2]);
  poly(ctx, p, [[x, f, top], [x + w, f, top], [x + w, f, z], [x, f, z]], colors[1]);
  poly(ctx, p, [[x, y, top], [x + w, y, top], [x + w, f, top], [x, f, top]], colors[0]);
}
function face(ctx, p, x, y, z, w, h, color) {
  poly(ctx, p, [[x, y, z + h], [x + w, y, z + h], [x + w, y, z], [x, y, z]], color);
}
function building(ctx, p, c, b) {
  const {x, y, w, d, h, kind} = b;
  const f = y + d + .015;
  box(ctx, p, [x, y, w, d, h], c[kind]);
  // Roof rim and panel seams keep the solid silhouettes legible on a small screen.
  poly(ctx, p, [[x, f, h], [x + w, f, h], [x + w, y, h]], null, c.edge, 1.2);
  for (let j = 1; j < Math.ceil(w / 10); j++) {
    poly(ctx, p, [[x + 10 * j, y + 1, h], [x + 10 * j, f - 1, h]], null, 'rgba(25,45,48,.21)', 1);
  }
  if (kind === 'stock') {
    for (let k = 0; k < 4; k++) {
      const l = x + 5 + k * 15;
      face(ctx, p, l, f, 0, 10.5, 8, c.stock[2]);
      face(ctx, p, l + 1.1, f + .02, 1.1, 8.3, 5.8, c.stock[1]);
      face(ctx, p, l + 1.2, f + .03, 7, 8.2, .48, c.window);
      slab(ctx, p, l, f + 1, 10.5, .56, c.paint, .01);
    }
    face(ctx, p, x + 11, f, 12, 45, 2.1, c.stock[2]);
    face(ctx, p, x + 13, f + .02, 12.65, 41, .6, c.window);
  } else {
    const rows = kind === 'office' ? 4 : 2;
    for (let row = 0; row < rows; row++) {
      for (let j = 0; j < Math.floor((w - 2) / 6); j++) {
        const l = x + 2.2 + j * 6;
        const z = h - 6.3 - 5.15 * row;
        face(ctx, p, l, f, z, 4.7, 3.38, c[kind][2]);
        face(ctx, p, l + .4, f + .01, z + .4, 3.9, 2.4,
          hash(j + row * 11 + b.h) > .31 ? c.window : c[kind][0]);
      }
    }
  }
  for (const [cx, cy, w2, d2, h2, z] of smallParts) {
    if (cx >= x && cx < x + w && cy >= y && cy < y + d && h === z) {
      box(ctx, p, [cx, cy, w2, d2, h2, z], c.roofDetail);
    }
  }
}
function circle(ctx, x, y, rx, ry, fill) {
  ctx.beginPath(); ctx.ellipse(x, y, rx, ry, 0, 0, TAU);
  ctx.fillStyle = fill; ctx.fill();
}
function truck(ctx, p, c, x, y, small = false) {
  const l = small ? 14 : 22, d = small ? 5.1 : 6.7, z = small ? 5.7 : 8.4;
  box(ctx, p, [x, y, l, d, 2.3], [c.asphalt, '#283839', '#233438']);
  for (const dx of [3.7, l - 3.1]) {
    const [wx, wy] = p.point([x + dx, y + d + .15, 1.15]);
    circle(ctx, wx, wy, p.scale * 1.3, p.scale * 1.24, '#1c2d30');
    circle(ctx, wx, wy, p.scale * .60, p.scale * .57, c.edge);
  }
  box(ctx, p, [x + .8, y + .25, l - 6.8, d - .5, z - 1.3, 1.8], c.truck);
  box(ctx, p, [x + l - 5.7, y + .18, 5.4, d - .34, z * .54, 2.0], c.roofDetail);
  face(ctx, p, x + l - 4.7, y + d - .13, 3.5, 3.8, z * .30, c.office[2]);
}
function loader(ctx, p, c, x, y) {
  const deep = ['#41484a', '#363f41', '#263236'];
  box(ctx, p, [x, y, 13, 6, 2.2], deep);
  box(ctx, p, [x + 1, y + .38, 11.3, 5.2, 3.7, 1.5], c.truck);
  box(ctx, p, [x + 2.7, y + .7, 5.2, 4.6, 4.4, 4.7], c.roofDetail);
  face(ctx, p, x + 3.2, y + 5.32, 6.2, 3.94, 2.0, c.stock[2]);
  poly(ctx, p, [[x + 7.6, y + 5.6, 5.1], [x + 12.4, y + 5.6, 6.5],
    [x + 17.4, y + 5.6, 2.55], [x + 16.7, y + 5.6, 1.55], [x + 11.0, y + 5.6, 4.55]], c.truck[0]);
  box(ctx, p, [x + 15.8, y + .3, 4.8, 6.0, 2.5], c.truck);
  for (const dx of [2.5, 10.75]) {
    const [cx, cy] = p.point([x + dx, y + 5.8, 1.05]);
    circle(ctx, cx, cy, 1.53 * p.scale, 1.45 * p.scale, '#243537');
    circle(ctx, cx, cy, .69 * p.scale, .65 * p.scale, c.paint);
  }
}
function tree(ctx, p, c, x, y, salt) {
  const [sx, sy] = p.point([x, y, 0]);
  const s = (.65 + hash(salt) * .60) * p.scale;
  circle(ctx, sx + 1.7 * s, sy + .5 * s, 4 * s, 2.0 * s, c.shadow);
  path(ctx, [[sx - .47 * s, sy], [sx + .48 * s, sy], [sx + .50 * s, sy - 6 * s],
    [sx - .45 * s, sy - 6 * s]], c.trunk);
  path(ctx, [[sx - 3.3 * s, sy - 4.1 * s], [sx - 2.1 * s, sy - 8.5 * s],
    [sx, sy - 11 * s], [sx + 3.2 * s, sy - 7 * s], [sx + 2.6 * s, sy - 4.2 * s]], c.treetop);
  path(ctx, [[sx - 3.3 * s, sy - 4.1 * s], [sx - 2.1 * s, sy - 8.5 * s],
    [sx, sy - 11 * s], [sx, sy - 3.9 * s]], c.turf);
}
function skyline(ctx, c, camera, morning) {
  const horizon = camera.horizonY ?? 294 - camera.tilt * 105;
  const sky = ctx.createLinearGradient(0, 128, 0, 475);
  c.sky.forEach((color, i) => sky.addColorStop(i === 1 ? .43 : i / 2, color));
  ctx.fillStyle = sky; ctx.fillRect(0, 0, W, 790);
  if (morning) {
    const glow = ctx.createRadialGradient(406, horizon - 9, 8, 406, horizon - 9, 120);
    glow.addColorStop(0, '#fff1bb'); glow.addColorStop(.43, '#ffba8777'); glow.addColorStop(1, '#ff9e7000');
    circle(ctx, 406, horizon - 9, 119, 118, glow);
    circle(ctx, 406, horizon - 9, 28, 28, '#ffeabc');
  }
  const shift = camera.yaw * 44 + camera.x * .19;
  path(ctx, [[0, horizon + 32], [0, horizon - 20], [76, horizon - 47], [176, horizon - 25],
    [290, horizon - 43], [399, horizon - 20], [505, horizon - 28], [540, horizon - 7],
    [540, horizon + 39]], c.horizon);
  for (let i = -2; i < 19; i++) {
    const x = i * 39 - shift;
    const h = 8 + 26 * hash(i * 5);
    ctx.fillStyle = c.tower; ctx.fillRect(x, horizon - h * .48, 26 + 16 * hash(i + 78), h);
    if (i % 3 === 0) {
      ctx.globalAlpha = .46; ctx.fillStyle = c.window; ctx.fillRect(x + 6, horizon + 1, 4, 1.3); ctx.globalAlpha = 1;
    }
  }
  ctx.fillStyle = c.ground; ctx.fillRect(0, horizon + 14, W, 715);
}

export function renderWorld(ctx, camera, t, morning = false) {
  const c = morning ? day : night;
  const p = projector(camera);
  skyline(ctx, c, camera, morning);
  slab(ctx, p, -180, -42, 360, 65, c.turf);
  slab(ctx, p, -180, 20, 360, 26, c.edge);
  slab(ctx, p, -176, 22, 352, 22, c.asphalt);
  slab(ctx, p, -86, 45, 110, 37, c.asphalt);
  slab(ctx, p, 26, 47, 7, 129, c.asphalt);
  slab(ctx, p, -75, -31, 170, 1.2, c.edge);
  for (let x = -148; x < 146; x += 15) slab(ctx, p, x, 33, 7, .58, c.paint, .01);
  for (let x = -81; x < 23; x += 14) {
    slab(ctx, p, x, 59, .44, 15, c.paint, .01);
    slab(ctx, p, x, 73.8, 6, .45, c.paint, .01);
  }
  for (let i = 0; i < 35; i++) {
    const x = -140 + i * 8;
    const y = i % 2 === 0 ? 84 + hash(i + 8) * 20 : -33;
    slab(ctx, p, x, y, 1 + 3 * hash(i), .25, c.edge, .01);
  }
  const actors = [];
  for (const b of workshops) {
    const {x, y, w, d, h} = b;
    slab(ctx, p, x + (morning ? 2 : -4), y + 4, w + 2, d + 6 + h * .12, c.shadow);
    actors.push([p.depth(x + w / 2, y + d), () => building(ctx, p, c, b)]);
  }
  const rolling = ((t * 10.2 + 61) % 220) - 113;
  for (const [i, x, y, small] of [[0, rolling, 24.4, false], [1, -51, 61, true], [2, -24, 63, false]]) {
    slab(ctx, p, x + 2, y + 1.6, small ? 17 : 25, 6.5, c.shadow);
    actors.push([p.depth(x + (i ? 7 : 11), y + 6.7), () => truck(ctx, p, c, x, y, small)]);
  }
  slab(ctx, p, 3, 60, 22, 8, c.shadow);
  actors.push([p.depth(13, 66), () => loader(ctx, p, c, 2, 60)]);
  for (let i = 0; i < 12; i++) {
    const x = -105 + 20 * i;
    const y = 86 + 6 * hash(i + 16);
    actors.push([p.depth(x, y), () => tree(ctx, p, c, x, y, i + 5)]);
  }
  for (let i = 0; i < 5; i++) {
    const x = 59 + 11 * hash(i + 3);
    const y = 3 + i * 8;
    actors.push([p.depth(x, y), () => tree(ctx, p, c, x, y, i + 23)]);
  }
  actors.sort(([a], [b]) => a - b);
  for (const [, draw] of actors) draw();
}
