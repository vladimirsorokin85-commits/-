import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { stat } from 'node:fs/promises';
import test from 'node:test';
import { createFilm } from '../strizh/film.mjs';
import { BPM, CHAPTERS, CONTACTS, DURATION, FILE, FPS, FRAME_COUNT, SHOTS, VIEWS, chapterAt } from '../strizh/story.mjs';
import { FILE as SAFETY_FILE } from '../site-safety/story.mjs';

test('the Strizh overview is a separate minute with three still views and beat-aligned edits', async () => {
  assert.notEqual(FILE, SAFETY_FILE);
  assert.deepEqual([DURATION, FPS, FRAME_COUNT], [60, 30, 1800]);
  assert.equal(SHOTS[0].start, 0);
  assert.equal(CHAPTERS.length, 6);
  assert.deepEqual(CONTACTS, []);
  assert.deepEqual(VIEWS.map(({ id }) => id), [1, 4, 16]);
  assert.deepEqual(SHOTS.filter(({ kind }) => kind === 'angle').map(({ view }) => view), [0, 1, 2]);
  const beat = 60 / BPM;
  for (const [i, { start }] of SHOTS.entries()) {
    assert.ok(start < (SHOTS[i + 1]?.start ?? DURATION));
    assert.ok(Math.abs(start * FPS - Math.round(start * FPS)) < 1e-9);
    assert.ok(Math.abs(start - Math.round(start / beat) * beat) <= .5 / FPS);
  }
  for (const [index, { id }] of VIEWS.entries()) {
    assert.ok((await stat(new URL(`../strizh/assets/view-${id}.jpg`, import.meta.url))).size > 0);
    assert.ok(SHOTS.some((shot) => shot.view === index));
  }
  for (const [i, { start, voice }] of CHAPTERS.entries()) {
    assert.equal(chapterAt(start), i);
    assert.ok(SHOTS.some((shot) => shot.start === start));
    assert.ok((await stat(new URL(`../vo/${voice.file}`, import.meta.url))).size > 0);
  }
});

test('the Strizh overview draws distinct static photo and flat illustrated compositions', () => {
  const { canvas, draw } = createFilm(.5);
  assert.deepEqual([canvas.width, canvas.height], [270, 480]);
  const hash = (t) => {
    const data = draw(t).data();
    assert.equal(data[3], 255);
    assert.equal(data.at(-1), 255);
    return createHash('sha256').update(data).digest('hex');
  };
  const edits = SHOTS.map(({ start }) => hash(start + .43));
  assert.equal(new Set(edits).size, SHOTS.length);
  assert.equal(hash(.43), edits[0]);
  assert.notEqual(hash(CHAPTERS[1].start + .31), hash(CHAPTERS[1].start + 1.54));
});
