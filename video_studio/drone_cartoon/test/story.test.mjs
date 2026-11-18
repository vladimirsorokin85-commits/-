import { createHash } from 'node:crypto';
import assert from 'node:assert/strict';
import test from 'node:test';
import { createFilm, HEIGHT, WIDTH } from '../film.mjs';
import { BEEP_AT, BEAT, CAT_AT, CHAPTERS, CONTACTS, DURATION, FPS, FRAME_COUNT, WIPE, WORK_CUTS, chapterAt } from '../story.mjs';

const hash = (data) => createHash('sha256').update(data).digest('hex');

test('five scenes cover 30 seconds and start on whole frames', () => {
  assert.equal(CHAPTERS.length, 5);
  for (const [i, beat] of [0, 12, 24, 56, 72].entries()) {
    assert.ok(Math.abs(CHAPTERS[i].start - beat * BEAT) <= .5 / FPS + 1e-9);
  }
  assert.equal(DURATION, 30);
  assert.equal(DURATION * FPS, FRAME_COUNT);
  for (const [i, { start }] of CHAPTERS.entries()) {
    assert.ok(Math.abs(start * FPS - Math.round(start * FPS)) < 1e-9);
    assert.equal(chapterAt(start), i);
    assert.equal(chapterAt(start + WIPE + .02), i);
    const length = (CHAPTERS[i + 1]?.start ?? DURATION) - start;
    assert.ok(length > WIPE);
    assert.ok(CHAPTERS[i].narration.length > 0 && CHAPTERS[i].voice.offset < length);
  }
});

test('matches the approved final slogan in the card and transcript', () => {
  const { heading, narration } = CHAPTERS.at(-1);
  const slogan = 'Не будь мишенью. Будь «В окопе»!';
  assert.equal(heading.join(' '), slogan);
  assert.equal(narration, slogan);
});

test('code-drawn frames are opaque, deterministic, and distinct across scenes', () => {
  const { canvas, draw } = createFilm(.5);
  assert.equal(canvas.width, WIDTH / 2);
  assert.equal(canvas.height, HEIGHT / 2);
  function frameHash(time) {
    // Canvas data is a native view; consume it before drawing the next frame.
    const frame = draw(time).data();
    assert.equal(frame.length, canvas.width * canvas.height * 4);
    assert.equal(frame[3], 255);
    assert.equal(frame.at(-1), 255);
    return hash(frame);
  }
  const frames = CHAPTERS.map(({ start }) => frameHash(start + 2.7));
  assert.equal(new Set(frames).size, CHAPTERS.length);
  assert.equal(frameHash(2.7), frames[0]);
  assert.notEqual(frameHash(3.25), frames[0]);
  assert.notEqual(frameHash(CHAPTERS[1].start + WIPE / 2), frames[1]);
  assert.notEqual(frameHash(CHAPTERS[1].start + BEEP_AT - .2), frameHash(CHAPTERS[1].start + BEEP_AT + .5));
  assert.notEqual(frameHash(CHAPTERS[3].start + CAT_AT - .2), frameHash(CHAPTERS[3].start + CAT_AT + .5));
  assert.deepEqual(CONTACTS.map(({ href }) => new URL(href).hostname), ['t.me', 'vk.com', 'www.avito.ru']);
  assert.equal(WORK_CUTS.length, 8);
  const beats = WORK_CUTS.map((cut) => frameHash(CHAPTERS[2].start + cut + .58));
  assert.equal(new Set(beats).size, WORK_CUTS.length);
  for (let i = 1; i < WORK_CUTS.length; i++) {
    assert.ok(Math.abs((WORK_CUTS[i] - WORK_CUTS[i - 1]) - 4 * BEAT) < 1 / FPS);
  }
});
