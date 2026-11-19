import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFileSync, statSync } from 'node:fs';
import test from 'node:test';
import { createFilm } from '../incubator/film.mjs';
import { STORM_RIDERS } from '../mix.mjs';
import { BPM, CHAPTERS, DURATION, FPS, FRAME_COUNT, PHYSICAL, SHOTS, TITLE, WIPE, chapterAt } from '../incubator/story.mjs';

const digest = (buffer) => createHash('sha256').update(buffer).digest('hex');

test('the short overview keeps its timeline on the owner track and has one voice take per chapter', () => {
  assert.equal(FRAME_COUNT, 840);
  assert.equal(FPS, 30);
  assert.equal(SHOTS[0].start, 0);
  assert.equal(SHOTS.length, 8);
  for (const [i, { start }] of SHOTS.entries()) {
    assert.ok(start >= 0 && start < DURATION);
    assert.ok(Math.abs(start - Math.round(start * BPM / 60) * 60 / BPM) <= .5 / FPS);
    if (i) assert.ok(start - SHOTS[i-1].start > 1 + WIPE);
  }
  for (const [i, { start, voice }] of CHAPTERS.entries()) {
    assert.equal(chapterAt(start), i);
    assert.ok(SHOTS.some(shot => shot.start === start));
    assert.ok(voice.offset > WIPE + .02);
    assert.ok(statSync(new URL(`../vo/${voice.file}`, import.meta.url)).size > 0);
  }
  assert.equal(STORM_RIDERS.bpm, BPM);
  assert.equal(digest(readFileSync(STORM_RIDERS.file)), '85e506fcd419bc253b65ec0665946aab791d4e0f24e63e923bba694e273d196b');
});

test('the print motif opens successive shots without a blank frame or art leaking into the cover', () => {
  const { canvas, draw, drawCover } = createFilm(.5);
  assert.deepEqual([canvas.width, canvas.height], [270, 480]);
  const hash = (surface) => {
    const pixels = surface.data();
    assert.equal(pixels[3], 255);
    assert.equal(pixels.at(-1), 255);
    return digest(pixels);
  };
  const cover = hash(drawCover());
  const cuts = SHOTS.map(({ start }) => hash(draw(start + .74)));
  assert.equal(new Set(cuts).size, SHOTS.length);
  const boundary = SHOTS[4].start;
  const middle = hash(draw(boundary + WIPE / 2));
  assert.notEqual(middle, hash(draw(boundary)));
  assert.notEqual(middle, hash(draw(boundary + WIPE)));
  assert.equal(hash(draw(DURATION + 1)), hash(draw(DURATION)));
  assert.equal(hash(draw(-1)), hash(draw(0)));
  assert.equal(hash(drawCover()), cover);
});

test('the copy names the edition and attributes dimensions and mass', () => {
  const copy = readFileSync(new URL('../incubator/publish.txt', import.meta.url),'utf8');
  assert.ok(copy.startsWith(`Заголовок\n${TITLE}\n\nОписание\n`));
  assert.ok(copy.includes(PHYSICAL.size));
  assert.ok(copy.includes(`${PHYSICAL.mass} (по карточке изделия)`));
});
