export const P = {
  dark: '#183638', deep: '#1f4b4a', teal: '#38766e', mint: '#a6d7c7', cream: '#f9ecd2',
  warm: '#f3c584', orange: '#db875e', rule: '#8ca99a', soft: '#d6dfc8', asphalt: '#476963',
};
export const clamp = (x) => Math.max(0, Math.min(1, x));
export const ease = (x) => 1 - (1 - clamp(x)) ** 3;
export function fill(ctx, color, x, y, w, h) { ctx.fillStyle = color; ctx.fillRect(x, y, w, h); }
export function path(ctx, points, color, stroke, width = 2) {
  ctx.beginPath(); ctx.moveTo(...points[0]);
  points.slice(1).forEach((p) => ctx.lineTo(...p));
  if (color) { ctx.closePath(); ctx.fillStyle = color; ctx.fill(); }
  if (stroke) { ctx.strokeStyle = stroke; ctx.lineWidth = width; ctx.stroke(); }
}
export function rounded(ctx, color, x, y, w, h, r, stroke, width = 1.5) {
  ctx.beginPath(); ctx.roundRect(x, y, w, h, r);
  if (color) { ctx.fillStyle = color; ctx.fill(); }
  if (stroke) { ctx.strokeStyle = stroke; ctx.lineWidth = width; ctx.stroke(); }
}
export function ellipse(ctx, color, x, y, w, h, stroke, width = 1) {
  ctx.beginPath(); ctx.ellipse(x, y, w, h, 0, 0, 2 * Math.PI);
  if (color) { ctx.fillStyle = color; ctx.fill(); }
  if (stroke) { ctx.strokeStyle = stroke; ctx.lineWidth = width; ctx.stroke(); }
}
export function type(ctx, value, x, y, size, color, { medium = false, align = 'left', tracking } = {}) {
  ctx.font = `${size}px Bulat${medium ? 'Medium' : 'Black'}`;
  ctx.textBaseline = 'alphabetic'; ctx.fillStyle = color;
  if (!tracking) { ctx.textAlign = align; ctx.fillText(value, x, y); return; }
  ctx.textAlign = 'left';
  const letters = [...value];
  const widths = letters.map((letter) => ctx.measureText(letter).width + tracking);
  const span = widths.reduce((a, b) => a + b, -tracking);
  if (align === 'right') x -= span;
  else if (align === 'center') x -= span / 2;
  for (const [i, letter] of letters.entries()) { ctx.fillText(letter, x, y); x += widths[i]; }
}
export function line(ctx, x, y, w, color = P.rule, thickness = 1) { fill(ctx, color, x, y, w, thickness); }

// Illustrative front view based on the supplied photo; these are drawing coordinates.
function aerial(ctx, x, top, width, grip, accent) {
  const body = ctx.createLinearGradient(x - width / 2, 0, x + width / 2, 0);
  body.addColorStop(0, '#19272a');
  body.addColorStop(.30, '#515e5e');
  body.addColorStop(.55, '#39494a');
  body.addColorStop(1, '#182628');
  rounded(ctx, body, x - width / 2, top, width, -108 - top, 6, '#182628', 2);
  rounded(ctx, '#222d30', x - width / 2, top - 1, width, 35, 6, '#101e22', 2);
  rounded(ctx, '#768282', x - width * .28, top + 5, width * .14, 24, 2);
  rounded(ctx, '#324144', x - width / 2 - 2, grip, width + 4, -107 - grip, 4, '#222f32', 1.5);
  for (let y = grip + 9; y < -124; y += 8) line(ctx, x - width / 2 + 1, y, width - 2, '#56646566');
  if (accent) ellipse(ctx, '#96cfc5', x, grip + 56, 9.1, 9.1, '#253b40', 1.3);
  else {
    rounded(ctx, '#647471', x - 11, -128, 22, 21, 3, '#1b2a2b');
    for (let y = -123; y <= -111; y += 4) line(ctx, x - 8, y, 16, '#a1a298');
  }
}
export function device(ctx, x, y, scale, roll, energy = 0) {
  ctx.save(); ctx.translate(x, y); ctx.scale(scale, scale); ctx.rotate(roll);
  aerial(ctx, -34, -357, 24, -247, false);
  aerial(ctx, 29, -523, 25, -236, true);
  rounded(ctx, '#102f2d42', -53, -103 + 8, 122, 216, 17);
  rounded(ctx, '#1c292b', -61, -111, 123, 221, 17, '#162628', 2.5);
  const face = ctx.createLinearGradient(-58, -104, 54, 118);
  face.addColorStop(0, '#4d5e5e'); face.addColorStop(.44, '#2d4041'); face.addColorStop(1, '#283434');
  rounded(ctx, face, -57, -109, 111, 214, 13, '#1a2a2b', 2);
  for (const ax of [-61, 58]) {
    for (let i = 0; i < 11; i++) rounded(ctx, '#4e6260', ax - 1.7, -85 + 13 * i, 4, 7, 1.1);
  }
  rounded(ctx, '#1d3031', -43, -99, 85, 86, 6, '#617774');
  rounded(ctx, '#9bcfc7', -36, -95, 70, 10, 2);
  type(ctx, 'БУЛАТ v4', -2, -87, 7.2, '#28514c', { align: 'center', tracking: .6 });
  rounded(ctx, '#0e2628', -37, -82, 71, 66, 4, '#506966');
  rounded(ctx, energy ? '#9d9c6c' : '#849671', -33, -78, 63, 58, 2);
  // Intentional placeholder marks rather than the device's real screen or key legends.
  line(ctx, -26, -68, 28, '#536b57', 2);
  line(ctx, -26, -57, 42, '#3d5e4e', 3.6);
  for (let i = 0; i < 4; i++) rounded(ctx, null, -26 + 12 * i, -44, 8, 5, .8, '#577358', .9);
  line(ctx, -26, -30, 33, '#668064', 1.2);
  rounded(ctx, '#243738', -43, -7, 85, 100, 9, '#627372');
  for (let row = 0; row < 5; row++) {
    for (let col = 0; col < 3; col++) {
      const kx = -35 + col * 25, ky = 1 + row * 17.8;
      rounded(ctx, row === 0 ? '#b9c0b5' : '#8e9f97', kx, ky, 21, 14, 3, '#133030', 1.35);
      line(ctx, kx + 4, ky + 2.4, 12, '#d7dccc', 1.1);
    }
  }
  ctx.restore();
}

function rollingTruck(ctx, x, y, service = false) {
  const body = service ? '#edb479' : '#d9ad76';
  const shadow = service ? '#d48b60' : '#9e8660';
  ellipse(ctx, '#243e3c63', x + 55, y + 54, 65, 10);
  rounded(ctx, P.dark, x - 5, y + 32, 126, 15, 3);
  rounded(ctx, body, x, y, service ? 90 : 78, 39, 4, P.dark, 2.6);
  path(ctx, [[x + 2, y + 29], [x + 80, y + 22], [x + 80, y + 37], [x + 2, y + 37]], shadow);
  path(ctx, [[x + 79, y + 8], [x + 105, y + 8], [x + 118, y + 22],
    [x + 122, y + 39], [x + 79, y + 39]], '#d6e2be', P.dark, 2.8);
  path(ctx, [[x + 95, y + 12], [x + 104, y + 12], [x + 115, y + 24], [x + 95, y + 24]], '#769990', P.dark, 1);
  if (service) line(ctx, x + 3, y + 23, 73, '#b27153', 4);
  rounded(ctx, '#f4d8a1', x + 114, y + 29, 6, 6, 1.6);
  for (const wx of [x + 19, x + 99]) {
    ellipse(ctx, P.dark, wx, y + 42, 9.8, 10);
    ellipse(ctx, '#879b88', wx, y + 42, 4.8, 4.8);
  }
}
function cloud(ctx, x, y, r) {
  rounded(ctx, '#d9e8d4b2', x - 26 * r, y, 106 * r, 12 * r, 6 * r);
  rounded(ctx, '#e4ebd3b2', x, y - 8 * r, 43 * r, 10 * r, 5 * r);
}
function box(ctx, x, y, s = 1) {
  const w = 38 * s, h = 29 * s;
  path(ctx, [[x, y], [x + w, y - 7 * s], [x + w + 12 * s, y], [x + 12 * s, y + 6 * s]], '#f3cf8f', '#765e51', 1.8);
  path(ctx, [[x + w + 12 * s, y], [x + 12 * s, y + 6 * s], [x + 12 * s, y + h],
    [x + w + 12 * s, y + h - 6 * s]], '#c39c74', '#765e51', 1.8);
  path(ctx, [[x, y], [x + 12 * s, y + 6 * s], [x + 12 * s, y + h], [x, y + h - 3 * s]], '#a9886b', '#765e51', 1.8);
}
function tree(ctx, x, y, scale, ink = '#6d9d81') {
  ctx.save(); ctx.translate(x, y); ctx.scale(scale, scale);
  ellipse(ctx, '#3d5d4f4c', 8, 1, 20, 5);
  fill(ctx, '#544c3f', -2, -16, 4.4, 16);
  path(ctx, [[0, -66], [20, -21], [13, -21], [23, -8], [-22, -8], [-11, -21], [-18, -21]], ink, '#4f7a69', 2);
  ctx.restore();
}
function helmetWorker(ctx, x, y, scale, t) {
  ctx.save(); ctx.translate(x, y); ctx.scale(scale, scale);
  ellipse(ctx, '#42634f66', 6, 0, 24, 5);
  rounded(ctx, '#436371', -13, -31, 28, 20, 4);
  path(ctx, [[-10, -19], [-10, -3], [-18, -2], [-18, 1], [-5, 1], [1, -20]], '#3a5058', P.dark, 1.6);
  path(ctx, [[1, -21], [3, -2], [14, 0], [20, -2], [13, -6], [12, -21]], '#3a5058', P.dark, 1.6);
  rounded(ctx, '#e6b681', -15, -58, 32, 29, 6, '#44655d', 2);
  path(ctx, [[-15, -38], [15, -40], [15, -46], [-15, -46]], '#f7d698');
  ellipse(ctx, '#dcb196', 1, -67, 11.4, 12.5, '#425b50', 1.7);
  ellipse(ctx, '#efbf77', .5, -76, 14.2, 9, '#586651', 1.8);
  rounded(ctx, '#efbf77', -16, -77, 33, 4.5, 2, '#586651', 1.4);
  const move = Math.sin(t * 2.3) * 1.8;
  path(ctx, [[9, -54], [30, -48 + move], [28, -42 + move], [12, -44]], '#bf9878', '#566859', 1.4);
  ctx.restore();
}

function warehouse(ctx, t) {
  fill(ctx, '#abcdbd', 0, 0, 460, 420);
  ellipse(ctx, '#f4cc8a', 374, 103, 42, 42);
  cloud(ctx, 77 - t * 2, 82, 1.1); cloud(ctx, 207 + t, 123, .75);
  path(ctx, [[0, 216], [92, 174], [184, 213], [282, 181], [460, 214], [460, 420], [0, 420]], '#8ab2a0');
  fill(ctx, '#78a08e', 0, 279, 460, 141);
  path(ctx, [[0, 346], [460, 283], [460, 361], [0, 409]], P.asphalt);
  for (let i = 0; i < 12; i++) path(ctx, [[i * 44, 376 - i * 5], [i * 44 + 18, 374 - i * 5]], null, '#d2c89c', 1.7);
  const d = Math.sin(t * .65) * 4;
  ellipse(ctx, '#36594c67', 205, 332, 149, 19);
  path(ctx, [[67 + d, 170], [274 + d, 169], [274 + d, 320], [67 + d, 316]], '#b5c9aa', '#3c6259', 3.3);
  path(ctx, [[274 + d, 169], [339 + d, 146], [339 + d, 291], [274 + d, 320]], '#6e998a', '#3c6259', 3.3);
  path(ctx, [[57 + d, 171], [146 + d, 120], [239 + d, 123], [349 + d, 145],
    [279 + d, 177]], '#579080', '#3c6259', 3.3);
  for (let i = 0; i < 3; i++) {
    const x = 86 + i * 57 + d;
    rounded(ctx, '#5c8176', x, 233, 44, 79, 3, '#486f66', 2);
    for (let j = 0; j < 7; j++) line(ctx, x + 4, 245 + j * 8, 36, '#c0ceab', 1.2);
  }
  rounded(ctx, '#3e7064', 92 + d, 183, 107, 31, 5);
  type(ctx, 'СКЛАД', 145 + d, 204, 16, P.cream, { align: 'center', tracking: 1.5 });
  box(ctx, 281, 302, .92); box(ctx, 300, 285, .75);
  ctx.save(); ctx.translate(71 + 69 * t, 346 - 7.4 * t); ctx.rotate(-.105); rollingTruck(ctx, -37, -29); ctx.restore();
}
function construction(ctx, t) {
  fill(ctx, '#d3d8b6', 0, 0, 460, 420);
  ellipse(ctx, '#f2c578', 86, 105, 43, 43);
  cloud(ctx, 218 - t * 2, 80, 1.07);
  path(ctx, [[0, 250], [121, 196], [259, 216], [376, 180], [460, 205], [460, 420], [0, 420]], '#a7bca2');
  fill(ctx, '#9caa8c', 0, 308, 460, 112);
  path(ctx, [[0, 382], [257, 328], [460, 327], [460, 420], [0, 420]], '#b0ac89');
  ellipse(ctx, '#58685366', 162, 347, 132, 16);
  path(ctx, [[52, 327], [52, 210], [251, 202], [251, 329]], '#b7c8a8', '#587b6a', 4);
  path(ctx, [[251, 202], [279, 179], [279, 311], [251, 329]], '#7f9e8a', '#587b6a', 4);
  for (const zy of [224, 270]) {
    path(ctx, [[49, zy], [252, zy - 8], [285, zy - 32]], null, '#5c8571', 8);
    for (let j = 0; j < 3; j++) {
      const x = 64 + j * 63;
      rounded(ctx, '#71937e', x, zy + 8 - j * 1.5, 49, 26, 2, '#608677', 1.8);
    }
  }
  path(ctx, [[315, 337], [315, 116], [335, 116], [335, 337]], '#d8ac71', '#7d785a', 2.3);
  for (let y = 129; y < 336; y += 18) path(ctx, [[315, y], [335, y + 18], [315, y + 18]], null, '#8f7653', 1.7);
  path(ctx, [[169, 115], [323, 72], [436, 114], [436, 125], [169, 125]], '#e3b675', '#7d785a', 2.5);
  path(ctx, [[322, 74], [321, 125], [372, 93], [372, 122]], null, '#b18e5e', 1.8);
  const hook = 208 + Math.sin(t * 1.1) * 8;
  path(ctx, [[382, 125], [382, hook - 8], [370, hook + 2]], null, '#5b7766', 1.65);
  box(ctx, 355, hook + 4, .68);
  helmetWorker(ctx, 287, 382, .86, t);
  box(ctx, 42, 373, 1); box(ctx, 76, 359, .9);
}
function service(ctx, t) {
  fill(ctx, '#b0cfbe', 0, 0, 460, 420);
  ellipse(ctx, '#f0cc91', 319, 100, 42, 42);
  cloud(ctx, 65 - t * 2, 84, 1.25);
  path(ctx, [[0, 242], [81, 164], [170, 203], [269, 144], [377, 191], [460, 173], [460, 420], [0, 420]], '#8db5a1');
  path(ctx, [[0, 298], [114, 246], [186, 265], [308, 234], [460, 262], [460, 420], [0, 420]], '#7ea783');
  for (const [x, y, size] of [[38, 247, .8], [69, 241, .56], [184, 246, .7], [398, 276, 1.1], [441, 250, .8]]) tree(ctx, x, y, size);
  path(ctx, [[0, 325], [460, 268], [460, 366], [0, 421]], '#55776e');
  for (let i = 0; i < 12; i++) path(ctx, [[i * 43, 385 - i * 4.7], [i * 43 + 17, 383 - i * 4.7]], null, '#ddd2a3', 2.3);
  ctx.save(); ctx.translate(101, 308); ctx.rotate(-.10); ctx.scale(1.17, 1.17); rollingTruck(ctx, -10, -20, true); ctx.restore();
  helmetWorker(ctx, 296 + 3 * Math.sin(t * 1.4), 347, .98, t);
  rounded(ctx, '#6b8d75', 324, 320, 68, 8, 3, '#476353', 1.8);
  for (const x of [330, 381]) fill(ctx, '#45695d', x, 328, 4, 24);
  ellipse(ctx, '#ecd197', 361, 313, 12, 8, '#b29873', 2);
}
const contexts = [warehouse, construction, service];
export function siteArt(ctx, i, t, x, y, w, h) {
  const scale = Math.max(w / 460, h / 420);
  ctx.save(); ctx.beginPath(); ctx.rect(x, y, w, h); ctx.clip();
  ctx.translate(x + (w - 460 * scale) / 2, y + (h - 420 * scale) / 2);
  ctx.scale(scale, scale); contexts[i](ctx, t); ctx.restore();
}
