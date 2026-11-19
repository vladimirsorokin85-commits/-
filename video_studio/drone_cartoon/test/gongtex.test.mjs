import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFile, stat } from 'node:fs/promises';
import test from 'node:test';
import { createFilm } from '../gongtex/film.mjs';
import { BPM, CHAPTERS, DURATION, FPS, FRAME_COUNT, PHOTOS, SHOTS, SPECS, TITLE, chapterAt } from '../gongtex/story.mjs';
import { STORM_RIDERS } from '../mix.mjs';

test('GONGTEX copy includes the supplied fabric, weight and details with no price or temperature claims', async () => {
  const copy = await readFile(new URL('../gongtex/publish.txt', import.meta.url), 'utf8');
  assert.ok(copy.startsWith(`Заголовок\n${TITLE}\n\nОписание\n`));
  assert.match(copy, /с одной стороны — мультикам, с другой — койот/iu);
  assert.match(copy, /96% полиэстер, 4% спандекс, плотность 110 г\/м²/iu);
  assert.match(copy, /DuPont — 120 г\/м²[\s\S]*молния SBS[\s\S]*липучке[\s\S]*карман на молнии[\s\S]*манжеты[\s\S]*эластичным шнурком/iu);
  assert.doesNotMatch(copy, /₽|\brub\b|градус|°C/iu);
  assert.equal(SPECS.polyester + SPECS.spandex, 100);
});

test('GONGTEX keeps 12 on-beat shots, five recorded takes and all eight supplied photos', async () => {
  assert.deepEqual([DURATION, FPS, FRAME_COUNT, SHOTS.length], [36, 30, 1080, 12]);
  assert.equal(SHOTS[0].start, 0);
  const beat = 60 / BPM;
  for (const [i, { start }] of SHOTS.entries()) {
    assert.ok(start < (SHOTS[i + 1]?.start ?? DURATION));
    assert.ok(Math.abs(start * FPS - Math.round(start * FPS)) < 1e-9);
    assert.ok(Math.abs(start - Math.round(start / beat) * beat) <= .5 / FPS);
  }
  assert.equal(CHAPTERS.length, 5);
  for (const [i, { start, voice }] of CHAPTERS.entries()) {
    assert.equal(chapterAt(start), i);
    assert.ok(SHOTS.some((shot) => shot.start === start));
    assert.ok((await stat(new URL(`../vo/${voice.file}`, import.meta.url))).size > 0);
  }
  assert.equal(new Set(PHOTOS).size, 8);
  for (const photo of PHOTOS) assert.ok((await stat(new URL(`../gongtex/assets/${photo}.jpg`, import.meta.url))).size > 0);
});

test('GONGTEX has two distinct color sides, opaque frames for all shots, and its own cover', () => {
  const { canvas, draw, drawCover } = createFilm(.5);
  assert.deepEqual([canvas.width, canvas.height], [270, 480]);
  const hash = (scene) => {
    const data = scene.data();
    assert.equal(data[3], 255);
    assert.equal(data.at(-1), 255);
    return createHash('sha256').update(data).digest('hex');
  };
  const shots = SHOTS.map(({ start }) => hash(draw(start + .81)));
  assert.equal(new Set(shots).size, SHOTS.length);
  assert.notEqual(hash(draw(.84)), hash(draw(2.24)));
  assert.ok(!shots.includes(hash(drawCover())));
});

test('approved music is the exact owner MP3 and the score uses its native BPM', async () => {
  const source = await readFile(STORM_RIDERS.file);
  assert.equal(createHash('sha256').update(source).digest('hex'), '85e506fcd419bc253b65ec0665946aab791d4e0f24e63e923bba694e273d196b');
  assert.equal(STORM_RIDERS.bpm, BPM);
});
