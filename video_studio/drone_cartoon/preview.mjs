import { createServer } from 'node:http';
import { createReadStream } from 'node:fs';
import { stat } from 'node:fs/promises';
import { resolve } from 'node:path';
import { pathToFileURL, fileURLToPath } from 'node:url';
import { FILE, SLUG } from './story.mjs';
import { FILE as GAME_FILE, SLUG as GAME_SLUG } from './game/story.mjs';
import { FILE as BULAT_FILE, SLUG as BULAT_SLUG } from './bulat/story.mjs';
import { FILE as TAK_FILE, SLUG as TAK_SLUG } from './tak710/story.mjs';
import { FILE as SAFETY_FILE, SLUG as SAFETY_SLUG } from './site-safety/story.mjs';
import { FILE as STRIZH_FILE, SLUG as STRIZH_SLUG } from './strizh/story.mjs';
import { FILE as POWER_FILE, SLUG as POWER_SLUG } from './power-stations/story.mjs';
import { FILE as GONGTEX_FILE, SLUG as GONGTEX_SLUG } from './gongtex/story.mjs';
import { FILE as RUNCAM_FILE, SLUG as RUNCAM_SLUG } from './runcam/story.mjs';
import { FILE as INCUBATOR_FILE, SLUG as INCUBATOR_SLUG } from './incubator/story.mjs';
import { FILE as FIBER_FILE, SLUG as FIBER_SLUG } from './fiber/story.mjs';
import { FILE as SABER_FILE, SLUG as SABER_SLUG } from './saber/story.mjs';
import { FILE as VAGABUND_FILE, SLUG as VAGABUND_SLUG } from './vagabund/story.mjs';

const HTML = 'text/html; charset=utf-8';
const JS = 'text/javascript; charset=utf-8';
const routes = new Map([
  ['/', ['web/index.html', HTML]],
  ['/index.html', ['web/index.html', HTML]],
  ['/style.css', ['web/style.css', 'text/css; charset=utf-8']],
  ['/player.mjs', ['web/player.mjs', JS]],
  ['/story.mjs', ['story.mjs', JS]],
  ['/fonts/Roboto-Regular.woff', ['../fonts/Roboto-Regular.woff', 'font/woff']],
  ['/fonts/Roboto-Black.woff', ['../fonts/Roboto-Black.woff', 'font/woff']],
  ['/output/cover.jpg', ['output/cover.jpg', 'image/jpeg']],
  [`/output/${SLUG}.jpg`, [`output/${SLUG}.jpg`, 'image/jpeg']],
  ['/output/v-svoem-ritme.mp4', ['output/v-svoem-ritme.mp4', 'video/mp4', 'v_okope_v_svoem_ritme.mp4']],
  ['/output/znat-vovremya.mp4', ['output/znat-vovremya.mp4', 'video/mp4', 'v_okope_znat_vovremya.mp4']],
  ['/film.mp4', [`output/${SLUG}.mp4`, 'video/mp4', FILE]],
  ['/output/dron-nad-obektom.mp4', ['output/dron-nad-obektom.mp4', 'video/mp4', 'v_okope_dron_nad_obektom.mp4']],
]);

const editions = new Map([
  ['/game-over', { page: 'game', file: GAME_FILE, slug: GAME_SLUG }],
  ['/bulat', { page: 'bulat', file: BULAT_FILE, slug: BULAT_SLUG }],
  ['/tak710', { page: 'tak710', file: TAK_FILE, slug: TAK_SLUG, fallbackCover: 'tak710/assets/cover.jpg' }],
  [`/${SAFETY_SLUG}`, { page: 'site-safety', file: SAFETY_FILE, slug: SAFETY_SLUG, fallbackCover: 'site-safety/assets/cover.jpg' }],
  [`/${STRIZH_SLUG}`, { page: 'strizh', file: STRIZH_FILE, slug: STRIZH_SLUG, fallbackCover: 'strizh/assets/cover.jpg' }],
  [`/${POWER_SLUG}`, { page: 'power-stations', file: POWER_FILE, slug: POWER_SLUG, fallbackCover: 'power-stations/assets/cover.jpg' }],
  [`/${GONGTEX_SLUG}`, { page: 'gongtex', file: GONGTEX_FILE, slug: GONGTEX_SLUG, fallbackCover: 'gongtex/assets/cover.jpg' }],
  [`/${RUNCAM_SLUG}`, { page: 'runcam', file: RUNCAM_FILE, slug: RUNCAM_SLUG, fallbackCover: 'runcam/assets/cover.jpg' }],
  [`/${INCUBATOR_SLUG}`, { page: 'incubator', file: INCUBATOR_FILE, slug: INCUBATOR_SLUG, fallbackCover: 'incubator/assets/cover.jpg' }],
  [`/${FIBER_SLUG}`, { page: 'fiber', file: FIBER_FILE, slug: FIBER_SLUG, fallbackCover: 'fiber/assets/cover.jpg' }],
  [`/${SABER_SLUG}`, { page: 'saber', file: SABER_FILE, slug: SABER_SLUG, fallbackCover: 'saber/assets/cover.jpg' }],
  [`/${VAGABUND_SLUG}`, { page: 'vagabund', file: VAGABUND_FILE, slug: VAGABUND_SLUG, fallbackCover: 'vagabund/assets/cover.jpg' }],
]);
for (const [route, { page, file, slug, fallbackCover }] of editions) {
  routes.set(`${route}/`, [`web/${page}.html`, HTML]);
  routes.set(`${route}/player.mjs`, ['web/player.mjs', JS]);
  routes.set(`${route}/story.mjs`, [`${page}/story.mjs`, JS]);
  routes.set(`${route}/cover.jpg`, [`output/${slug}.jpg`, 'image/jpeg', fallbackCover]);
  routes.set(`${route}/film.mp4`, [`output/${slug}.mp4`, 'video/mp4', file]);
}
routes.set('/game-over/game.css', ['web/game.css', 'text/css; charset=utf-8']);
routes.set('/tak710/publish.txt', ['tak710/publish.txt', 'text/plain; charset=utf-8']);
routes.set(`/${SAFETY_SLUG}/publish.txt`, ['site-safety/publish.txt', 'text/plain; charset=utf-8']);
routes.set(`/${STRIZH_SLUG}/description.txt`, ['strizh/description.txt', 'text/plain; charset=utf-8']);
routes.set(`/${POWER_SLUG}/catalogue.txt`, ['power-stations/catalogue.txt', 'text/plain; charset=utf-8']);
routes.set(`/${GONGTEX_SLUG}/publish.txt`, ['gongtex/publish.txt', 'text/plain; charset=utf-8']);
routes.set(`/${RUNCAM_SLUG}/publish.txt`, ['runcam/publish.txt', 'text/plain; charset=utf-8']);
routes.set(`/${INCUBATOR_SLUG}/incubator.css`, ['web/incubator.css', 'text/css; charset=utf-8']);
routes.set(`/${INCUBATOR_SLUG}/publish.txt`, ['incubator/publish.txt', 'text/plain; charset=utf-8']);
routes.set(`/${FIBER_SLUG}/fiber.css`, ['web/fiber.css', 'text/css; charset=utf-8']);
routes.set(`/${FIBER_SLUG}/publish.txt`, ['fiber/publish.txt', 'text/plain; charset=utf-8']);
routes.set(`/${SABER_SLUG}/saber.css`, ['web/saber.css', 'text/css; charset=utf-8']);
routes.set(`/${SABER_SLUG}/publish.txt`, ['saber/publish.txt', 'text/plain; charset=utf-8']);
routes.set(`/${VAGABUND_SLUG}/vagabund.css`, ['web/vagabund.css', 'text/css; charset=utf-8']);
routes.set(`/${VAGABUND_SLUG}/publish.txt`, ['vagabund/publish.txt', 'text/plain; charset=utf-8']);

export function parseRange(value, size) {
  const match = /^bytes=(\d*)-(\d*)$/.exec(value);
  if (!match || size <= 0 || (!match[1] && !match[2])) return null;
  const start = match[1] ? Number(match[1]) : Math.max(0, size - Number(match[2]));
  const end = match[1] && match[2] ? Math.min(size - 1, Number(match[2])) : size - 1;
  return start < size && start <= end ? { start, end } : null;
}

export function makeServer() {
  return createServer(async (req, res) => {
    if (req.method !== 'GET' && req.method !== 'HEAD') {
      res.writeHead(405, { Allow: 'GET, HEAD' }).end();
      return;
    }
    const path = req.url?.split('?')[0];
    if (editions.has(path)) {
      res.writeHead(308, { Location: `${path}/` }).end();
      return;
    }
    const route = routes.get(path);
    if (!route) { res.writeHead(404).end(); return; }
    const [relativePath, type, fallback] = route;
    let file = fileURLToPath(new URL(relativePath, import.meta.url));
    let size;
    try {
      let info;
      try { info = await stat(file); }
      catch (error) {
        if (!fallback || error.code !== 'ENOENT') throw error;
        file = fileURLToPath(new URL(fallback, import.meta.url));
        info = await stat(file);
      }
      if (!info.isFile()) { res.writeHead(404).end(); return; }
      size = info.size;
    } catch (error) {
      res.writeHead(error.code === 'ENOENT' ? 404 : 500).end();
      return;
    }
    const wantsRange = type === 'video/mp4' && req.headers.range;
    const range = wantsRange ? parseRange(wantsRange, size) : null;
    if (wantsRange && !range) {
      res.writeHead(416, { 'Content-Range': `bytes */${size}` }).end();
      return;
    }
    const length = range ? range.end - range.start + 1 : size;
    const headers = { 'Content-Type': type, 'Content-Length': length, 'Cache-Control': 'no-cache' };
    if (type === 'video/mp4') headers['Accept-Ranges'] = 'bytes';
    if (range) headers['Content-Range'] = `bytes ${range.start}-${range.end}/${size}`;
    res.writeHead(range ? 206 : 200, headers);
    if (req.method === 'HEAD' || !length) { res.end(); return; }
    const stream = createReadStream(file, range ?? undefined);
    stream.on('error', () => res.destroy());
    res.on('close', () => stream.destroy());
    stream.pipe(res);
  });
}

if (process.argv[1] && pathToFileURL(resolve(process.argv[1])).href === import.meta.url) {
  const port = Number(process.env.PORT ?? 8000);
  makeServer().listen(port, '0.0.0.0', () => console.log(`Кинозал открыт на 0.0.0.0:${port}`));
}
