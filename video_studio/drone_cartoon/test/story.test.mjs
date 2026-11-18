import { createHash } from 'node:crypto';
import assert from 'node:assert/strict';
import test from 'node:test';
import { createFilm, HEIGHT, WIDTH } from '../film.mjs';
import { CHAPTERS, DURATION, FPS, WIPE, chapterAt } from '../story.mjs';

const hash = (data) => createHash('sha256').update(data).digest('hex');

test('four scenes cover the timeline and start on whole frames', () => {
  assert.equal(CHAPTERS.length, 4);
  assert.equal(CHAPTERS[0].start, 0);
  assert.equal(DURATION * FPS, 720);
  for (const [i, { start }] of CHAPTERS.entries()) {
    assert.ok(Math.abs(start * FPS - Math.round(start * FPS)) < 1e-9);
    assert.equal(chapterAt(start), i);
    assert.equal(chapterAt(start + WIPE + .02), i);
    assert.ok((CHAPTERS[i + 1]?.start ?? DURATION) - start > WIPE);
  }
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
});
