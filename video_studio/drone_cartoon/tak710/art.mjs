import { Path2D } from '@napi-rs/canvas';
import { ellipse, fill, line, path, rounded } from '../bulat/art.mjs';

export const C = {
  paper: '#ede8d9', ink: '#233a3c', muted: '#567174',
  mint: '#a8c9be', cream: '#f8eed4', amber: '#f5c76f',
};
const paths = new Map();
function shape(ctx, d, color, outline, width = 1) {
  let p = paths.get(d);
  if (!p) { p = new Path2D(d); paths.set(d, p); }
  if (color) { ctx.fillStyle = color; ctx.fill(p); }
  if (outline) { ctx.strokeStyle = outline; ctx.lineWidth = width; ctx.stroke(p); }
}
export function text(ctx, value, x, y, size, color, { align = 'left', track, medium = false } = {}) {
  ctx.font = `${size}px Tak${medium ? 'Medium' : 'Black'}`;
  ctx.fillStyle = color; ctx.textBaseline = 'alphabetic';
  if (!track) { ctx.textAlign = align; ctx.fillText(value, x, y); return; }
  ctx.textAlign = 'left';
  const chars = [...value];
  const widths = chars.map((ch) => ctx.measureText(ch).width + track);
  const span = widths.reduce((sum, w) => sum + w, -track);
  if (align === 'center') x -= span / 2;
  else if (align === 'right') x -= span;
  chars.forEach((ch, i) => { ctx.fillText(ch, x, y); x += widths[i]; });
}
function webbing(ctx) {
  const web = 'M-73 -74 C-115 -94 -164 -75 -188 -45 Q-201 -7 -185 53 Q-164 92 -81 87 L70 89 Q161 90 201 45 Q215 23 205 -22 Q178 -68 83 -72 L59 -30 Q130 -32 160 -12 Q174 11 155 32 Q126 49 64 45 L-78 43 Q-141 44 -149 17 Q-156 -12 -110 -18 L-75 -15Z';
  const band = ctx.createLinearGradient(0, -83, 0, 92);
  band.addColorStop(0, '#535653'); band.addColorStop(.47, '#2f3938'); band.addColorStop(1, '#232d2c');
  shape(ctx, web, band, '#1d2628', 3.5);
  ctx.save(); ctx.clip(paths.get(web));
  for (let y = -78; y < 90; y += 4) line(ctx, -194, y, 405, '#adb6a420');
  for (let x = -189; x < 209; x += 7) fill(ctx, '#a5aa981c', x, -85, 1.3, 178);
  ctx.restore();
  shape(ctx, 'M-181 -37 Q-166 -47 -142 -47 L-142 35 Q-160 42 -177 49Z', '#5f645c', '#202d2d', 1.5);
  for (let y = -33; y <= 30; y += 9) shape(ctx, `M-173 ${y + 5} L-148 ${y}`, null, '#818b78', .9);
  rounded(ctx, '#252d2e', 113, -65, 63, 115, 13, '#1b2527', 3);
  rounded(ctx, '#4a5452', 106, -67, 61, 106, 12, '#283633', 2.5);
  rounded(ctx, '#212d2e', 117, -53, 11, 78, 4, '#717869');
  rounded(ctx, '#212d2e', 144, -53, 11, 78, 4, '#717869');
  rounded(ctx, '#35413e', 127, -64, 24, 105, 6);
}

// Exterior illustration, based on the front product photo. No operating sequence or screen values.
export function product(ctx, x, y, scale, angle, glow = 0) {
  ctx.save(); ctx.translate(x, y); ctx.scale(scale, scale); ctx.rotate(angle);
  webbing(ctx);
  rounded(ctx, '#151f2173', -82, -154, 181, 309, 40);
  rounded(ctx, '#263031', -89, -159, 183, 307, 42, '#151f21', 3.4);
  const rubber = ctx.createLinearGradient(-91, -135, 105, 147);
  rubber.addColorStop(0, '#4c5655'); rubber.addColorStop(.49, '#323e40'); rubber.addColorStop(1, '#273335');
  rounded(ctx, rubber, -97, -162, 178, 302, 41, '#243335', 2.5);
  for (let i = 0; i < 10; i++) {
    const yy = -124 + i * 24;
    path(ctx, [[-92, yy + 9], [-81, yy - 1]], null, '#222e30', 1.5);
    path(ctx, [[65, yy + 5], [78, yy - 4]], null, '#2a3637', 1.4);
  }
  rounded(ctx, '#333c3e', -79, -143, 144, 266, 28, '#c59d54', 1.9);
  rounded(ctx, null, -76, -139, 138, 258, 24, '#6b705d', 1.1);
  shape(ctx, 'M-31 -112 Q-8 -119 15 -112 Q20 -106 19 -90 Q17 -69 -8 -59 Q-32 -66 -37 -88 Q-39 -107 -31 -112Z', '#eab85c', '#ba944c', 1.4);
  shape(ctx, 'M-22 -105 L-9 -94 L5 -105 L10 -100 L-4 -89 L10 -77 L5 -73 L-9 -85 L-23 -74 L-27 -79 L-14 -90 L-28 -101Z', '#303b39');
  text(ctx, 'XMETIX', -8, -63, 8.4, '#303b39', { align: 'center', track: .3 });
  text(ctx, 'TAK710', -8, -39, 17, '#edc273', { align: 'center', track: 1.4 });
  shape(ctx, 'M-71 -16 Q-71 -29 -56 -33 Q-8 -44 49 -31 Q59 -28 59 -12 V85 Q59 107 45 111 H-51 Q-71 108 -71 89Z', '#212d2e');
  rounded(ctx, '#5a6660', -53, -13, 93, 32, 5, '#151f20', 1.4);
  rounded(ctx, '#233636', -49, -9, 85, 24, 3);
  const lit = glow ? '#bbe5cc' : '#8bb7ae';
  for (const i of [-33, -20, 0, 13]) {
    rounded(ctx, lit, i, 2, 9.8, 2.5, 1.2);
  }
  ellipse(ctx, lit, -5, 3.2, 1.4, 1.4);
  ellipse(ctx, '#2e3739', -7, 64, 29, 29, '#192426', 2.2);
  ellipse(ctx, null, -7, 64, 23.5, 23.5, '#4e5b57', 1);
  for (const e of [-4, 4]) path(ctx, [[-14 + e, 54], [-3 + e, 64], [-14 + e, 74]], null, '#f4c86d', 2.8);
  rounded(ctx, '#9f584e', 78, 51, 17, 48, 3.2, '#4c3737');
  rounded(ctx, '#d57d65', 90, 49, 7, 57, 2);
  ctx.restore();
}
function plus(ctx, x, y, r, color) {
  rounded(ctx, color, x - r / 4, y - r, r / 2, r * 2, 2);
  rounded(ctx, color, x - r, y - r / 4, r * 2, r / 2, 2);
}
function medKit(ctx, x, y, scale, shade = '#b06f58') {
  ctx.save(); ctx.translate(x, y); ctx.scale(scale, scale);
  ellipse(ctx, '#36514968', 4, 60, 97, 17);
  rounded(ctx, '#4b6153', -39, -79, 76, 31, 8, '#273d3b', 3.3);
  rounded(ctx, '#96aa93', -30, -71, 57, 18, 4.4);
  rounded(ctx, '#6a7059', -85, -55, 175, 107, 20, '#3d5447', 3);
  rounded(ctx, shade, -88, -58, 169, 102, 16, '#5b5144', 3);
  rounded(ctx, null, -79, -49, 151, 85, 12, '#e6c39c', 1.35);
  plus(ctx, -3, -6, 21, '#efe3c5');
  line(ctx, -67, -36, 35, '#a2705e', 2.5);
  ctx.restore();
}
function cabinet(ctx, t) {
  fill(ctx, '#acc5b2', 0, 0, 460, 420);
  path(ctx, [[0, 25], [460, 0], [460, 389], [0, 420]], '#a8bdab');
  path(ctx, [[0, 65], [460, 12], [460, 108], [0, 153]], '#bed0b8');
  path(ctx, [[0, 340], [460, 318], [460, 420], [0, 420]], '#7d9a8b');
  for (let i = 0; i < 10; i++) line(ctx, 35 + i * 43, 354 + i % 3 * 14, 21, '#a0b49a');
  rounded(ctx, '#597c73', 83, 111, 286, 227, 6, '#416154', 3.5);
  rounded(ctx, '#d7dfc3', 99, 120, 249, 198, 4, '#5f8574', 2.7);
  rounded(ctx, '#b1c4ab', 111, 130, 226, 176, 4, '#8ca78f', 2);
  rounded(ctx, '#345d50', 144, 145, 162, 24, 4);
  text(ctx, 'ПЕРВАЯ ПОМОЩЬ', 225, 161, 12, C.cream, { align: 'center', track: 1.3 });
  medKit(ctx, 225, 248 + Math.sin(t * .88) * 2.0, .80);
  rounded(ctx, '#7e9987', 341, 129, 8, 178, 3);
}
function road(ctx, t) {
  fill(ctx, '#aac4b3', 0, 0, 460, 420);
  ellipse(ctx, '#f4cc8b', 369, 87, 37, 37);
  path(ctx, [[0, 214], [93, 147], [177, 184], [271, 141], [460, 209], [460, 420], [0, 420]], '#83a990');
  path(ctx, [[0, 280], [460, 250], [460, 420], [0, 420]], '#7ea18d');
  path(ctx, [[0, 345], [460, 308], [460, 381], [0, 420]], '#4d716b');
  for (let i = 0; i < 12; i++) path(ctx, [[i * 46, 390 - i * 4], [i * 46 + 19, 388 - i * 4]], null, '#c7c5a1', 2);
  ellipse(ctx, '#3959506c', 221, 318, 155, 18);
  path(ctx, [[73, 279], [81, 200], [249, 185], [287, 189], [329, 238], [358, 252],
    [366, 296], [336, 312], [83, 309]], '#d2cda5', '#3a645b', 3.6);
  path(ctx, [[249, 195], [283, 197], [317, 235], [245, 235]], '#6a9589', '#43685d', 2.7);
  path(ctx, [[87, 248], [234, 244], [234, 296], [88, 296]], '#98b4a0', '#668f80', 2.5);
  line(ctx, 102, 253, 120, '#b3c6a7', 2);
  for (const wx of [124, 308]) {
    ellipse(ctx, '#294442', wx, 307, 24, 26);
    ellipse(ctx, '#859c8a', wx, 308, 11, 12);
  }
  medKit(ctx, 220 + 3 * Math.sin(t * .8), 323, .58);
}
export function setArt(ctx, index, t, x, y, w, h) {
  const k = Math.max(w / 460, h / 420) * (1 + .036 * Math.min(t / 2, 1));
  ctx.save(); ctx.beginPath(); ctx.rect(x, y, w, h); ctx.clip();
  ctx.translate(x + (w - 460 * k) / 2, y + (h - 420 * k) / 2); ctx.scale(k, k);
  (index ? road : cabinet)(ctx, t);
  ctx.restore();
}
