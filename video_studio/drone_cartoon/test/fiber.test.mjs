import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFileSync, statSync } from 'node:fs';
import test from 'node:test';
import { buildMaster } from '../fiber/mix.mjs';
import { STORM_RIDERS } from '../mix.mjs';
import { createFilm } from '../fiber/film.mjs';
import { BPM, CHAPTERS, DETAILS, DURATION, FPS, FRAME_COUNT, SHOTS, TITLE, WIPE, chapterAt } from '../fiber/story.mjs';

const digest = (buffer) => createHash('sha256').update(buffer).digest('hex');

test('the fiber review distinguishes the card length from the photographed label', () => {
  const copy = readFileSync(new URL('../fiber/publish.txt', import.meta.url), 'utf8');
  assert.ok(copy.startsWith(`Заголовок\n${TITLE}\n\nОписание\n`));
  assert.ok(copy.includes(`Диаметр по карточке — ${DETAILS.diameter}`));
  assert.ok(copy.includes(`В карточке указано ${DETAILS.fromCard}, а на этикетке одной из катушек на фото — ${DETAILS.fromLabel}`));
  assert.equal(CHAPTERS.at(-1).narration, `В карточке — ${DETAILS.fromCard}. На этикетке этой катушки — ${DETAILS.fromLabel}.`);
});

test('fiber has six shot beats, three voice takes and the approved track', () => {
  assert.equal(FRAME_COUNT, 870);
  assert.equal(FPS, 30);
  assert.equal(SHOTS[0].start, 0);
  assert.equal(SHOTS.length, 6);
  assert.equal(typeof buildMaster, 'function');
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
  assert.equal(BPM, STORM_RIDERS.bpm);
  assert.equal(digest(readFileSync(STORM_RIDERS.file)), '85e506fcd419bc253b65ec0665946aab791d4e0f24e63e923bba694e273d196b');
});

test('fiber shot drawings are distinct and the elliptical transition preserves full-bleed framing', () => {
  const { canvas, draw, drawCover } = createFilm(.5);
  assert.deepEqual([canvas.width, canvas.height], [270,480]);
  const frame = (surface) => {
    const pixels = surface.data();
    assert.equal(pixels[3],255);
    assert.equal(pixels.at(-1),255);
    return digest(pixels);
  };
  const shots = SHOTS.map(({start}) => frame(draw(start + 1.1)));
  assert.equal(new Set(shots).size,SHOTS.length);
  const start = SHOTS.find(({ kind }) => kind === 'winding').start;
  const mid = frame(draw(start + WIPE / 2));
  assert.notEqual(mid, frame(draw(start)));
  assert.notEqual(mid, frame(draw(start + WIPE)));
  const cover = frame(drawCover());
  assert.ok(!shots.includes(cover));
  assert.equal(frame(draw(DURATION)), frame(draw(DURATION + 3)));
  assert.equal(frame(drawCover()), cover);
});
