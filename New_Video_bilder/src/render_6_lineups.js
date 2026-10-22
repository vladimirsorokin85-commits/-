#!/usr/bin/env node
/**
 * High-speed single-browser parallel renderer for all 6 Power Station Lineup Reels
 * (`1080x1920 @ 60 fps`, `1800` frames each = `10,800` frames total, bit-exact deterministic).
 */
const http = require('http');
const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');
const puppeteer = require('puppeteer-core');
const ffmpegPath = require('@ffmpeg-installer/ffmpeg').path;

const PROJECT_ROOT = path.resolve(__dirname, '..');
const REPO_ROOT = path.resolve(PROJECT_ROOT, '..');
const OUT_DIR = '/tmp/power_lineups_pack/v_okope_power_lineups';
const FPS = 60;
const FRAMES = 1800;

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.ttf': 'font/ttf',
  '.woff': 'font/woff',
};

(async () => {
  fs.mkdirSync(OUT_DIR, { recursive: true });
  process.env.LD_LIBRARY_PATH = `/tmp/sp_libs/lib:/tmp/sp_libs:${process.env.LD_LIBRARY_PATH || ''}`;
  const mod = await import('@sparticuz/chromium');
  const execPath = fs.existsSync('/tmp/chromium') ? '/tmp/chromium' : await (mod.default || mod).executablePath();
  const syncMap = JSON.parse(fs.readFileSync(path.join(PROJECT_ROOT, 'src', 'lineups_sync_map.json'), 'utf8'));

  const srv = http.createServer((req, res) => {
    const u = decodeURIComponent(req.url.split('?')[0]);
    let fp = null;
    if (u === '/' || u === '/scene_lineup.html') fp = path.join(PROJECT_ROOT, 'src', 'scene_lineup.html');
    else if (u.startsWith('/src/')) fp = path.join(PROJECT_ROOT, u.slice(1));
    else if (u.startsWith('/fonts/')) fp = path.join(REPO_ROOT, 'video_studio', 'toolkit', 'fonts', path.basename(u));
    else if (u.startsWith('/studio_fonts/')) fp = path.join(REPO_ROOT, 'video_studio', 'fonts', path.basename(u));
    else if (u.startsWith('/assets/')) fp = path.join(PROJECT_ROOT, u.slice(1));
    if (!fp || !fs.existsSync(fp)) { res.writeHead(404); res.end(); return; }
    res.writeHead(200, { 'Content-Type': MIME[path.extname(fp).toLowerCase()] || 'application/octet-stream' });
    fs.createReadStream(fp).pipe(res);
  });
  await new Promise((r) => srv.listen(0, '127.0.0.1', r));
  const port = srv.address().port;

  const browser = await puppeteer.launch({
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-gpu', '--disable-dev-shm-usage', '--font-render-hinting=none'],
    defaultViewport: { width: 1080, height: 1920, deviceScaleFactor: 1 },
    executablePath: execPath,
    headless: true,
  });

  const numWorkers = 2;
  const pages = await Promise.all(
    Array.from({ length: numWorkers }, async () => {
      const p = await browser.newPage();
      await p.goto(`http://127.0.0.1:${port}/scene_lineup.html`, { waitUntil: 'networkidle0' });
      await p.evaluate(() => window.__READY_PROMISE);
      return p;
    })
  );

  for (const slug of Object.keys(syncMap)) {
    const t0 = Date.now();
    const syncObj = syncMap[slug];
    await Promise.all(pages.map((p) => p.evaluate(([sl, syn]) => window.setBrand(sl, syn), [slug, syncObj])));

    // Determinism gate per brand
    const det = await pages[0].evaluate(() => {
      window.renderAt(14.5);
      const a = window.getFrameSignature();
      window.renderAt(3.1);
      window.renderAt(26.2);
      window.renderAt(14.5);
      const b = window.getFrameSignature();
      return { a, b, ok: a === b };
    });
    if (!det.ok) throw new Error(`Determinism failed for ${slug}: ${JSON.stringify(det)}`);

    const outMp4 = path.join(OUT_DIR, `${slug}.mp4`);
    const audioPath = path.join(PROJECT_ROOT, 'assets', 'audio', `master_${slug}.wav`);
    const ff = spawn(ffmpegPath, [
      '-y', '-v', 'error',
      '-f', 'image2pipe', '-vcodec', 'mjpeg', '-framerate', String(FPS), '-i', 'pipe:0',
      '-i', audioPath,
      '-map', '0:v:0', '-map', '1:a:0',
      '-c:v', 'libx264', '-preset', 'veryfast', '-profile:v', 'high', '-crf', '19',
      '-maxrate', '2600k', '-bufsize', '5200k',
      '-pix_fmt', 'yuv420p', '-r', String(FPS), '-vsync', 'cfr',
      '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-ac', '2',
      '-movflags', '+faststart',
      outMp4,
    ], { stdio: ['pipe', 'inherit', 'inherit'] });
    const ffDone = new Promise((res, rej) => ff.on('close', (c) => (c === 0 ? res() : rej(new Error(`FFmpeg exited ${c}`)))));

    const perWorker = 15;
    const step = numWorkers * perWorker;
    for (let base = 0; base < FRAMES; base += step) {
      const batches = await Promise.all(
        pages.map(async (page, wi) => {
          const s = base + wi * perWorker;
          if (s >= FRAMES) return [];
          const e = Math.min(FRAMES, s + perWorker);
          const ts = [];
          for (let k = s; k < e; k++) ts.push(k / FPS);
          const list = await page.evaluate((arr) => {
            const c = document.getElementById('master');
            const out = [];
            for (let j = 0; j < arr.length; j++) {
              window.renderAt(arr[j]);
              out.push(c.toDataURL('image/jpeg', 0.90).slice(23));
            }
            return out;
          }, ts);
          return list.map((b64) => Buffer.from(b64, 'base64'));
        })
      );
      for (const b of batches) {
        for (const buf of b) {
          if (!ff.stdin.write(buf)) await new Promise((r) => ff.stdin.once('drain', r));
        }
      }
    }
    ff.stdin.end();
    await ffDone;
    const mb = (fs.statSync(outMp4).size / 1048576).toFixed(2);
    console.log(`[DONE] ${slug}.mp4 -> ${mb} MB in ${((Date.now() - t0) / 1000).toFixed(1)}s (sig ${det.a})`);
  }

  await browser.close();
  srv.close();
})().catch((e) => { console.error(e); process.exit(1); });
