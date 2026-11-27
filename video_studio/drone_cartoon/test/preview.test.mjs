import assert from 'node:assert/strict';
import { once } from 'node:events';
import { open } from 'node:fs/promises';
import test from 'node:test';
import { makeServer, parseRange } from '../preview.mjs';
import { FILE as SABER_FILE, SLUG as SABER_SLUG, TITLE as SABER_TITLE } from '../saber/story.mjs';
import { FILE as VAGABUND_FILE, SLUG as VAGABUND_SLUG, TITLE as VAGABUND_TITLE } from '../vagabund/story.mjs';
import { FILE as FIBER_FILE, SLUG as FIBER_SLUG, TITLE as FIBER_TITLE } from '../fiber/story.mjs';
import { FILE as INCUBATOR_FILE, SLUG as INCUBATOR_SLUG, TITLE as INCUBATOR_TITLE } from '../incubator/story.mjs';
import { FILE as RUNCAM_FILE, SLUG as RUNCAM_SLUG, TITLE as RUNCAM_TITLE } from '../runcam/story.mjs';
import { FILE as GONGTEX_FILE, SLUG as GONGTEX_SLUG, TITLE as GONGTEX_TITLE } from '../gongtex/story.mjs';
import { FILE as TAK_FILE } from '../tak710/story.mjs';
import { FILE as SAFETY_FILE, SLUG as SAFETY_SLUG } from '../site-safety/story.mjs';
import { FILE as STRIZH_FILE, SLUG as STRIZH_SLUG } from '../strizh/story.mjs';
import { FILE as POWER_FILE, SLUG as POWER_SLUG, formatCatalogue } from '../power-stations/story.mjs';

test('media ranges respect inclusive ends, file size and invalid inputs', () => {
  assert.deepEqual(parseRange('bytes=20-39', 120), { start: 20, end: 39 });
  assert.deepEqual(parseRange('bytes=20-', 120), { start: 20, end: 119 });
  assert.deepEqual(parseRange('bytes=-20', 120), { start: 100, end: 119 });
  assert.deepEqual(parseRange('bytes=110-200', 120), { start: 110, end: 119 });
  for (const range of ['bytes=99-98', 'bytes=120-', 'bytes=-0', 'bytes=-', 'bytes=0-3,9-12', 'items=1-2']) {
    assert.equal(parseRange(range, 120), null);
  }
});

test('preview serves its assets on a proxy host and handles HEAD', async (t) => {
  const server = makeServer();
  t.after(() => new Promise((resolve, reject) => server.close((error) => error ? reject(error) : resolve())));
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  const url = `http://127.0.0.1:${server.address().port}`;
  const html = await fetch(url, { headers: { Host: '8000-example.e2b.app' } });
  assert.equal(html.status, 200);
  const page = await html.text();
  assert.match(page, /МАГАЗИН «В ОКОПЕ»/);
  assert.match(page, /В своём ритме/);
  assert.match(page, /id="contacts"/);
  assert.match(page, /<source src="\.\/film\.mp4"/);
  const script = await fetch(`${url}/player.mjs`, { method: 'HEAD' });
  assert.equal(script.status, 200);
  assert.match(script.headers.get('content-type'), /javascript/);
  assert.equal(await script.text(), '');
  assert.equal((await fetch(`${url}/package.json`)).status, 404);
});

test('game cut has its own relative player, story and media routes', async (t) => {
  const server = makeServer();
  t.after(() => new Promise((resolve, reject) => server.close((error) => error ? reject(error) : resolve())));
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  const root = `http://127.0.0.1:${server.address().port}`;
  const res = await fetch(`${root}/game-over`, { redirect: 'manual' });
  assert.equal(res.status, 308);
  assert.equal(res.headers.get('location'), '/game-over/');
  const game = await fetch(`${root}/game-over/`, { headers: { Host: '8000-example.e2b.app' } });
  assert.equal(game.status, 200);
  assert.match(await game.text(), /download="v_okope_game_over\.mp4"/);
  const story = await fetch(`${root}/game-over/story.mjs`);
  assert.match(await story.text(), /Game Over для дрона/);
  assert.equal((await fetch(`${root}/game-over/player.mjs`, { method: 'HEAD' })).status, 200);
  assert.equal((await fetch(`${root}/game-over/game.css`, { method: 'HEAD' })).status, 200);
  assert.equal((await fetch(`${root}/game-over/web/game.html`)).status, 404);
});

test('Bulat player is separate from both previously delivered cuts', async (t) => {
  const server = makeServer();
  t.after(() => new Promise((resolve, reject) => server.close((error) => error ? reject(error) : resolve())));
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  const root = `http://127.0.0.1:${server.address().port}`;
  const redirect = await fetch(`${root}/bulat`, { redirect: 'manual' });
  assert.equal(redirect.status, 308);
  assert.equal(redirect.headers.get('location'), '/bulat/');
  const page = await fetch(`${root}/bulat/`, { headers: { Host: '8000-example.e2b.app' } });
  assert.equal(page.status, 200);
  assert.match(await page.text(), /download="v_okope_bulat_v4_detektor\.mp4"/);
  assert.match(await (await fetch(`${root}/bulat/story.mjs`)).text(), /Зачем гражданским/);
  assert.equal((await fetch(`${root}/bulat/player.mjs`, { method: 'HEAD' })).status, 200);
  assert.equal((await fetch(`${root}/game-over/`)).status, 200);
  assert.equal((await fetch(`${root}/`)).status, 200);
});

test('TAK710 serves a separate player, poster, publication copy and exact MP4 ranges', async (t) => {
  const server = makeServer();
  t.after(() => new Promise((resolve, reject) => server.close((error) => error ? reject(error) : resolve())));
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  const root = `http://127.0.0.1:${server.address().port}`;
  const redirect = await fetch(`${root}/tak710`, { redirect: 'manual' });
  assert.equal(redirect.status, 308);
  assert.equal(redirect.headers.get('location'), '/tak710/');
  const url = `${root}/tak710/`;
  const page = await fetch(url, { headers: { Host: '8000-example.e2b.app' } });
  assert.equal(page.status, 200);
  const html = await page.text();
  assert.ok(html.includes(`download="${TAK_FILE}"`));
  assert.match(html, /Это обзор, а не инструкция/);
  const story = await (await fetch(`${url}story.mjs`)).text();
  assert.match(story, /Цех, дорога и поход/);
  assert.doesNotMatch(story, /112|диспетчер/iu);
  assert.equal((await fetch(`${url}player.mjs`, { method: 'HEAD' })).status, 200);
  const poster = await fetch(`${url}cover.jpg`, { method: 'HEAD' });
  assert.equal(poster.status, 200);
  assert.equal(poster.headers.get('content-type'), 'image/jpeg');
  const copy = await fetch(`${url}publish.txt`);
  assert.match(copy.headers.get('content-type'), /text\/plain/);
  assert.match(await copy.text(), /YOUTUBE SHORTS[\s\S]*ВК КЛИПЫ/);
  assert.match(await (await fetch(root)).text(), /href="\.\/tak710\/"/);
  const mp4 = `${url}film.mp4`;
  const range = await fetch(mp4, { headers: { Range: 'bytes=45120-45151' } });
  assert.equal(range.status, 206);
  assert.match(range.headers.get('content-range'), /^bytes 45120-45151\/\d+$/);
  assert.equal(range.headers.get('content-type'), 'video/mp4');
  const file = await open(new URL(`../${TAK_FILE}`, import.meta.url), 'r');
  try {
    const expected = Buffer.alloc(32);
    const { bytesRead } = await file.read(expected, 0, 32, 45120);
    assert.equal(bytesRead, 32);
    assert.deepEqual(Buffer.from(await range.arrayBuffer()), expected);
  } finally {
    await file.close();
  }
});

test('safety player has its own cover, chapter data and downloadable byte ranges', async (t) => {
  const server = makeServer();
  t.after(() => new Promise((resolve, reject) => server.close((error) => error ? reject(error) : resolve())));
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  const root = `http://127.0.0.1:${server.address().port}`;
  const url = `${root}/${SAFETY_SLUG}`;
  const host = { Host: '8000-example.e2b.app' };
  const redirect = await fetch(url, { redirect: 'manual', headers: host });
  assert.equal(redirect.status, 308);
  assert.equal(redirect.headers.get('location'), `/${SAFETY_SLUG}/`);
  const response = await fetch(`${url}/`, { headers: host });
  assert.equal(response.status, 200);
  const page = await response.text();
  assert.ok(page.includes(`download="${SAFETY_FILE}"`));
  assert.match(page, /иллюстративная съёмка Tiger Lily \/ Pexels/);
  assert.match(await (await fetch(`${url}/story.mjs`)).text(), /Держите дистанцию/);
  assert.match(await (await fetch(`${url}/publish.txt`)).text(), /00:19 — кому сообщить/);
  assert.equal((await fetch(`${url}/cover.jpg`, { method: 'HEAD' })).headers.get('content-type'), 'image/jpeg');
  const partial = await fetch(`${url}/film.mp4`, { headers: { ...host, Range: 'bytes=4096-4127' } });
  assert.equal(partial.status, 206);
  assert.match(partial.headers.get('content-range'), /^bytes 4096-4127\/\d+$/);
  const master = await open(new URL(`../${SAFETY_FILE}`, import.meta.url), 'r');
  try {
    const expected = Buffer.alloc(32);
    assert.equal((await master.read(expected, 0, 32, 4096)).bytesRead, 32);
    assert.deepEqual(Buffer.from(await partial.arrayBuffer()), expected);
  } finally {
    await master.close();
  }
});

test('the Strizh page serves an independent overview, poster, chapters and exact download', async (t) => {
  const server = makeServer();
  t.after(() => new Promise((resolve, reject) => server.close((error) => error ? reject(error) : resolve())));
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  const root = `http://127.0.0.1:${server.address().port}`;
  const url = `${root}/${STRIZH_SLUG}`;
  const headers = { Host: '8000-example.e2b.app' };
  const redirect = await fetch(url, { redirect: 'manual', headers });
  assert.equal(redirect.status, 308);
  assert.equal(redirect.headers.get('location'), `/${STRIZH_SLUG}/`);
  const page = await fetch(`${url}/`, { headers });
  assert.equal(page.status, 200);
  const html = await page.text();
  assert.ok(html.includes(`download="${STRIZH_FILE}"`));
  assert.match(html, /«Стриж»<span>Внешний вид/);
  assert.doesNotMatch(html, /памятка|склад/i);
  assert.match(await (await fetch(`${url}/story.mjs`)).text(), /В три четверти/);
  const poster = await fetch(`${url}/cover.jpg`, { method: 'HEAD' });
  assert.equal(poster.status, 200);
  assert.equal(poster.headers.get('content-type'), 'image/jpeg');
  assert.match(await (await fetch(`${url}/description.txt`)).text(), /00:44 — три ракурса рядом/);
  assert.equal((await fetch(`${root}/${SAFETY_SLUG}/`)).status, 200);
  const home = await (await fetch(root)).text();
  assert.ok(home.includes(`href="./${STRIZH_SLUG}/"`));
  assert.ok(!home.includes(`href="./${SAFETY_SLUG}/"`));
  const media = await fetch(`${url}/film.mp4`, { headers: { ...headers, Range: 'bytes=4096-4127' } });
  assert.equal(media.status, 206);
  assert.equal(media.headers.get('content-type'), 'video/mp4');
  const master = await open(new URL(`../${STRIZH_FILE}`, import.meta.url), 'r');
  try {
    const expected = Buffer.alloc(32);
    assert.equal((await master.read(expected, 0, 32, 4096)).bytesRead, 32);
    assert.deepEqual(Buffer.from(await media.arrayBuffer()), expected);
  } finally {
    await master.close();
  }
});

test('power catalogue serves its own MP4, cover, chapter data and text list', async (t) => {
  const server = makeServer();
  t.after(() => new Promise((resolve, reject) => server.close((error) => error ? reject(error) : resolve())));
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  const root = `http://127.0.0.1:${server.address().port}`;
  const url = `${root}/${POWER_SLUG}`;
  const headers = { Host: '8000-example.e2b.app' };
  const redirect = await fetch(url, { redirect: 'manual', headers });
  assert.equal(redirect.status, 308);
  assert.equal(redirect.headers.get('location'), `/${POWER_SLUG}/`);
  const page = await fetch(`${url}/`, { headers });
  assert.equal(page.status, 200);
  const html = await page.text();
  assert.ok(html.includes(`download="${POWER_FILE}"`));
  assert.match(html, /21 портативная станция и один дополнительный аккумулятор/);
  const cover = await fetch(`${url}/cover.jpg`, { method: 'HEAD' });
  assert.equal(cover.status, 200);
  assert.equal(cover.headers.get('content-type'), 'image/jpeg');
  const catalogue = await fetch(`${url}/catalogue.txt`);
  assert.equal(catalogue.status, 200);
  assert.equal(await catalogue.text(), formatCatalogue());
  assert.match(await (await fetch(`${url}/story.mjs`)).text(), /DELTA 3 Ultra Plus/);
  assert.ok((await (await fetch(root)).text()).includes(`href="./${POWER_SLUG}/"`));
  const media = await fetch(`${url}/film.mp4`, { headers: { ...headers, Range: 'bytes=4096-4127' } });
  assert.equal(media.status, 206);
  assert.equal(media.headers.get('content-type'), 'video/mp4');
  const master = await open(new URL(`../${POWER_FILE}`, import.meta.url), 'r');
  try {
    const expected = Buffer.alloc(32);
    assert.equal((await master.read(expected, 0, 32, 4096)).bytesRead, 32);
    assert.deepEqual(Buffer.from(await media.arrayBuffer()), expected);
  } finally {
    await master.close();
  }
});

test('GONGTEX preview serves the cover, copy and exact range from the jacket release', async (t) => {
  const server = makeServer();
  t.after(() => new Promise((resolve, reject) => server.close((error) => error ? reject(error) : resolve())));
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  const root = `http://127.0.0.1:${server.address().port}/`;
  const url = `${root}${GONGTEX_SLUG}`;
  const headers = { Host: '8000-example.e2b.app' };
  const redirect = await fetch(url, { redirect: 'manual', headers });
  assert.equal(redirect.status, 308);
  assert.equal(redirect.headers.get('location'), `/${GONGTEX_SLUG}/`);
  const html = await (await fetch(`${url}/`, { headers })).text();
  assert.ok(html.includes(`download="${GONGTEX_FILE}"`));
  assert.match(html, /GONGTEX <span>Reversible Jacket/);
  assert.ok((await (await fetch(root)).text()).includes(`href="./${GONGTEX_SLUG}/"`));
  const cover = await fetch(`${url}/cover.jpg`, { method: 'HEAD' });
  assert.equal(cover.status, 200);
  assert.equal(cover.headers.get('content-type'), 'image/jpeg');
  assert.match(await (await fetch(`${url}/story.mjs`)).text(), /Манжеты и утяжка/);
  const copy = await fetch(`${url}/publish.txt`, { headers });
  assert.equal(copy.headers.get('content-type'), 'text/plain; charset=utf-8');
  assert.ok((await copy.text()).startsWith(`Заголовок\n${GONGTEX_TITLE}\n\nОписание\n`));
  const response = await fetch(`${url}/film.mp4`, { headers: { ...headers, Range: 'bytes=4096-4127' } });
  assert.equal(response.status, 206);
  assert.match(response.headers.get('content-range'), /^bytes 4096-4127\/\d+$/);
  assert.equal(response.headers.get('content-type'), 'video/mp4');
  const master = await open(new URL(`../${GONGTEX_FILE}`, import.meta.url), 'r');
  try {
    const expected = Buffer.alloc(32);
    assert.equal((await master.read(expected, 0, 32, 4096)).bytesRead, 32);
    assert.deepEqual(Buffer.from(await response.arrayBuffer()), expected);
  } finally {
    await master.close();
  }
});

test('RunCam loads on the preview host with independent artwork, copy and MP4 byte ranges', async (t) => {
  const server = makeServer();
  t.after(() => new Promise((resolve, reject) => server.close((error) => error ? reject(error) : resolve())));
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  const root = `http://127.0.0.1:${server.address().port}/`;
  const url = `${root}${RUNCAM_SLUG}`;
  const headers = { Host: '8000-example.e2b.app' };
  const redirect = await fetch(url, { redirect: 'manual', headers });
  assert.equal(redirect.status, 308);
  assert.equal(redirect.headers.get('location'), `/${RUNCAM_SLUG}/`);
  const page = await fetch(`${url}/`, { headers });
  assert.equal(page.status, 200);
  const html = await page.text();
  assert.ok(html.includes(`download="${RUNCAM_FILE}"`));
  assert.match(html, /RunCam <span>Helmet Camera/);
  assert.ok((await (await fetch(root)).text()).includes(`href="./${RUNCAM_SLUG}/"`));
  const cover = await fetch(`${url}/cover.jpg`, { method: 'HEAD' });
  assert.equal(cover.status, 200);
  assert.equal(cover.headers.get('content-type'), 'image/jpeg');
  assert.match(await (await fetch(`${url}/story.mjs`)).text(), /Аккумулятор 18650/);
  const copy = await fetch(`${url}/publish.txt`, { headers });
  assert.equal(copy.headers.get('content-type'), 'text/plain; charset=utf-8');
  assert.ok((await copy.text()).startsWith(`Заголовок\n${RUNCAM_TITLE}\n\nОписание\n`));
  const response = await fetch(`${url}/film.mp4`, { headers: { ...headers, Range: 'bytes=4096-4127' } });
  assert.equal(response.status, 206);
  assert.match(response.headers.get('content-range'), /^bytes 4096-4127\/\d+$/);
  assert.equal(response.headers.get('content-type'), 'video/mp4');
  const master = await open(new URL(`../${RUNCAM_FILE}`, import.meta.url), 'r');
  try {
    const expected = Buffer.alloc(32);
    assert.equal((await master.read(expected, 0, 32, 4096)).bytesRead, 32);
    assert.deepEqual(Buffer.from(await response.arrayBuffer()), expected);
  } finally {
    await master.close();
  }
});

test('the Incubator photo review has its own proxy-safe player, styling, cover, copy and exact media', async (t) => {
  const server = makeServer();
  t.after(() => new Promise((resolve, reject) => server.close((error) => error ? reject(error) : resolve())));
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  const root = `http://127.0.0.1:${server.address().port}`;
  const path = `/${INCUBATOR_SLUG}`;
  const headers = { Host: '8000-example.e2b.app' };
  const redirect = await fetch(root + path, { headers, redirect: 'manual' });
  assert.equal(redirect.status, 308);
  assert.equal(redirect.headers.get('location'), `${path}/`);
  const url = `${root}${path}/`;
  const page = await fetch(url, { headers });
  assert.equal(page.status, 200);
  const html = await page.text();
  assert.ok(html.includes(`download="${INCUBATOR_FILE}"`));
  assert.match(html, /Инкубатор <span>3\.30<\/span>/);
  assert.match(html, /<source src="\.\/film\.mp4"/);
  for (const [asset, type] of [['cover.jpg', 'image/jpeg'], ['incubator.css','text/css'],
    ['player.mjs','text/javascript'], ['story.mjs','text/javascript']]) {
    const res = await fetch(url + asset, { method: 'HEAD', headers });
    assert.equal(res.status, 200);
    assert.ok(res.headers.get('content-type').startsWith(type));
  }
  const copy = await fetch(url + 'publish.txt', { headers });
  assert.equal(copy.headers.get('content-type'), 'text/plain; charset=utf-8');
  assert.ok((await copy.text()).startsWith(`Заголовок\n${INCUBATOR_TITLE}\n\nОписание\n`));
  const range = await fetch(url + 'film.mp4', { headers: { ...headers, Range: 'bytes=4096-4127' } });
  assert.equal(range.status, 206);
  assert.match(range.headers.get('content-range'), /^bytes 4096-4127\/\d+$/);
  const master = await open(new URL(`../${INCUBATOR_FILE}`, import.meta.url), 'r');
  try {
    const expected = Buffer.alloc(32);
    assert.equal((await master.read(expected, 0, 32, 4096)).bytesRead, 32);
    assert.deepEqual(Buffer.from(await range.arrayBuffer()), expected);
  } finally {
    await master.close();
  }
});

test('fiber stock review serves an independent player, cover, publication copy and playable byte ranges', async (t) => {
  const server = makeServer();
  t.after(() => new Promise((resolve, reject) => server.close((error) => error ? reject(error) : resolve())));
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  const root = `http://127.0.0.1:${server.address().port}`;
  const path = `/${FIBER_SLUG}`;
  const headers = { Host: '8000-example.e2b.app' };
  const redirect = await fetch(root + path, { headers, redirect: 'manual' });
  assert.equal(redirect.status, 308);
  assert.equal(redirect.headers.get('location'), `${path}/`);
  const url = `${root}${path}/`;
  const page = await fetch(url, { headers });
  assert.equal(page.status, 200);
  const html = await page.text();
  assert.ok(html.includes(`download="${FIBER_FILE}"`));
  assert.match(html, /Показываем прозрачное оптоволокно, которое есть у нас на складе/);
  assert.match(html, /id="running-time">00:31/);
  assert.doesNotMatch(html, /карточк|51,395|50,4/iu);
  for (const [asset, type] of [['cover.jpg','image/jpeg'], ['fiber.css','text/css'], ['story.mjs','text/javascript']]) {
    const res = await fetch(url + asset, { method: 'HEAD', headers });
    assert.equal(res.status, 200);
    assert.ok(res.headers.get('content-type').startsWith(type));
  }
  const copy = await fetch(url + 'publish.txt', { headers });
  assert.equal(copy.headers.get('content-type'), 'text/plain; charset=utf-8');
  assert.ok((await copy.text()).startsWith(`Заголовок\n${FIBER_TITLE}\n\nОписание\n`));
  const range = await fetch(url + 'film.mp4', { headers: { ...headers, Range: 'bytes=4096-4127' } });
  assert.equal(range.status, 206);
  assert.match(range.headers.get('content-range'), /^bytes 4096-4127\/\d+$/);
  const master = await open(new URL(`../${FIBER_FILE}`, import.meta.url), 'r');
  try {
    const expected = Buffer.alloc(32);
    assert.equal((await master.read(expected, 0, 32, 4096)).bytesRead, 32);
    assert.deepEqual(Buffer.from(await range.arrayBuffer()), expected);
  } finally {
    await master.close();
  }
});

test('Saber preview serves the review and its downloads on the proxy host', async (t) => {
  const server = makeServer();
  t.after(() => new Promise((resolve, reject) => server.close(error => error ? reject(error) : resolve())));
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  const url = `http://127.0.0.1:${server.address().port}/${SABER_SLUG}`;
  const headers = { Host: '8000-example.e2b.app' };
  const redirect = await fetch(url, { headers, redirect: 'manual' });
  assert.equal(redirect.status, 308);
  assert.equal(redirect.headers.get('location'), `/${SABER_SLUG}/`);
  const res = await fetch(`${url}/`, { headers });
  assert.equal(res.status, 200);
  const html = await res.text();
  assert.match(html, /Wiley X <span>Saber Advanced<\/span>/);
  assert.match(html, /id="running-time">00:52/);
  assert.match(html, /<source src="\.\/film\.mp4"/);
  assert.ok(html.includes(`download="${SABER_FILE}"`));
  for (const [asset, type] of [['cover.jpg','image/jpeg'], ['saber.css','text/css'],
    ['player.mjs','text/javascript'], ['story.mjs','text/javascript']]) {
    const head = await fetch(`${url}/${asset}`, { method: 'HEAD', headers });
    assert.equal(head.status, 200);
    assert.ok(head.headers.get('content-type').startsWith(type));
  }
  const copy = await fetch(`${url}/publish.txt`, { headers });
  assert.equal(copy.headers.get('content-type'), 'text/plain; charset=utf-8');
  assert.ok((await copy.text()).startsWith(`Заголовок\n${SABER_TITLE}\n\nОписание\n`));
  const range = await fetch(`${url}/film.mp4`, { headers: { ...headers, Range: 'bytes=4096-4127' } });
  assert.equal(range.status, 206);
  assert.match(range.headers.get('content-range'), /^bytes 4096-4127\/\d+$/);
  const master = await open(new URL(`../${SABER_FILE}`, import.meta.url), 'r');
  try {
    const expected = Buffer.alloc(32);
    assert.equal((await master.read(expected, 0, 32, 4096)).bytesRead, 32);
    assert.deepEqual(Buffer.from(await range.arrayBuffer()), expected);
  } finally {
    await master.close();
  }
});

test('Prabos preview has its own cover, publication copy and exact seek ranges', async (t) => {
  const server = makeServer();
  t.after(() => new Promise((resolve, reject) => server.close(error => error ? reject(error) : resolve())));
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  const url = `http://127.0.0.1:${server.address().port}/${VAGABUND_SLUG}`;
  const headers = { Host: '8000-example.e2b.app' };
  const redirect = await fetch(url, { headers, redirect: 'manual' });
  assert.equal(redirect.status, 308);
  assert.equal(redirect.headers.get('location'), `/${VAGABUND_SLUG}/`);
  const player = await fetch(`${url}/`, { headers });
  assert.equal(player.status, 200);
  const html = await player.text();
  assert.match(html, /Prabos <span>Vagabund Ankle Field<\/span>/);
  assert.match(html, /id="running-time">00:51/);
  assert.match(html, /<source src="\.\/film\.mp4"/);
  assert.ok(html.includes(`download="${VAGABUND_FILE}"`));
  for (const [asset,type] of [['cover.jpg','image/jpeg'],['vagabund.css','text/css'],
    ['player.mjs','text/javascript'],['story.mjs','text/javascript']]) {
    const head = await fetch(`${url}/${asset}`, { method: 'HEAD', headers });
    assert.equal(head.status, 200);
    assert.ok(head.headers.get('content-type').startsWith(type));
  }
  const copy = await fetch(`${url}/publish.txt`, { headers });
  assert.equal(copy.headers.get('content-type'), 'text/plain; charset=utf-8');
  assert.ok((await copy.text()).startsWith(`Заголовок\n${VAGABUND_TITLE}\n\nОписание\n`));
  const range = await fetch(`${url}/film.mp4`, { headers: { ...headers, Range: 'bytes=4096-4127' } });
  assert.equal(range.status, 206);
  assert.match(range.headers.get('content-range'), /^bytes 4096-4127\/\d+$/);
  const master = await open(new URL(`../${VAGABUND_FILE}`, import.meta.url), 'r');
  try {
    const expected = Buffer.alloc(32);
    assert.equal((await master.read(expected, 0, 32, 4096)).bytesRead, 32);
    assert.deepEqual(Buffer.from(await range.arrayBuffer()), expected);
  } finally {
    await master.close();
  }
});
