import assert from 'node:assert/strict';
import { once } from 'node:events';
import test from 'node:test';
import { makeServer, parseRange } from '../preview.mjs';

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
