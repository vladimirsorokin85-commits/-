#!/usr/bin/env node
/**
 * Permanent Broadcast Cover / Thumbnail Generator for «В ОКОПЕ» (New_Video_bilder)
 * Generates BOTH horizontal 16:9 (1920x1080) AND vertical 9:16 (1080x1920) high-CTR covers (< 2 MB JPEG)
 * for all horizontal and vertical videos in output/covers/:
 *   1. zastone_key256_cover_16x9.jpg & zastone_key256_cover_9x16.jpg
 *   2. sidewinder_gen3_cover_16x9.jpg & sidewinder_gen3_cover_9x16.jpg
 *   3. azar_3mx_cover_16x9.jpg       & azar_3mx_cover_9x16.jpg
 *   4. power_stations_cover_16x9.jpg & power_stations_cover_9x16.jpg
 *   5. voevoda_1423_cover_16x9.jpg   & voevoda_1423_cover_9x16.jpg
 *   6. v_okope_store_cover_16x9.jpg  & v_okope_store_cover_9x16.jpg
 */
const http = require("http");
const fs = require("fs");
const path = require("path");
const puppeteer = require("puppeteer-core");

const PROJECT_ROOT = path.resolve(__dirname, "..");
const COVERS_DIR = path.join(PROJECT_ROOT, "output", "covers");

const MIME = {
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
};

const COVER_SPECS = [
  {
    slug: "zastone_key256",
    kicker: "ШИФРОВАННАЯ СВЯЗЬ · КОМПЛЕКТ 2 ШТ.",
    line1: "РАЦИИ «КЛЮЧ 256»",
    line2: "ТОЛЬКО ДЛЯ СВОИХ",
    accent: "#5be38a",
    glow: "rgba(91, 227, 138, 0.30)",
    bg: "/assets/images/bg_radar_dusk.jpg",
    chips: ["AES-256 MOTOROLA", "СПУТНИК 195+ КАНАЛОВ", "ДО 60 КМ · IP67"],
    subline: "ZASTONE DP-UV008 MOD · ПРОШИТЫ ДО ОТГРУЗКИ · ОПТ И РОЗНИЦА · НДС",
    items16: [
      { src: "/assets/zastone_key256/z_full_kit_rgba.png", x: 1030, y: 470, w: 500, h: 470, alpha: 0.96 },
      { src: "/assets/zastone_key256/z_pair_rgba.png",     x: 1385, y: 58,  w: 490, h: 900, alpha: 1.00 },
    ],
    items9: [
      { src: "/assets/zastone_key256/z_full_kit_rgba.png", x: 52,  y: 900, w: 590, h: 485, alpha: 0.97 },
      { src: "/assets/zastone_key256/z_pair_rgba.png",     x: 520, y: 635, w: 505, h: 760, alpha: 1.00 },
    ],
  },
  {
    slug: "sidewinder_gen3",
    kicker: "ТАКТИЧЕСКИЙ ШЛЕМНЫЙ ФОНАРЬ",
    line1: "SIDEWINDER GEN_3",
    line2: "4 ЦВЕТА + ИК-РЕЖИМ",
    accent: "#f6d88c",
    glow: "rgba(246, 216, 140, 0.28)",
    bg: "/assets/images/bg_trench_dugout_dusk.jpg",
    chips: ["БЕЛЫЙ · КРАСНЫЙ · СИНИЙ · ИК", "СТРОБОСКОП В 2 КЛИКА", "ПОВОРОТ 360° · КЕЙС"],
    subline: "КРЕПЛЕНИЯ ARC / ПНВ / MOLLE В КОМПЛЕКТЕ · ОПТ И РОЗНИЦА · С НДС И БЕЗ НДС",
    items16: [
      { src: "/assets/sidewinder_gen3/sw_opencase_rgba.png", x: 1015, y: 430, w: 520, h: 520, alpha: 0.96 },
      { src: "/assets/sidewinder_gen3/sw_front_rgba.png",    x: 1390, y: 74,  w: 475, h: 885, alpha: 1.00 },
    ],
    items9: [
      { src: "/assets/sidewinder_gen3/sw_opencase_rgba.png", x: 56,  y: 855, w: 530, h: 530, alpha: 0.96 },
      { src: "/assets/sidewinder_gen3/sw_front_rgba.png",    x: 505, y: 645, w: 515, h: 745, alpha: 1.00 },
    ],
  },
  {
    slug: "azar_3mx",
    kicker: "РАДИОЭЛЕКТРОННАЯ РАЗВЕДКА · 3MX",
    line1: "ПЕРЕХВАТ «АЗАР»",
    line2: "ГЛАЗАМИ FPV-ДРОНА",
    accent: "#59c8ff",
    glow: "rgba(89, 200, 255, 0.30)",
    bg: "/assets/images/bg_radar_dusk.jpg",
    chips: ["300–12 000 МГЦ", "ДАЛЬНОСТЬ ДО 1,5 КМ", "ТАНДЕМ С «БУЛАТ» В.4"],
    subline: "ВЫВОД ВИДЕО НА ВНЕШНИЙ МОНИТОР · ДО 6,5 Ч · ОРИГИНАЛ 3MX С ПАСПОРТОМ",
    items16: [
      { src: "/assets/azar_3mx/azar_kit_standing_rgba.png", x: 1055, y: 56, w: 820, h: 905, alpha: 1.00 },
    ],
    items9: [
      { src: "/assets/azar_3mx/azar_kit_standing_rgba.png", x: 90,   y: 635, w: 900, h: 760, alpha: 1.00 },
    ],
  },
  {
    slug: "power_stations",
    kicker: "АВТОНОМНОЕ ПИТАНИЕ ПОЗИЦИЙ И РЭБ",
    line1: "ЗАРЯДНЫЕ СТАНЦИИ",
    line2: "17 МОДЕЛЕЙ В СТРОЮ",
    accent: "#5be38a",
    glow: "rgba(91, 227, 138, 0.28)",
    bg: "/assets/images/bg_military_crates_olive.jpg",
    chips: ["DJI · ECOFLOW DELTA", "JACKERY · BLUETTI", "JQB · ALLPOWERS"],
    subline: "ТИХАЯ ТЯГА ДЛЯ БЛИНДАЖЕЙ, СВЯЗИ И БПЛА · ОПТОМ И В РОЗНИЦУ · НДС",
    items16: [
      { src: "/assets/real_power/dji_power_2000_rgba.png",     x: 1015, y: 455, w: 470, h: 490, alpha: 0.97 },
      { src: "/assets/real_power/jackery_2000_v2_rgba.png",    x: 1415, y: 445, w: 465, h: 505, alpha: 0.98 },
      { src: "/assets/real_power/ecoflow_delta_pro3_rgba.png", x: 1185, y: 80,  w: 540, h: 590, alpha: 1.00 },
    ],
    items9: [
      { src: "/assets/real_power/dji_power_2000_rgba.png",     x: 56,  y: 900, w: 470, h: 480, alpha: 0.97 },
      { src: "/assets/real_power/jackery_2000_v2_rgba.png",    x: 554, y: 890, w: 470, h: 495, alpha: 0.98 },
      { src: "/assets/real_power/ecoflow_delta_pro3_rgba.png", x: 255, y: 635, w: 570, h: 520, alpha: 1.00 },
    ],
  },
  {
    slug: "voevoda_1423",
    kicker: "КОМПЛЕКС БРОНЕЗАЩИТЫ · ООО «ВАРЯГ»",
    line1: "ВОЕВОДА 14/23",
    line2: "ПОЛНЫЙ КОНТУР БРОНИ",
    accent: "#f6d88c",
    glow: "rgba(246, 216, 140, 0.28)",
    bg: "/assets/images/bg_armor_plate_camo.jpg",
    chips: ["СВМПЭ Бр1 / С2", "КЕРАМИКА Бр5", "БЫСТРОСБРОС ROC"],
    subline: "ГОСТ 34286-2017 · 4 КОМПЛЕКТАЦИИ · ОПТОМ И В РОЗНИЦУ · С НДС И БЕЗ НДС",
    items16: [
      { src: "/assets/real_products/real_br5_plates_rgba.png",   x: 1015, y: 470, w: 430, h: 485, alpha: 0.97 },
      { src: "/assets/real_products/real_voevoda_hero_rgba.png", x: 1320, y: 54,  w: 555, h: 910, alpha: 1.00 },
    ],
    items9: [
      { src: "/assets/real_products/real_br5_plates_rgba.png",   x: 60,  y: 915, w: 430, h: 470, alpha: 0.97 },
      { src: "/assets/real_products/real_voevoda_hero_rgba.png", x: 405, y: 630, w: 620, h: 770, alpha: 1.00 },
    ],
  },
  {
    slug: "v_okope_store",
    kicker: "ПРЯМЫЕ ПОСТАВКИ СНАРЯЖЕНИЯ ПО РОССИИ",
    line1: "МАГАЗИН «В ОКОПЕ»",
    line2: "БРОНЯ · РЭБ · СВЯЗЬ",
    accent: "#5be38a",
    glow: "rgba(91, 227, 138, 0.28)",
    bg: "/assets/images/bg_military_crates_olive.jpg",
    chips: ["ЗАВОДСКОЙ ОТК", "ОПТ И РОЗНИЦА", "С НДС И БЕЗ НДС"],
    subline: "t.me/vokope_ru  ·  vk.com/vokope_rus  ·  МАГАЗИН НА АВИТО «В ОКОПЕ»",
    items16: [
      { src: "/assets/real_products/real_reb_romashka8_rgba.png", x: 1010, y: 120, w: 470, h: 820, alpha: 0.96 },
      { src: "/assets/real_products/real_voevoda_hero_rgba.png",  x: 1355, y: 62,  w: 525, h: 900, alpha: 1.00 },
    ],
    items9: [
      { src: "/assets/real_products/real_reb_romashka8_rgba.png", x: 58,  y: 675, w: 470, h: 705, alpha: 0.96 },
      { src: "/assets/real_products/real_voevoda_hero_rgba.png",  x: 430, y: 635, w: 595, h: 760, alpha: 1.00 },
    ],
  },
  {
    slug: "tyt_mduv390",
    kicker: "ЦИФРОВАЯ РАДИОСТАНЦИЯ · DMR + АНАЛОГ",
    line1: "TYT MD-UV390 PLUS",
    line2: "10 ВТ · AES-256 · IP67",
    accent: "#4ae88a",
    glow: "rgba(74, 232, 138, 0.30)",
    bg: "/assets/images/bg_radar_dusk.jpg",
    chips: ["AES-256 ШИФРОВАНИЕ", "АКБ 3600 TYPE-C", "2 АНТЕННЫ 12/38 СМ"],
    subline: "136–174 / 400–480 МГц · ДОП. АКБ В НАЛИЧИИ · ОПТ И РОЗНИЦА · С НДС И БЕЗ НДС",
    items16: [
      { src: "/assets/tyt_mduv390/tyt_kit_front_rgba.png",       x: 1042, y: 505, w: 495, h: 465, alpha: 0.98 },
      { src: "/assets/tyt_mduv390/tyt_handset_upright_rgba.png", x: 1418, y: 54,  w: 465, h: 910, alpha: 1.00 },
    ],
    items9: [
      { src: "/assets/tyt_mduv390/tyt_kit_front_rgba.png",       x: 52,   y: 895, w: 575, h: 495, alpha: 0.97 },
      { src: "/assets/tyt_mduv390/tyt_handset_upright_rgba.png", x: 520,  y: 635, w: 510, h: 765, alpha: 1.00 },
    ],
  },
  {
    slug: "aldan12",
    kicker: "ДРОН-ДЕТЕКТОР БПЛА · ЧАСЫ В ПОДАРОК",
    line1: "«АЛДАН-12»",
    line2: "100 МГц – 13 ГГц",
    accent: "#f6d88c",
    glow: "rgba(246, 216, 140, 0.30)",
    bg: "/assets/images/bg_radar_dusk.jpg",
    chips: ["360° · ДО 1000 М · 9 БПЛА", "ФИЛЬТР РАЦИЙ 425–445 МГц", "ДО 15 Ч · 2 АКБ + ЧАСЫ"],
    subline: "DJI · FPV · AUTEL · 298 Г · ДЕКЛАРАЦИЯ ЕАЭС ДО 2030 Г. · ОПТ И РОЗНИЦА · НДС",
    items16: [
      { src: "/assets/aldan_12/aldan_watch_rgba.png", x: 1030, y: 630, w: 300, h: 325, alpha: 0.99 },
      { src: "/assets/aldan_12/aldan_pair_rgba.png",  x: 1275, y: 42,  w: 615, h: 925, alpha: 1.00 },
    ],
    items9: [
      { src: "/assets/aldan_12/aldan_watch_rgba.png", x: 64,   y: 995, w: 325, h: 375, alpha: 0.99 },
      { src: "/assets/aldan_12/aldan_pair_rgba.png",  x: 345,  y: 625, w: 690, h: 775, alpha: 1.00 },
    ],
  },
  {
    slug: "detectors_guide",
    kicker: "ПОЛНЫЙ РАЗБОР · 19 ПОЗИЦИЙ В ОДНОМ ВИДЕО",
    line1: "ВСЕ ДЕТЕКТОРЫ БПЛА",
    line2: "100 МГц – 13 ГГц",
    accent: "#56e68a",
    glow: "rgba(86, 230, 138, 0.30)",
    bg: "/assets/images/bg_radar_dusk.jpg",
    chips: ["АЛДАН-8/12 · БУЛАТ · МАРС", "ДИСПЕТЧЕР 135+ / 835+", "ASEL · ТЕНЬ V4 · ТАИР"],
    subline: "4 ЭШЕЛОНА РАДИОРАЗВЕДКИ · ПЕРЕХВАТ ВИДЕО · ОПТОМ И В РОЗНИЦУ · НДС",
    items16: [
      { src: "/assets/detectors_lineup/dispetcher_835.png", x: 995,  y: 500, w: 530, h: 465, alpha: 0.99 },
      { src: "/assets/detectors_lineup/aldan_trio.png",     x: 1385, y: 46,  w: 505, h: 920, alpha: 1.00 },
    ],
    items9: [
      { src: "/assets/detectors_lineup/dispetcher_835.png", x: 46,   y: 910, w: 560, h: 485, alpha: 0.99 },
      { src: "/assets/detectors_lineup/aldan_trio.png",     x: 470,  y: 625, w: 565, h: 775, alpha: 1.00 },
    ],
  },
  {
    slug: "runcam_helmet2",
    kicker: "НОВИНКА // ТАКТИЧЕСКАЯ ЭКИПИРОВКА",
    line1: "RUNCAM HELMET 2",
    line2: "ГИБКИЙ ОБЪЕКТИВ // F/1.6",
    accent: "#ff6a00",
    glow: "rgba(255, 106, 0, 0.35)",
    bg: "/assets/images/bg_radar_dusk.jpg",
    chips: ["ГИБКАЯ ШЕЙКА ПО ЛИНИИ ВЗГЛЯДА", "8 ЧАСОВ ЗАПИСИ ОТ 18650", "IP67 / ВИБРООТКЛИК БЕЗ ДИОДОВ"],
    subline: "1080P @ 60 FPS · СВЕТОСИЛА F/1.6 · СЛАЙДЕР В ПЕРЧАТКАХ · В НАЛИЧИИ В ОКОПЕ",
    items16: [
      { src: "/assets/runcam_helmet2/runcam_hero_iso_rgba.png", x: 1060, y: 90, w: 800, h: 800, alpha: 1.00 },
      { src: "/assets/runcam_helmet2/runcam_full_kit_rgba.png", x: 1390, y: 490, w: 500, h: 500, alpha: 0.94 },
    ],
    items9: [
      { src: "/assets/runcam_helmet2/runcam_hero_iso_rgba.png", x: 90, y: 560, w: 900, h: 900, alpha: 1.00 },
    ],
  },
  {
    slug: "pole31",
    kicker: "НОВИНКА НПО «КИЛОВАТТ» · СТАНЦИЯ РЭБ",
    line1: "«ПОЛЕ-31» · 240 ВТ",
    line2: "СРЫВ СПУТНИКОВ ≥ 2 КМ",
    accent: "#56e68a",
    glow: "rgba(86, 230, 138, 0.30)",
    bg: "/assets/images/bg_radar_dusk.jpg",
    chips: ["1162–1300 / 1550–1630 МГц", "GPS · ГЛОНАСС · BEIDOU · GALILEO", "КУПОЛ 900×300 · ЛЮБОЙ ЦВЕТ"],
    subline: "РАБОТА 24/7 · 12В / 24В / 220В · СКИДКИ ВОЕННЫМ, ФОНДАМ И НА ОПТ · НДС",
    items16: [
      { src: "/assets/pole_31/dome_silver_rgba.png", x: 1125, y: 108, w: 540, h: 390, alpha: 0.96 },
      { src: "/assets/pole_31/dome_green_rgba.png",  x: 982,  y: 388, w: 862, h: 585, alpha: 1.00 },
    ],
    items9: [
      { src: "/assets/pole_31/dome_silver_rgba.png", x: 515,  y: 635, w: 505, h: 375, alpha: 0.96 },
      { src: "/assets/pole_31/dome_green_rgba.png",  x: 64,   y: 825, w: 835, h: 575, alpha: 1.00 },
    ],
  },
];

function startAssetServer() {
  return new Promise((resolve) => {
    const srv = http.createServer((req, res) => {
      const urlPath = decodeURIComponent(req.url.split("?")[0]);
      if (urlPath === "/cover.html") {
        res.writeHead(200, { "Content-Type": "text/html; charset=utf-8" });
        res.end(`<!doctype html><html><body style="margin:0;background:#000"><canvas id="c"></canvas><script>${RENDER_FN_SCRIPT}</script></body></html>`);
        return;
      }
      const filePath = path.join(PROJECT_ROOT, urlPath.slice(1));
      if (!fs.existsSync(filePath)) {
        res.writeHead(404);
        res.end("Not found");
        return;
      }
      const ext = path.extname(filePath).toLowerCase();
      res.writeHead(200, { "Content-Type": MIME[ext] || "application/octet-stream" });
      fs.createReadStream(filePath).pipe(res);
    });
    srv.listen(0, "127.0.0.1", () => resolve({ server: srv, port: srv.address().port }));
  });
}

const RENDER_FN_SCRIPT = `
async function renderCoverCanvas(spec, orient) {
  const isWide = orient === "16x9";
  const W = isWide ? 1920 : 1080;
  const H = isWide ? 1080 : 1920;

  const canvas = document.getElementById("c");
  canvas.width = W;
  canvas.height = H;
  const ctx = canvas.getContext("2d", { alpha: false });

  const loadImg = (src) => new Promise((res, rej) => {
    const im = new Image();
    im.onload = () => res(im);
    im.onerror = () => rej(new Error("Missing " + src));
    im.src = src;
  });

  const logoFull = await loadImg("/assets/brand/logo_full_sand.png");
  const bgImg = await loadImg(spec.bg);
  const items = isWide ? spec.items16 : spec.items9;
  const loadedItems = await Promise.all(items.map(async (it) => ({ ...it, img: await loadImg(it.src) })));

  function rr(x, y, w, h, r) {
    ctx.beginPath();
    ctx.roundRect(x, y, w, h, r);
  }
  function fitText(text, x, y, maxW, maxPx, weight = 900, color = "#fff", align = "left") {
    let sz = maxPx;
    while (sz > 14) {
      ctx.font = weight + " " + sz + "px 'Liberation Sans', 'DejaVu Sans', Arial, sans-serif";
      if (ctx.measureText(text).width <= maxW) break;
      sz -= 1;
    }
    ctx.save();
    ctx.shadowColor = "rgba(0,0,0,0.82)";
    ctx.shadowBlur = 22;
    ctx.shadowOffsetY = 6;
    ctx.fillStyle = color;
    ctx.textAlign = align;
    ctx.textBaseline = "alphabetic";
    ctx.fillText(text, x, y);
    ctx.restore();
  }
  function drawContain(im, x, y, w, h, alpha = 1.0) {
    const sc = Math.min(w / im.width, h / im.height);
    const dw = im.width * sc, dh = im.height * sc;
    const dx = x + (w - dw) / 2, dy = y + (h - dh) / 2;
    ctx.save();
    ctx.globalAlpha = alpha;
    ctx.shadowColor = "rgba(0, 0, 0, 0.92)";
    ctx.shadowBlur = 46;
    ctx.shadowOffsetY = 22;
    ctx.drawImage(im, dx, dy, dw, dh);
    ctx.restore();
  }

  // 1. Dark atmospheric military backdrop + high-contrast vignette
  ctx.fillStyle = "#060906";
  ctx.fillRect(0, 0, W, H);
  ctx.save();
  ctx.globalAlpha = 0.24;
  const scBg = Math.max(W / bgImg.width, H / bgImg.height) * 1.04;
  ctx.drawImage(bgImg, (W - bgImg.width * scBg) / 2, (H - bgImg.height * scBg) / 2, bgImg.width * scBg, bgImg.height * scBg);
  ctx.restore();

  const vg = ctx.createLinearGradient(0, 0, isWide ? W : 0, isWide ? 0 : H);
  if (isWide) {
    vg.addColorStop(0.0, "rgba(7, 11, 8, 0.95)");
    vg.addColorStop(0.54, "rgba(10, 16, 11, 0.85)");
    vg.addColorStop(1.0, "rgba(14, 24, 15, 0.66)");
  } else {
    vg.addColorStop(0.0, "rgba(7, 11, 8, 0.94)");
    vg.addColorStop(0.50, "rgba(12, 20, 13, 0.74)");
    vg.addColorStop(1.0, "rgba(6, 10, 7, 0.96)");
  }
  ctx.fillStyle = vg;
  ctx.fillRect(0, 0, W, H);

  // Subtle tactical grid
  ctx.strokeStyle = "rgba(140, 185, 140, 0.055)";
  ctx.lineWidth = 1;
  for (let x = 0; x <= W; x += 80) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke(); }
  for (let y = 0; y <= H; y += 80) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke(); }

  // Radial glow behind product hero
  const gx = isWide ? 1455 : 540;
  const gy = isWide ? 520 : 1015;
  const gr = isWide ? 560 : 500;
  const rg = ctx.createRadialGradient(gx, gy, 40, gx, gy, gr);
  rg.addColorStop(0, spec.glow);
  rg.addColorStop(0.62, "rgba(25, 42, 26, 0.14)");
  rg.addColorStop(1, "rgba(0, 0, 0, 0)");
  ctx.fillStyle = rg;
  ctx.fillRect(0, 0, W, H);

  // Chamfered tactical border frame
  ctx.strokeStyle = "rgba(216, 178, 99, 0.42)";
  ctx.lineWidth = 2.5;
  rr(28, 28, W - 56, H - 56, 26);
  ctx.stroke();

  if (isWide) {
    // ===================== 16:9 WIDESCREEN HIGH-CTR LAYOUT (1920x1080) =====================
    // Brand Header [x=84, y=72]
    rr(84, 68, 360, 114, 18);
    ctx.fillStyle = "rgba(9, 14, 9, 0.90)";
    ctx.fill();
    ctx.lineWidth = 2;
    ctx.strokeStyle = "rgba(216, 178, 99, 0.55)";
    ctx.stroke();
    drawContain(logoFull, 102, 76, 324, 98);

    // Kicker Pill
    rr(84, 214, 640, 52, 12);
    ctx.fillStyle = "rgba(216, 178, 99, 0.17)";
    ctx.fill();
    ctx.lineWidth = 2;
    ctx.strokeStyle = "rgba(246, 216, 140, 0.65)";
    ctx.stroke();
    fitText("◆  " + spec.kicker, 110, 249, 590, 24, 900, "#f6d88c");

    // Massive 2-Line Click-Magnet Poster Title
    fitText(spec.line1, 84, 392, 960, 104, 900, "#ffffff");
    fitText(spec.line2, 84, 506, 960, 98, 900, spec.accent);

    // 3 High-Contrast Spec Chips
    spec.chips.forEach((ch, idx) => {
      const cy = 562 + idx * 102;
      rr(84, cy, 740, 82, 16);
      ctx.fillStyle = idx === 0 ? "rgba(22, 52, 30, 0.93)" : "rgba(15, 22, 16, 0.92)";
      ctx.fill();
      ctx.lineWidth = 2.2;
      ctx.strokeStyle = idx === 0 ? spec.accent : "rgba(216, 178, 99, 0.48)";
      ctx.stroke();
      fitText("✓  " + ch, 118, cy + 52, 676, 33, 900, idx === 0 ? spec.accent : "#ffffff");
    });

    // Bottom Left Subline (keeps x > 1620, y > 960 completely free for YouTube 02:30 badge!)
    fitText(spec.subline, 84, 998, 1460, 23, 800, "#d8b263");

    // Draw Real Studio Cutouts on Right Stage
    for (const it of loadedItems) {
      drawContain(it.img, it.x, it.y, it.w, it.h, it.alpha);
    }
  } else {
    // ===================== 9:16 VERTICAL SAFE-ZONE POSTER (1080x1920) =====================
    // All vital content strictly inside y = 175 .. 1715 so neither Shorts/Reels UI nor 4:5 profile crop clips anything!
    rr(290, 172, 500, 134, 22);
    ctx.fillStyle = "rgba(9, 14, 9, 0.92)";
    ctx.fill();
    ctx.lineWidth = 2;
    ctx.strokeStyle = "rgba(216, 178, 99, 0.58)";
    ctx.stroke();
    drawContain(logoFull, 314, 182, 452, 114);

    // Kicker Pill Centered
    rr(96, 332, 888, 54, 13);
    ctx.fillStyle = "rgba(216, 178, 99, 0.17)";
    ctx.fill();
    ctx.lineWidth = 2;
    ctx.strokeStyle = "rgba(246, 216, 140, 0.65)";
    ctx.stroke();
    fitText("◆  " + spec.kicker, 540, 368, 836, 25, 900, "#f6d88c", "center");

    // Giant 2-Line Poster Title
    fitText(spec.line1, 540, 492, 956, 94, 900, "#ffffff", "center");
    fitText(spec.line2, 540, 594, 956, 88, 900, spec.accent, "center");

    // Center Hero Studio Product Stage [y = 630 .. 1405]
    for (const it of loadedItems) {
      drawContain(it.img, it.x, it.y, it.w, it.h, it.alpha);
    }

    // 3 Bold Stacked Spec Pills in Lower Safe Zone [y = 1380 .. 1624 — 296px clear bottom margin!]
    spec.chips.forEach((ch, idx) => {
      const cy = 1380 + idx * 88;
      rr(84, cy, 912, 74, 16);
      ctx.fillStyle = idx === 0 ? "rgba(22, 52, 30, 0.95)" : "rgba(14, 21, 15, 0.94)";
      ctx.fill();
      ctx.lineWidth = 2.2;
      ctx.strokeStyle = idx === 0 ? spec.accent : "rgba(216, 178, 99, 0.48)";
      ctx.stroke();
      fitText("✓  " + ch, 540, cy + 48, 850, 31, 900, idx === 0 ? spec.accent : "#ffffff", "center");
    });
  }

  return canvas.toDataURL("image/jpeg", 0.94).slice(23);
}
`;

(async () => {
  const zlib = require("zlib");
  const { execSync } = require("child_process");
  if (!fs.existsSync("/tmp/sp_libs/lib/libnspr4.so")) {
    fs.mkdirSync("/tmp/sp_libs", { recursive: true });
    const brPath = path.join(PROJECT_ROOT, "node_modules", "@sparticuz", "chromium", "bin", "al2023.tar.br");
    fs.writeFileSync("/tmp/sp_libs/al2023.tar", zlib.brotliDecompressSync(fs.readFileSync(brPath)));
    execSync("tar -xf /tmp/sp_libs/al2023.tar -C /tmp/sp_libs");
  }
  process.env.LD_LIBRARY_PATH = `/tmp/sp_libs/lib:/tmp/sp_libs:${process.env.LD_LIBRARY_PATH || ""}`;
  let execPath = "/tmp/chromium";
  if (!fs.existsSync(execPath)) {
    const mod = await import("@sparticuz/chromium");
    execPath = await (mod.default || mod).executablePath();
  }
  fs.mkdirSync(COVERS_DIR, { recursive: true });
  const { server, port } = await startAssetServer();

  const browser = await puppeteer.launch({
    executablePath: execPath,
    headless: true,
    defaultViewport: { width: 1920, height: 1920, deviceScaleFactor: 1 },
    args: ["--no-sandbox", "--disable-setuid-sandbox", "--disable-gpu", "--disable-dev-shm-usage"],
  });

  try {
    const page = await browser.newPage();
    await page.goto(`http://127.0.0.1:${port}/cover.html`, { waitUntil: "load" });

    for (const spec of COVER_SPECS) {
      for (const orient of ["16x9", "9x16"]) {
        const b64 = await page.evaluate(({ s, o }) => renderCoverCanvas(s, o), { s: spec, o: orient });
        const outPath = path.join(COVERS_DIR, `${spec.slug}_cover_${orient}.jpg`);
        const buf = Buffer.from(b64, "base64");
        fs.writeFileSync(outPath, buf);
        const kb = (buf.length / 1024).toFixed(0);
        if (buf.length >= 2 * 1024 * 1024) {
          throw new Error(`Cover ${outPath} exceeds 2 MB YouTube limit (${kb} KB)!`);
        }
        console.log(`  Generated ${path.basename(outPath)} (${kb} KB)`);
      }
    }
  } finally {
    await browser.close();
    server.close();
  }
})();
