import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFileSync, statSync } from 'node:fs';
import test from 'node:test';
import { createFilm } from '../saber/film.mjs';
import { BPM, CHAPTERS, DURATION, FPS, FRAME_COLORS, FRAME_COUNT, LENSES, PACKSHOT, PHOTOS, SHOTS,
  TITLE, WIPE, chapterAt } from '../saber/story.mjs';
import { STORM_RIDERS } from '../mix.mjs';

const hash = value => createHash('sha256').update(value).digest('hex');

test('Saber is a stock walkthrough with separate frame colours, lens tints and publish copy', () => {
  assert.deepEqual(FRAME_COLORS, ['Чёрная','Оливковая','Песочная']);
  assert.deepEqual(Object.values(LENSES).map(lens => lens.name), ['Clear','Smoke Grey','Light Rust']);
  assert.equal(new Set(PHOTOS).size, 8);
  assert.deepEqual(SHOTS.map(shot => shot.kind), ['hero','stack','colors','box','lenses','clear','smoke','rust',
    'profile','arm','nose','extras','case','clasp','full','packshot']);
  const copy = readFileSync(new URL('../saber/publish.txt', import.meta.url), 'utf8');
  assert.ok(copy.startsWith(`Заголовок\n${TITLE}\n\nОписание\nНа складе`));
  for (const text of [copy, ...CHAPTERS.map(chapter => chapter.narration)]) {
    assert.doesNotMatch(text, /карточк|гаранти|оригинальн|MIL-PRF|\d+ мм/iu);
  }
});

test('Saber timing fits each uncut voice take and holds the exact final slogan', () => {
  assert.equal(FPS, 30);
  assert.ok(DURATION >= 45 && DURATION <= 60);
  assert.equal(FRAME_COUNT / FPS, DURATION);
  assert.equal(SHOTS[0].start, 0);
  for (const [i, { start }] of SHOTS.entries()) {
    assert.ok(Math.abs(start - Math.round(start * BPM / 60) * 60 / BPM) <= .5 / FPS);
    if (i) assert.ok(start - SHOTS[i - 1].start > 1.5 + WIPE);
  }
  const recordedSeconds = [12.50, 13.58, 11.74, 11.90];
  assert.equal(CHAPTERS.length, recordedSeconds.length);
  for (const [i, { start, voice }] of CHAPTERS.entries()) {
    const next = CHAPTERS[i + 1]?.start ?? PACKSHOT.start;
    assert.equal(chapterAt(start), i);
    assert.ok(SHOTS.some(shot => shot.start === start));
    assert.ok(voice.offset > WIPE + .02);
    assert.ok(next - start - voice.offset - recordedSeconds[i] / voice.tempo > .25);
    assert.ok(statSync(new URL(`../vo/${voice.file}`, import.meta.url)).size > 0);
  }
  assert.deepEqual(SHOTS.at(-1), { start: PACKSHOT.start, kind: 'packshot' });
  assert.equal(PACKSHOT.lines.join(' '), 'Не будь мишенью. Будь «В окопе»');
  assert.ok(DURATION - PACKSHOT.start - WIPE > 4);
});

test('Saber uses the stock track and draws distinct full-size shots with a lens wipe', () => {
  assert.equal(BPM, STORM_RIDERS.bpm);
  assert.equal(hash(readFileSync(STORM_RIDERS.file)), '85e506fcd419bc253b65ec0665946aab791d4e0f24e63e923bba694e273d196b');
  const { canvas, draw, drawCover } = createFilm(.5);
  assert.deepEqual([canvas.width, canvas.height], [270,480]);
  const frame = surface => {
    const pixels = surface.data();
    assert.equal(pixels[3], 255);
    assert.equal(pixels.at(-1), 255);
    return hash(pixels);
  };
  const shots = SHOTS.map(({ start }) => frame(draw(start + 1)));
  assert.equal(new Set(shots).size, SHOTS.length);
  const { start } = SHOTS.find(({ kind }) => kind === 'rust');
  const mid = frame(draw(start + WIPE / 2));
  assert.notEqual(mid, frame(draw(start)));
  assert.notEqual(mid, frame(draw(start + WIPE)));
  assert.ok(!shots.includes(frame(drawCover())));
  assert.equal(frame(draw(DURATION)), frame(draw(DURATION + 1)));
});
