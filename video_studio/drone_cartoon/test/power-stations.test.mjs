import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFile, stat } from 'node:fs/promises';
import test from 'node:test';
import { createFilm } from '../power-stations/film.mjs';
import { badge, BPM, BRANDS, CHAPTERS, DURATION, FPS, FRAME_COUNT, ITEMS, PAGES, SHOTS, STATIONS, chapterAt, formatCatalogue, fullModel } from '../power-stations/story.mjs';

const expected = [
  'R1500 Lite', 'R2500 V.2', 'R3500 V.2', 'AC70P', 'AC180P', 'AC200PL',
  'Power 1000 Mini EU', 'Power 1000 V2 EU', 'Power 2000 CN', 'Power Expansion Battery 2000',
  'DELTA 3', 'DELTA 3 Plus', 'DELTA 3 Max', 'DELTA 3 Max Plus', 'DELTA 3 Ultra Plus', 'DELTA Pro 3',
  'P2001E Pro', 'BP3000E Plus', 'BP5000E Pro Max', 'F1000LFP', 'E3800LFP', 'F5000LFP',
];

test('catalogue contains all 22 stock items in six brands, no prices and a separately marked battery', async () => {
  assert.deepEqual(BRANDS, ['ALLPOWERS', 'BLUETTI', 'DJI', 'EcoFlow', 'OUKITEL', 'PECRON']);
  assert.deepEqual(ITEMS.map(fullModel), expected);
  assert.equal(STATIONS, 21);
  assert.deepEqual(ITEMS.filter(({ battery }) => battery).map(fullModel), ['Power Expansion Battery 2000']);
  assert.deepEqual(PAGES.filter(({ brand }) => brand === 'EcoFlow').map(({ items }) => items.length), [3, 3]);
  assert.deepEqual(badge(ITEMS.find(({ model }) => model === 'DELTA 3')), { caption: 'ЁМКОСТЬ', value: '1\u00a0024 Вт·ч' });
  assert.deepEqual(badge(ITEMS.find(({ model }) => model === 'E3800LFP')), { caption: 'МОЩНОСТЬ', value: '4\u00a0200 Вт' });
  const text = await readFile(new URL('../power-stations/catalogue.txt', import.meta.url), 'utf8');
  assert.equal(text, formatCatalogue());
  assert.doesNotMatch(text, /₽|[$€]|(?:руб(?:ль|лей|ля|\.)|\bRUB\b)/iu);
  assert.ok(ITEMS.every((item) => !Object.hasOwn(item, 'price')));
});

test('all power station cards, voices and edits are on the minute-long, frame-aligned score', async () => {
  assert.deepEqual([DURATION, FPS, FRAME_COUNT], [60, 30, 1800]);
  assert.equal(SHOTS[0].start, 0);
  assert.equal(SHOTS.filter(({ kind }) => kind === 'catalogue').length, 7);
  const beat = 60 / BPM;
  for (const [i, { start }] of SHOTS.entries()) {
    assert.ok(start < (SHOTS[i + 1]?.start ?? DURATION));
    assert.ok(Math.abs(start * FPS - Math.round(start * FPS)) < 1e-9);
    assert.ok(Math.abs(start - Math.round(start / beat) * beat) <= .5 / FPS);
  }
  for (const [i, { start, voice }] of CHAPTERS.entries()) {
    assert.equal(chapterAt(start), i);
    assert.ok(SHOTS.some((shot) => shot.start === start));
    assert.ok((await stat(new URL(`../vo/${voice.file}`, import.meta.url))).size > 0);
  }
});

test('each illustrated power station card draws as a distinct opaque scene', () => {
  const { canvas, draw } = createFilm(.5);
  assert.deepEqual([canvas.width, canvas.height], [270, 480]);
  const hash = (t) => {
    const data = draw(t).data();
    assert.equal(data[3], 255);
    assert.equal(data.at(-1), 255);
    return createHash('sha256').update(data).digest('hex');
  };
  const sceneHashes = SHOTS.map(({ start }) => hash(start + .56));
  assert.equal(new Set(sceneHashes).size, SHOTS.length);
  assert.equal(hash(.56), sceneHashes[0]);
  assert.notEqual(hash(6.3), hash(7.1));
});
