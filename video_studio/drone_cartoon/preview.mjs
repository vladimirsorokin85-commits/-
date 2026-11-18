import { createServer } from 'node:http';
import { createReadStream } from 'node:fs';
import { stat } from 'node:fs/promises';
import { resolve } from 'node:path';
import { pathToFileURL, fileURLToPath } from 'node:url';
import { FILE, SLUG } from './story.mjs';
import { FILE as GAME_FILE, SLUG as GAME_SLUG } from './game/story.mjs';

const HTML = 'text/html; charset=utf-8';
const JS = 'text/javascript; charset=utf-8';
const routes = new Map([
  ['/', ['web/index.html', HTML]],
  ['/index.html', ['web/index.html', HTML]],
  ['/game-over/', ['web/game.html', HTML]],
  ['/game-over/game.css', ['web/game.css', 'text/css; charset=utf-8']],
  ['/game-over/player.mjs', ['web/player.mjs', JS]],
  ['/game-over/story.mjs', ['game/story.mjs', JS]],
  ['/game-over/cover.jpg', [`output/${GAME_SLUG}.jpg`, 'image/jpeg']],
  ['/game-over/film.mp4', [`output/${GAME_SLUG}.mp4`, 'video/mp4', GAME_FILE]],
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
    if (path === '/game-over') {
      res.writeHead(308, { Location: '/game-over/' }).end();
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
