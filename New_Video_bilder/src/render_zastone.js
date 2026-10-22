#!/usr/bin/env node
/**
 * High-Speed Same-Origin HTTP + Batched Canvas 2D Widescreen (1920x1080 @ 60.000 fps) Renderer
 * Renders New_Video_bilder/src/scene_zastone_16x9.html (9,000 frames = 150.000s = 2:30.00)
 * using batched canvas.toDataURL('image/jpeg', 0.94) across parallel workers directly into FFmpeg!
 */
const http = require("http");
const fs = require("fs");
const os = require("os");
const path = require("path");
const { spawn } = require("child_process");
const puppeteer = require("puppeteer-core");
const ffmpegPath = require("@ffmpeg-installer/ffmpeg").path;

const PROJECT_ROOT = path.resolve(__dirname, "..");
const AUDIO_PATH = "/tmp/master_zastone_256.wav";
const OUT_MP4 = path.join(PROJECT_ROOT, "output", "v_okope_zastone_key256.mp4");

const FPS = 60;
const DURATION = 150.0;
const TOTAL_FRAMES = Math.round(FPS * DURATION); // 9000 exact frames

const MIME = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
};

function startLocalServer() {
  return new Promise((resolve) => {
    const srv = http.createServer((req, res) => {
      const urlPath = decodeURIComponent(req.url.split("?")[0]);
      const filePath = urlPath === "/"
        ? path.join(PROJECT_ROOT, "src", "scene_zastone_16x9.html")
        : path.join(PROJECT_ROOT, urlPath.slice(1));
      if (!fs.existsSync(filePath)) {
        res.writeHead(404);
        res.end("Not found: " + urlPath);
        return;
      }
      const ext = path.extname(filePath).toLowerCase();
      res.writeHead(200, { "Content-Type": MIME[ext] || "application/octet-stream" });
      fs.createReadStream(filePath).pipe(res);
    });
    srv.listen(0, "127.0.0.1", () => resolve({ server: srv, port: srv.address().port }));
  });
}

(async () => {
  process.env.LD_LIBRARY_PATH = `/tmp/sp_libs/lib:/tmp/sp_libs:${process.env.LD_LIBRARY_PATH || ""}`;
  const qaOnly = process.argv.includes("--qa-only");
  const { server, port } = await startLocalServer();
  const url = `http://127.0.0.1:${port}/`;

  const numWorkers = qaOnly ? 1 : Math.max(3, Math.min(4, os.cpus().length * 2));
  const browser = await puppeteer.launch({
    executablePath: "/tmp/chromium",
    headless: true,
    defaultViewport: { width: 1920, height: 1080, deviceScaleFactor: 1 },
    args: [
      "--no-sandbox",
      "--disable-setuid-sandbox",
      "--disable-gpu",
      "--disable-dev-shm-usage",
      "--hide-scrollbars",
      "--font-render-hinting=none",
    ],
  });

  try {
    const pages = await Promise.all(
      Array.from({ length: numWorkers }, async () => {
        const p = await browser.newPage();
        await p.goto(url, { waitUntil: "networkidle0" });
        await p.evaluate(() => window.__READY_PROMISE);
        return p;
      })
    );

    if (qaOnly) {
      const SAMPLE_TIMES = [5.0, 18.5, 33.0, 49.0, 64.0, 76.5, 89.5, 105.0, 119.0, 134.0, 146.5];
      for (let i = 0; i < SAMPLE_TIMES.length; i++) {
        const b64 = await pages[0].evaluate((t) => {
          window.renderAt(t);
          return document.getElementById("master").toDataURL("image/jpeg", 0.94).slice(23);
        }, SAMPLE_TIMES[i]);
        fs.writeFileSync(`/tmp/z16_act_${String(i + 1).padStart(2, "0")}.jpg`, Buffer.from(b64, "base64"));
      }
      console.log("QA_FRAMES_READY");
      return;
    }

    // Strict Cold-Seek vs Rewind Bit-Exact Determinism Gate
    const det = await pages[0].evaluate(() => {
      const g = document.getElementById("master").getContext("2d");
      window.renderAt(89.5);
      const a = new Uint8Array(g.getImageData(0, 0, 1920, 1080).data);
      window.renderAt(5.0);
      window.renderAt(134.0);
      window.renderAt(89.5);
      const b = new Uint8Array(g.getImageData(0, 0, 1920, 1080).data);
      let maxDiff = 0;
      for (let i = 0; i < a.length; i += 4) {
        maxDiff = Math.max(maxDiff, Math.abs(a[i] - b[i]), Math.abs(a[i + 1] - b[i + 1]), Math.abs(a[i + 2] - b[i + 2]));
      }
      return { maxDiff, deterministic: maxDiff === 0 };
    });
    console.log("[DETERMINISM GATE]", JSON.stringify(det));
    if (!det.deterministic) throw new Error("Determinism check failed!");

    fs.mkdirSync(path.dirname(OUT_MP4), { recursive: true });
    const ffArgs = [
      "-y",
      "-v", "error",
      "-f", "image2pipe",
      "-vcodec", "mjpeg",
      "-framerate", String(FPS),
      "-i", "pipe:0",
      "-i", AUDIO_PATH,
      "-map", "0:v:0",
      "-map", "1:a:0",
      "-c:v", "libx264",
      "-preset", "medium",
      "-profile:v", "high",
      "-crf", "20",
      "-maxrate", "1850k",
      "-bufsize", "3700k",
      "-pix_fmt", "yuv420p",
      "-r", String(FPS),
      "-vsync", "cfr",
      "-c:a", "aac",
      "-b:a", "192k",
      "-ar", "48000",
      "-ac", "2",
      "-shortest",
      "-movflags", "+faststart",
      OUT_MP4,
    ];

    const ff = spawn(ffmpegPath, ffArgs, { stdio: ["pipe", "inherit", "inherit"] });
    const ffDone = new Promise((resolve, reject) => {
      ff.on("close", (code) => (code === 0 ? resolve() : reject(new Error(`FFmpeg exited ${code}`))));
    });

    const t0 = Date.now();
    const perWorker = 10;
    const step = numWorkers * perWorker;

    for (let base = 0; base < TOTAL_FRAMES; base += step) {
      const workerBatches = await Promise.all(
        pages.map(async (page, wIdx) => {
          const subStart = base + wIdx * perWorker;
          if (subStart >= TOTAL_FRAMES) return [];
          const subEnd = Math.min(TOTAL_FRAMES, subStart + perWorker);
          const times = [];
          for (let f = subStart; f < subEnd; f++) times.push(f / FPS);
          const b64Arr = await page.evaluate((ts) => {
            const c = document.getElementById("master");
            const out = [];
            for (let j = 0; j < ts.length; j++) {
              window.renderAt(ts[j]);
              out.push(c.toDataURL("image/jpeg", 0.94).slice(23));
            }
            return out;
          }, times);
          return b64Arr.map((s) => Buffer.from(s, "base64"));
        })
      );

      for (const arr of workerBatches) {
        for (const buf of arr) {
          if (!ff.stdin.write(buf)) {
            await new Promise((r) => ff.stdin.once("drain", r));
          }
        }
      }

      const done = Math.min(TOTAL_FRAMES, base + step);
      if (done % 960 === 0 || done === TOTAL_FRAMES) {
        const sec = ((Date.now() - t0) / 1000).toFixed(1);
        const fpsRate = (done / Math.max(0.1, (Date.now() - t0) / 1000)).toFixed(1);
        console.log(`  Rendered ${done}/${TOTAL_FRAMES} frames (${sec}s elapsed, ${fpsRate} fps)`);
      }
    }

    ff.stdin.end();
    await ffDone;
    const stat = fs.statSync(OUT_MP4);
    console.log(`[COMPLETE] ${OUT_MP4} (${(stat.size / (1024 * 1024)).toFixed(2)} MB)`);
  } finally {
    await browser.close();
    server.close();
  }
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
