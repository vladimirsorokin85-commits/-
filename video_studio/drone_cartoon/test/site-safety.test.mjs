import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFile, stat } from 'node:fs/promises';
import test from 'node:test';
import { createCanvas } from '@napi-rs/canvas';
import { EXCERPTS } from '../site-safety/broll.mjs';
import { createFilm } from '../site-safety/film.mjs';
import { BPM, CHAPTERS, CONTACTS, DURATION, FPS, FRAME_COUNT, SHOTS, chapterAt } from '../site-safety/story.mjs';

const hash = (bytes) => createHash('sha256').update(bytes).digest('hex');

test('site safety is exactly one minute, with chapter and silent excerpt ranges aligned to frames', async () => {
  assert.deepEqual([DURATION, FPS, FRAME_COUNT], [60, 30, 1800]);
  assert.equal(SHOTS[0].start, 0);
  assert.equal(CHAPTERS.length, 6);
  assert.deepEqual(CONTACTS, []);
  assert.equal(SHOTS.filter(({ kind }) => kind === 'archive').length, 2);
  for (const [i, { start, kind }] of SHOTS.entries()) {
    const next = SHOTS[i + 1]?.start ?? DURATION;
    assert.ok(next > start);
    assert.ok(Math.abs(start * FPS - Math.round(start * FPS)) < 1e-9);
    const beat = 60 / BPM;
    assert.ok(Math.abs(start - Math.round(start / beat) * beat) <= .5 / FPS);
    if (Object.hasOwn(EXCERPTS, kind)) assert.equal(Math.round((next - start) * FPS), EXCERPTS[kind].frames);
  }
  assert.deepEqual(SHOTS.filter(({ kind }) => Object.hasOwn(EXCERPTS, kind)).map(({ kind }) => kind), ['warehouse', 'landscape']);
  for (const [kind, { sha256 }] of Object.entries(EXCERPTS)) {
    assert.equal(hash(await readFile(new URL(`../site-safety/assets/${kind}.mp4`, import.meta.url))), sha256);
  }
  for (const [i, { start, voice }] of CHAPTERS.entries()) {
    assert.equal(chapterAt(start), i);
    assert.ok(SHOTS.some((shot) => shot.start === start));
    assert.ok((await stat(new URL(`../vo/${voice.file}`, import.meta.url))).size > 0);
  }
});

test('site safety draws distinct illustrated scenes, photos and separately timed video inserts', () => {
  const insert = createCanvas(480, 270), ctx = insert.getContext('2d');
  const calls = [];
  const film = createFilm(.5, { footage(kind, t) {
    calls.push({ kind, frame: Math.round(t * FPS) });
    ctx.fillStyle = kind === 'warehouse' ? '#945629' : '#327163';
    ctx.fillRect(0, 0, 480, 270);
    return insert;
  } });
  assert.deepEqual([film.canvas.width, film.canvas.height], [270, 480]);
  const frames = SHOTS.map(({ start }) => hash(film.draw(start + .4).data()));
  assert.equal(new Set(frames).size, frames.length);
  assert.deepEqual(calls, [{ kind: 'warehouse', frame: 12 }, { kind: 'landscape', frame: 12 }]);
  assert.equal(hash(film.draw(.4).data()), frames[0]);
});
