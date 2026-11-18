import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { stat } from 'node:fs/promises';
import test from 'node:test';
import { createFilm } from '../bulat/film.mjs';
import { BEEP_AT, CHAPTERS, CONTACTS, DURATION, FILE, FPS, FRAME_COUNT, SITES, SLOGAN, chapterAt } from '../bulat/story.mjs';
import { FILE as ORIGINAL } from '../story.mjs';
import { FILE as GAME } from '../game/story.mjs';

test('Bulat is a separate 30-second film with local cue and three civilian settings', async () => {
  assert.notEqual(FILE, ORIGINAL);
  assert.notEqual(FILE, GAME);
  assert.equal(DURATION, 30);
  assert.equal(FPS * DURATION, FRAME_COUNT);
  assert.ok(CHAPTERS[1].start < BEEP_AT && BEEP_AT < CHAPTERS[2].start);
  assert.deepEqual(SITES.map((s) => s.name), ['Склад', 'Стройплощадка', 'Выездная бригада']);
  let previous = CHAPTERS[2].start;
  for (const { start } of SITES) {
    assert.ok(previous < start && start < CHAPTERS[3].start);
    previous = start;
  }
  assert.equal(CHAPTERS.at(-1).narration, SLOGAN);
  assert.equal(CONTACTS.length, 3);
  await Promise.all(CHAPTERS.map(async ({ start, voice }, i) => {
    assert.equal(chapterAt(start), i);
    assert.ok(Math.abs(start * FPS - Math.round(start * FPS)) < 1e-9);
    assert.ok((await stat(new URL(`../vo/${voice.file}`, import.meta.url))).size > 0);
  }));
});

test('illustration, cue, setting changes and branded finale render natively', () => {
  const { draw, canvas } = createFilm(.5);
  assert.equal(canvas.width, 270);
  assert.equal(canvas.height, 480);
  const hash = (t) => {
    const bytes = draw(t).data();
    assert.equal(bytes[3], 255);
    assert.equal(bytes.at(-1), 255);
    return createHash('sha256').update(bytes).digest('hex');
  };
  const times = [2.9, BEEP_AT - .12, BEEP_AT + .1, 13.5, ...SITES.map((s) => s.start + .34), 22.5, 28.1];
  const frames = times.map(hash);
  assert.equal(new Set(frames).size, times.length);
  assert.equal(hash(times[0]), frames[0]);
});
