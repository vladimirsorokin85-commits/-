import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { stat } from 'node:fs/promises';
import test from 'node:test';
import { createFilm, HEIGHT, WIDTH } from '../game/film.mjs';
import { BEEP_AT, CHAPTERS, CONTACTS, DURATION, FILE, FPS, FRAME_COUNT, GAME_OVER_AT, POV_SHOTS, SITE_SHOTS, SLOGAN, chapterAt } from '../game/story.mjs';
import { FILE as ORIGINAL } from '../story.mjs';

test('game cut has its own file, grid-aligned timing, two speakers and an approved finale', async () => {
  assert.notEqual(FILE, ORIGINAL);
  assert.equal(30 * FPS, FRAME_COUNT);
  assert.equal(DURATION, 30);
  assert.deepEqual(CHAPTERS.map((x) => x.start), [0, 6, 13, 22, 25]);
  assert.ok(CHAPTERS[1].start < BEEP_AT && BEEP_AT < GAME_OVER_AT && GAME_OVER_AT < CHAPTERS[2].start);
  assert.deepEqual(SITE_SHOTS.map((x) => x.start), [22, 23, 24]);
  assert.equal(POV_SHOTS.length, 3);
  for (const t of [...POV_SHOTS.map((shot) => shot.start), BEEP_AT, GAME_OVER_AT]) {
    assert.ok(Math.abs(t * FPS - Math.round(t * FPS)) < 1e-9);
  }
  assert.equal(CHAPTERS.at(-1).narration, SLOGAN);
  assert.equal(SLOGAN, 'Не будь мишенью. Будь «В окопе»!');
  assert.equal(CONTACTS.length, 3);
  assert.deepEqual(CHAPTERS.map((x) => !!x.voice.radio), [true, true, false, false, false]);
  await Promise.all(CHAPTERS.map(async ({ start, narration, voice }, i) => {
    assert.equal(chapterAt(start), i);
    assert.ok(narration.length > 0 && voice.offset < (CHAPTERS[i + 1]?.start ?? DURATION) - start);
    assert.ok((await stat(new URL(`../vo/${voice.file}`, import.meta.url))).size > 0);
  }));
});

test('game footage draws deterministic, opaque and distinct shots', () => {
  const { canvas, draw } = createFilm(.5);
  assert.equal(canvas.width, WIDTH / 2);
  assert.equal(canvas.height, HEIGHT / 2);
  const frameHash = (time) => {
    const pixels = draw(time).data();
    assert.equal(pixels[3], 255);
    assert.equal(pixels.at(-1), 255);
    return createHash('sha256').update(pixels).digest('hex');
  };
  const keyframes = [1, 3.5, 5.2, 7.1, 11.25, 16.2, 22.5, 23.5, 24.5, 28.1];
  const frames = keyframes.map(frameHash);
  assert.equal(new Set(frames).size, keyframes.length);
  assert.equal(frameHash(1), frames[0]);
});
