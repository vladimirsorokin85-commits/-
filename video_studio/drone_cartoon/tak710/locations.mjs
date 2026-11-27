import { ellipse, fill, line, path, rounded } from '../bulat/art.mjs';

const W = 540, H = 960;
function wash(ctx, from, to, y = H) {
  const paint = ctx.createLinearGradient(0, 0, 0, y);
  paint.addColorStop(0, from); paint.addColorStop(1, to);
  fill(ctx, paint, 0, 0, W, H);
}
function helmet(ctx, x, y, k, t) {
  ctx.save(); ctx.translate(x, y); ctx.scale(k, k);
  ellipse(ctx, '#233d3e64', 5, 0, 38, 11);
  path(ctx, [[-20, -58], [22, -58], [20, -4], [31, 0], [2, 1], [-3, -40], [-9, 0], [-33, 0], [-24, -11]], '#273b42', '#203039', 2.5);
  rounded(ctx, '#cf955d', -25, -110, 53, 60, 12, '#374649', 2.5);
  path(ctx, [[-23, -104], [-8, -104], [-6, -56], [-19, -57]], '#f1bc61');
  path(ctx, [[12, -105], [24, -105], [25, -54], [14, -53]], '#f1bc61');
  path(ctx, [[-17, -74], [24, -76], [24, -67], [-17, -64]], '#eccda1');
  const swing = Math.sin(t * 4.2) * 5;
  path(ctx, [[26, -101], [35, -80], [40 + swing, -74], [35 + swing, -66], [27, -71], [19, -96]], '#a76f53', '#725e51', 2);
  ellipse(ctx, '#e0af86', 0, -124, 15, 18, '#4d554b', 2);
  ellipse(ctx, '#f1bc60', -1, -137, 20, 12, '#7a6d53', 2.1);
  rounded(ctx, '#deb268', -26, -138, 52, 7, 3, '#8d7e60', 1.6);
  ctx.restore();
}
function shop(ctx, t) {
  wash(ctx, '#295152', '#8da782', 740);
  const sun = ctx.createLinearGradient(0, 110, 0, 650);
  sun.addColorStop(0, '#e8d5aa55'); sun.addColorStop(1, '#e8d5aa00');
  path(ctx, [[25, 150], [191, 197], [432, 713], [120, 713]], sun);
  path(ctx, [[0, 189], [540, 265], [540, 458], [0, 375]], '#bfd0ac', '#4e7168', 4);
  for (let i = 0; i < 8; i++) {
    const x = i * 83 - 14;
    path(ctx, [[x, -20], [x + 16, -20], [x + 9, 432], [x - 4, 429]], '#4f6e65');
    path(ctx, [[x, 258 + x * .125], [x + 80, 268 + x * .125]], null, '#78968a', 3);
  }
  for (let i = 0; i < 5; i++) {
    const y = i * 53;
    path(ctx, [[0, y - 80], [540, y + 16], [540, y + 29], [0, y - 65]], '#274849', '#38625c', 1.1);
  }
  for (const x of [73, 268, 445]) {
    path(ctx, [[x, 10], [x, 120], [x + 58, 129]], null, '#203e40', 2.5);
    rounded(ctx, '#c2bda1', x - 37, 120, 108, 5, 2);
    rounded(ctx, '#f0d69d', x - 35, 123, 105, 4, 1);
  }
  path(ctx, [[0, 619], [540, 578], [540, 960], [0, 960]], '#697e71');
  for (let x = -400; x < 1000; x += 114) path(ctx, [[270 + (x - 270) * .22, 606], [x, 960]], null, '#a5a58b', 1.4);
  for (const y of [640, 672, 720, 791, 886]) line(ctx, 0, y, 540, '#879680', 1.3);
  // The foreground aisle, painted steel and conveyor establish a production floor.
  path(ctx, [[305, 687], [540, 606], [540, 626], [307, 714]], '#d9ba74');
  rounded(ctx, '#234648', 12, 370, 247, 297, 9, '#335456', 3.4);
  path(ctx, [[259, 372], [301, 406], [303, 639], [259, 665]], '#54786c', '#2b4f4d', 3.3);
  rounded(ctx, '#6c9482', 23, 386, 226, 210, 5, '#9fbaa1', 2);
  rounded(ctx, '#254647', 37, 401, 193, 135, 7, '#3a615b', 3);
  path(ctx, [[43, 411], [142, 411], [91, 530], [45, 530]], '#527a7044');
  for (let i = 0; i < 7; i++) line(ctx, 51, 553 + i * 10, 147, '#355a53', 2.6);
  rounded(ctx, '#c6b97f', 204, 554, 33, 64, 4, '#4c6e62', 2);
  for (let i = 0; i < 3; i++) ellipse(ctx, i === 1 ? '#d4b269' : '#889b75', 220, 566 + 16 * i, 4, 4);
  path(ctx, [[-30, 676], [350, 603], [396, 631], [0, 726]], '#3f6860', '#254b4d', 3);
  path(ctx, [[-10, 712], [394, 629], [394, 643], [-15, 737]], '#b1b28d', '#547066', 2.2);
  for (let i = 0; i < 9; i++) {
    const x = -14 + ((i * 49 + t * 52) % 422);
    ellipse(ctx, '#78948a', x, 721 - .21 * x, 8.2, 3.3, '#354f4b', 1.3);
  }
  for (let i = 0; i < 3; i++) {
    const x = -15 + ((i * 126 + t * 58) % 372), y = 696 - .22 * x;
    path(ctx, [[x, y], [x + 55, y - 12], [x + 55, y - 52], [x, y - 41]], '#ada982', '#596657', 2.3);
    path(ctx, [[x, y - 41], [x - 21, y - 54], [x + 33, y - 65], [x + 55, y - 52]], '#d1c29b', '#6a7967', 2.2);
    path(ctx, [[x, y], [x - 21, y - 13], [x - 21, y - 54], [x, y - 41]], '#858a73', '#636e5b', 2);
  }
  helmet(ctx, 423 + t * 9, 697 + t * 4, 1.13, t);
}
function cloud(ctx, x, y, r, color) {
  ellipse(ctx, color, x, y, r, r * .14);
  ellipse(ctx, color, x - r * .38, y - r * .065, r * .48, r * .14);
  ellipse(ctx, color, x + r * .2, y - r * .115, r * .51, r * .19);
}
function truck(ctx, x, y, k, t) {
  ctx.save(); ctx.translate(x, y); ctx.scale(k, k); ctx.rotate(-.06);
  ellipse(ctx, '#21353788', -8, 33, 170, 22);
  path(ctx, [[-176, 8], [-168, -63], [-156, -86], [33, -93], [72, -83], [121, -37],
    [163, -21], [180, 2], [176, 29], [133, 35], [-158, 37]], '#d8bb84', '#314b45', 4.3);
  path(ctx, [[-165, -3], [156, -14], [176, 0], [176, 27], [127, 35], [-160, 36]], '#a8ab85', '#536c5f', 2.5);
  path(ctx, [[44, -78], [69, -75], [110, -38], [38, -32]], '#4b7c7b', '#355556', 3);
  path(ctx, [[43, -77], [60, -74], [76, -59], [42, -51]], '#83a697');
  rounded(ctx, '#678982', -145, -72, 151, 46, 5, '#56776a', 2.8);
  path(ctx, [[-140, -68], [-66, -68], [-99, -32], [-139, -32]], '#8aab96');
  path(ctx, [[36, -20], [31, 18], [98, 17]], null, '#8c947c', 2);
  rounded(ctx, '#64796d', 43, -21, 28, 4, 2);
  rounded(ctx, '#f5df9e', 148, -16, 25, 13, 3, '#756e5e', 1.2);
  rounded(ctx, '#c96b57', -172, -17, 13, 20, 3);
  for (const w of [-109, 112]) {
    ellipse(ctx, '#283c3c', w, 30, 27, 27, '#1c3033', 3.4);
    ellipse(ctx, '#7d9588', w, 30, 14.5, 14.5, '#334e4e', 2.1);
    for (let i = 0; i < 4; i++) {
      const a = i * Math.PI / 2 + t * 10.5;
      path(ctx, [[w + 5 * Math.cos(a), 30 + 5 * Math.sin(a)], [w + 11 * Math.cos(a), 30 + 11 * Math.sin(a)]], null, '#c2c6a1', 2);
    }
  }
  ctx.restore();
}
function highway(ctx, t) {
  wash(ctx, '#79a599', '#d9c79f', 650);
  ellipse(ctx, '#f5ce8d', 425, 286, 57, 57);
  cloud(ctx, 122 - 14 * t, 295, 93, '#e5dac0bd');
  cloud(ctx, 358 - 16 * t, 372, 125, '#efdcb5ac');
  path(ctx, [[0, 446], [102, 371], [198, 424], [344, 368], [540, 446], [540, 960], [0, 960]], '#769d8d');
  path(ctx, [[0, 522], [167, 462], [334, 513], [540, 450], [540, 960], [0, 960]], '#628e7f');
  for (let i = 0; i < 10; i++) {
    const x = ((i * 74 - t * 48 + 99) % 690) - 56;
    ellipse(ctx, '#557968', x, 527 - .10 * x + (i % 4) * 12, 31 + (i % 3) * 9, 11 + i % 5 * 3);
  }
  path(ctx, [[0, 618], [540, 516], [540, 766], [0, 919]], '#3a5759', '#325356', 2);
  path(ctx, [[0, 630], [540, 528]], null, '#c5ba91', 3);
  path(ctx, [[0, 899], [540, 751]], null, '#c4b48a', 3);
  for (let i = -1; i <= 7; i++) {
    const x = i * 97 - (t * 114 % 97);
    path(ctx, [[x, 768 - x * .243], [x + 52, 756 - x * .243]], null, '#e8cea0', 3.6);
  }
  truck(ctx, 189 + t * 91, 677 - t * 21, 1.07, t);
  for (let i = 0; i < 8; i++) {
    const x = ((i * 124 - t * 152 + 140) % 960) - 52, y = 914 - x * .24;
    path(ctx, [[x - 4, y + 30], [x + 4, y], [x + 15, y + 27], [x + 12, y + 34]], '#507366');
  }
}
function pine(ctx, x, y, k, green) {
  ctx.save(); ctx.translate(x, y); ctx.scale(k, k);
  rounded(ctx, '#6d7261', -3, -35, 6, 33, 1);
  path(ctx, [[0, -123], [24, -80], [15, -83], [38, -51], [24, -54], [53, -21],
    [7, -30], [-40, -18], [-22, -55], [-33, -53], [-15, -82], [-21, -80]], green);
  ctx.restore();
}
function hiker(ctx, x, y, k, t) {
  ctx.save(); ctx.translate(x, y); ctx.scale(k, k);
  ellipse(ctx, '#284c465f', 5, 0, 40, 10);
  const step = Math.sin(t * 8.3) * 16;
  path(ctx, [[-18, -68], [-3, -68], [-6 + step * .43, -31], [-6 + step, -6],
    [1 + step, -1], [-19 + step, 0], [-22 + step, -14], [-19, -37]], '#3b5351', '#2a4443', 2.2);
  path(ctx, [[4, -66], [20, -66], [15 - step * .46, -34], [17 - step, -6],
    [26 - step, -4], [28 - step, 1], [8 - step, 2], [3 - step, -9], [0, -35]], '#4a6660', '#2a4443', 2.2);
  path(ctx, [[-14, -121], [16, -129], [30, -108], [21, -64], [-22, -65], [-27, -105]], '#bc7154', '#715a4b', 2.8);
  rounded(ctx, '#d2a468', -38, -113, 25, 46, 9, '#685a4a', 2.1);
  path(ctx, [[-24, -112], [-9, -121], [6, -119], [21, -85]], null, '#785f49', 4);
  path(ctx, [[15, -113], [24, -88], [45 - step * .3, -83], [43 - step * .3, -72], [17, -77], [4, -104]], '#ce8d62', '#805d4d', 2.3);
  path(ctx, [[43 - step * .3, -81], [61 + step * .28, -6]], null, '#3c524b', 2.8);
  ellipse(ctx, '#d9ab83', 14, -141, 15, 19, '#6b6452', 2);
  path(ctx, [[-4, -139], [0, -154], [15, -162], [29, -151], [36, -141]], '#bdbf99', '#5f776b', 2);
  ctx.restore();
}
function hills(ctx, t) {
  wash(ctx, '#7ea8a2', '#d8c6a1', 690);
  ellipse(ctx, '#f5d392', 389, 297, 60, 60);
  cloud(ctx, 210 - 15 * t, 379, 154, '#e5dbc0b8');
  cloud(ctx, 491 - 12 * t, 405, 128, '#ebddbeae');
  path(ctx, [[0, 536], [143, 327], [269, 486], [364, 350], [540, 490], [540, 960], [0, 960]], '#6e9a91');
  path(ctx, [[74, 428], [143, 327], [224, 427], [172, 402], [147, 421], [127, 396]], '#b8c9ac');
  path(ctx, [[286, 462], [364, 350], [455, 422], [382, 410], [365, 430], [346, 401]], '#b9c8a8');
  path(ctx, [[0, 567], [154, 470], [292, 579], [434, 458], [540, 496], [540, 960], [0, 960]], '#548677');
  path(ctx, [[0, 662], [149, 574], [351, 640], [540, 571], [540, 960], [0, 960]], '#4d7568');
  for (let i = 0; i < 13; i++) pine(ctx, i * 53 - t * 21 - 22, 670 - i % 5 * 23, .56 + i % 5 * .075, i % 2 ? '#36645e' : '#416c62');
  path(ctx, [[0, 844], [216, 719], [402, 640], [540, 641], [271, 770], [135, 960], [0, 960]], '#ab9f7c', '#7a886e', 2);
  path(ctx, [[0, 915], [189, 781], [333, 716]], null, '#d1ba8e', 3);
  hiker(ctx, 193 + t * 65, 787 - t * 37, 1.38 - t * .12, t);
  pine(ctx, 468 - t * 25, 873, 1.67, '#255853');
  pine(ctx, 548 - t * 30, 925, 2.18, '#224d4b');
}

const sets = [shop, highway, hills];
export function place(ctx, index, t, { x = 0, y = 0, w = W, h = H } = {}) {
  const zoom = 1.02 + .045 * Math.min(t / 1.7, 1);
  const scale = zoom * Math.max(w / W, h / H);
  ctx.save(); ctx.beginPath(); ctx.rect(x, y, w, h); ctx.clip();
  ctx.translate(x + (w - scale * W) / 2, y + (h - scale * H) * (h < 220 ? .67 : .48));
  ctx.scale(scale, scale);
  sets[index](ctx, t);
  ctx.restore();
}
