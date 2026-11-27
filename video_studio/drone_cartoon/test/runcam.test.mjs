import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFile, stat } from 'node:fs/promises';
import test from 'node:test';
import { createFilm } from '../runcam/film.mjs';
import { BPM, CHAPTERS, DURATION, FPS, FRAME_COUNT, PHOTOS, SHOTS, SPECS, TITLE, chapterAt } from '../runcam/story.mjs';
import { STORM_RIDERS } from '../mix.mjs';

test('RunCam keeps the 8-hour figure with the manufacturer battery capacity and recording mode', async () => {
  const copy = await readFile(new URL('../runcam/publish.txt', import.meta.url), 'utf8');
  assert.ok(copy.startsWith(`Заголовок\n${TITLE}\n\nОписание\n`));
  assert.match(copy, /Full HD \(1920 × 1080\) до 60 кадров\/с/u);
  assert.match(copy, /сменного аккумулятора 18650[. ]+Около 8 часов при 1080p60 — показатель RunCam для батареи 3 500 мА·ч/u);
  assert.match(copy, /f\/1\.6, защита от пыли и брызг/u);
  assert.doesNotMatch(copy, /\bIP67\b|погружен|инфракрасн|мгновенн|₽/iu);
  assert.deepEqual([SPECS.runtime, SPECS.referenceCapacity, SPECS.width, SPECS.height, SPECS.fps], [8, 3500, 1920, 1080, 60]);
});

test('the RunCam vertical score has five VO cues, thirteen frame- and beat-aligned shots and nine photos', async () => {
  assert.deepEqual([DURATION, FPS, FRAME_COUNT, SHOTS.length], [47, 30, 1410, 13]);
  assert.equal(CHAPTERS.length, 5);
  assert.equal(SHOTS[0].start, 0);
  const beat = 60 / BPM;
  for (const [i, { start }] of SHOTS.entries()) {
    assert.ok(start < (SHOTS[i + 1]?.start ?? DURATION));
    assert.ok(Math.abs(start * FPS - Math.round(start * FPS)) < 1e-9);
    assert.ok(Math.abs(start - Math.round(start / beat) * beat) <= .5 / FPS);
  }
  assert.equal(new Set(PHOTOS).size, 9);
  for (const name of PHOTOS) assert.ok((await stat(new URL(`../runcam/assets/${name}.jpg`, import.meta.url))).size > 0);
  for (const [i, { start, voice }] of CHAPTERS.entries()) {
    assert.equal(chapterAt(start), i);
    assert.ok(SHOTS.some((shot) => shot.start === start));
    assert.ok((await stat(new URL(`../vo/${voice.file}`, import.meta.url))).size > 0);
  }
  assert.equal(STORM_RIDERS.bpm, BPM);
});

test('RunCam snapshots draw distinct opaque frames, a moving lens diagram and a cover', () => {
  const { canvas, draw, drawCover } = createFilm(.5);
  assert.deepEqual([canvas.width, canvas.height], [270, 480]);
  const hash = (scene) => {
    const data = scene.data();
    assert.equal(data[3], 255);
    assert.equal(data.at(-1), 255);
    return createHash('sha256').update(data).digest('hex');
  };
  const frames = SHOTS.map(({ start }) => hash(draw(start + .98)));
  assert.equal(new Set(frames).size, SHOTS.length);
  const a = SHOTS.find(({ kind }) => kind === 'angle').start;
  assert.notEqual(hash(draw(a + .21)), hash(draw(a + 1.29)));
  assert.ok(!frames.includes(hash(drawCover())));
});
