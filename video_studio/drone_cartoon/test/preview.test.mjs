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
