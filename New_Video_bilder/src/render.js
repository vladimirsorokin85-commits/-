#!/usr/bin/env node
/**
 * High-speed deterministic 2-worker parallel 60fps Chromium renderer for New_Video_bilder.
 * Unpacks Chromium runtime libs automatically if needed, verifies bit-exact cold-seek / rewind
 * determinism (maxColdRew === 0, maxFwdRew === 0), renders all frames in parallel batches across
 * workers directly into FFmpeg (H.264 High profile, yuv420p, exact 60/1 CFR, AAC 256k stereo).
 */
const http = require('http');
const fs = require('fs');
const os = require('os');
const path = require('path');
const zlib = require('zlib');
const { spawn, execSync } = require('child_process');
const puppeteer = require('puppeteer-core');
const chromiumMod = require('@sparticuz/chromium');
const chromium = chromiumMod.default || chromiumMod;
const ffmpegPath = require('@ffmpeg-installer/ffmpeg').path;

const PROJECT_ROOT = path.resolve(__dirname, '..');
const REPO_ROOT = path.resolve(PROJECT_ROOT, '..');
const FPS = 60;

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.ttf': 'font/ttf',
  '.woff': 'font/woff',
  '.wav': 'audio/wav',
  '.mp3': 'audio/mpeg',
};

function ensureRuntimeLibs() {
  const libDir = '/tmp/sp_libs/lib';
  if (!fs.existsSync(path.join(libDir, 'libnspr4.so'))) {
    fs.mkdirSync('/tmp/sp_libs', { recursive: true });
    for (const name of ['al2023.tar']) {
      const brPath = path.join(PROJECT_ROOT, 'node_modules', '@sparticuz', 'chromium', 'bin', `${name}.br`);
      const raw = zlib.brotliDecompressSync(fs.readFileSync(brPath));
      fs.writeFileSync(`/tmp/sp_libs/${name}`, raw);
      execSync(`tar -xf /tmp/sp_libs/${name} -C /tmp/sp_libs`);
    }
  }
  process.env.LD_LIBRARY_PATH = `/tmp/sp_libs/lib:/tmp/sp_libs:${process.env.LD_LIBRARY_PATH || ''}`;
}

function startStaticServer() {
  return new Promise((resolve) => {
    const srv = http.createServer((req, res) => {
      const urlPath = decodeURIComponent(req.url.split('?')[0]);
      let filePath = null;
      if (urlPath === '/' || urlPath === '/scene.html') {
        filePath = path.join(PROJECT_ROOT, 'src', 'scene.html');
      } else if (urlPath.startsWith('/vendor/')) {
        filePath = path.join(PROJECT_ROOT, 'node_modules', 'three', 'build', path.basename(urlPath));
      } else if (urlPath.startsWith('/fonts/')) {
        filePath = path.join(REPO_ROOT, 'video_studio', 'toolkit', 'fonts', path.basename(urlPath));
      } else if (urlPath.startsWith('/studio_fonts/')) {
        filePath = path.join(REPO_ROOT, 'video_studio', 'fonts', path.basename(urlPath));
      } else if (urlPath.startsWith('/assets/')) {
        filePath = path.join(PROJECT_ROOT, urlPath.slice(1));
      }
      if (!filePath || !fs.existsSync(filePath)) {
        res.writeHead(404);
        res.end('Not found: ' + urlPath);
        return;
      }
      const ext = path.extname(filePath).toLowerCase();
      res.writeHead(200, { 'Content-Type': MIME[ext] || 'application/octet-stream' });
      fs.createReadStream(filePath).pipe(res);
    });
    srv.listen(0, '127.0.0.1', () => {
      resolve({ server: srv, port: srv.address().port });
    });
  });
}

async function renderSegment({ browserUrl, startFrame, frameCount, audioPath, audioOffsetSec, outMp4 }) {
  ensureRuntimeLibs();
  const execPath = await chromium.executablePath();
  const numWorkers = Math.max(2, Math.min(4, os.cpus().length));

  const browser = await puppeteer.launch({
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-gpu',
      '--disable-dev-shm-usage',
      '--hide-scrollbars',
      '--font-render-hinting=none',
    ],
    defaultViewport: { width: 1080, height: 1920, deviceScaleFactor: 1 },
    executablePath: execPath,
    headless: true,
  });

  const pages = await Promise.all(
    Array.from({ length: numWorkers }, async () => {
      const p = await browser.newPage();
      p.on('pageerror', (err) => console.error('[PAGE EXC]', err));
      await p.goto(browserUrl, { waitUntil: 'networkidle0' });
      await p.evaluate(() => window.__READY_PROMISE);
      return p;
    })
  );

  // Strict Cold-Seek vs Forward-Play vs Backward-Rewind Bit-Exact Determinism Gate
  const seekCheck = await pages[0].evaluate(() => {
    const c2d = document.getElementById('master').getContext('2d');
    window.renderAt(16.25);
    const coldHash = window.getFrameSignature();
    const coldBuf = new Uint8Array(c2d.getImageData(0, 0, 1080, 1920).data);

    window.renderAt(2.10);
    window.renderAt(9.45);
    window.renderAt(16.25);
    const forwardHash = window.getFrameSignature();
    const fwdBuf = new Uint8Array(c2d.getImageData(0, 0, 1080, 1920).data);

    window.renderAt(27.80);
    window.renderAt(16.25);
    const rewindHash = window.getFrameSignature();
    const rewBuf = new Uint8Array(c2d.getImageData(0, 0, 1080, 1920).data);

    let maxColdRew = 0;
    let maxFwdRew = 0;
    for (let i = 0; i < coldBuf.length; i += 4) {
      const dCR = Math.max(
        Math.abs(coldBuf[i] - rewBuf[i]),
        Math.abs(coldBuf[i + 1] - rewBuf[i + 1]),
        Math.abs(coldBuf[i + 2] - rewBuf[i + 2])
      );
      const dFR = Math.max(
        Math.abs(fwdBuf[i] - rewBuf[i]),
        Math.abs(fwdBuf[i + 1] - rewBuf[i + 1]),
        Math.abs(fwdBuf[i + 2] - rewBuf[i + 2])
      );
      if (dCR > maxColdRew) maxColdRew = dCR;
      if (dFR > maxFwdRew) maxFwdRew = dFR;
    }
    return {
      coldHash,
      forwardHash,
      rewindHash,
      maxColdRew,
      maxFwdRew,
      deterministic: maxColdRew === 0 && maxFwdRew === 0,
    };
  });
  console.log('[DETERMINISM CHECK]', JSON.stringify(seekCheck));
  if (!seekCheck.deterministic) {
    throw new Error('Strict 0-diff determinism check FAILED: ' + JSON.stringify(seekCheck));
  }

  fs.mkdirSync(path.dirname(outMp4), { recursive: true });
  const durSec = (frameCount / FPS).toFixed(6);

  const ffArgs = [
    '-y',
    '-v', 'error',
    '-f', 'image2pipe',
    '-vcodec', 'mjpeg',
    '-framerate', String(FPS),
    '-i', 'pipe:0',
    '-ss', audioOffsetSec.toFixed(6),
    '-t', durSec,
    '-i', audioPath,
    '-map', '0:v:0',
    '-map', '1:a:0',
    '-c:v', 'libx264',
    '-preset', 'medium',
    '-profile:v', 'high',
    '-crf', '17',
    '-pix_fmt', 'yuv420p',
    '-r', String(FPS),
    '-vsync', 'cfr',
    '-c:a', 'aac',
    '-b:a', '256k',
    '-ar', '48000',
    '-ac', '2',
    '-movflags', '+faststart',
    outMp4,
  ];

  const ff = spawn(ffmpegPath, ffArgs, { stdio: ['pipe', 'inherit', 'inherit'] });
  const ffDone = new Promise((resolve, reject) => {
    ff.on('close', (code) => (code === 0 ? resolve() : reject(new Error(`FFmpeg exited ${code}`))));
  });

  const t0 = Date.now();
  // Batch 8 frames per worker inside Chromium using fast native canvas JPEG encode -> minimal IPC overhead!
  const perWorker = 8;
  const stepSize = numWorkers * perWorker;

  for (let base = 0; base < frameCount; base += stepSize) {
    const workerResults = await Promise.all(
      pages.map(async (page, wIdx) => {
        const subStart = base + wIdx * perWorker;
        if (subStart >= frameCount) return [];
        const subEnd = Math.min(frameCount, subStart + perWorker);
        const times = [];
        for (let k = subStart; k < subEnd; k++) {
          times.push((startFrame + k) / FPS);
        }
        const b64List = await page.evaluate(async (ts) => {
          const c = document.getElementById('master');
          const out = [];
          for (let j = 0; j < ts.length; j++) {
            window.renderAt(ts[j]);
            const url = c.toDataURL('image/jpeg', 0.95);
            out.push(url.slice(23));
          }
          return out;
        }, times);
        return b64List.map((s) => Buffer.from(s, 'base64'));
      })
    );

    for (const chunkList of workerResults) {
      for (const buf of chunkList) {
        if (!ff.stdin.write(buf)) {
          await new Promise((r) => ff.stdin.once('drain', r));
        }
      }
    }

    const doneNow = Math.min(frameCount, base + stepSize);
    if (doneNow % 320 === 0 || doneNow === frameCount) {
      const elapsed = ((Date.now() - t0) / 1000).toFixed(1);
      const rate = (doneNow / Math.max(0.1, (Date.now() - t0) / 1000)).toFixed(1);
      console.log(`Rendered ${doneNow}/${frameCount} frames (${elapsed}s, ${rate} fps)`);
    }
  }

  ff.stdin.end();
  await ffDone;
  await browser.close();
  console.log(`SUCCESS -> ${outMp4}`);
}

(async () => {
  const args = process.argv.slice(2);
  const { server, port } = await startStaticServer();
  const browserUrl = `http://127.0.0.1:${port}/scene.html`;
  const audioPath = path.join(PROJECT_ROOT, 'assets', 'audio', 'master_30s.wav');

  try {
    if (args[0] === '--probe') {
      const startSec = 12.8;
      await renderSegment({
        browserUrl,
        startFrame: Math.round(startSec * FPS),
        frameCount: Math.round(4.5 * FPS),
        audioPath,
        audioOffsetSec: startSec,
        outMp4: path.join(PROJECT_ROOT, 'output', 'risk_probe_s2_s3.mp4'),
      });
    } else {
      const outRel = args[1] || 'output/draft_v1.mp4';
      await renderSegment({
        browserUrl,
        startFrame: 0,
        frameCount: 30 * FPS,
        audioPath,
        audioOffsetSec: 0.0,
        outMp4: path.resolve(PROJECT_ROOT, outRel),
      });
    }
  } finally {
    server.close();
  }
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
