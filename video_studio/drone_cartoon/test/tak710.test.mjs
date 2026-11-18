import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFile, stat } from 'node:fs/promises';
import test from 'node:test';
import { createFilm } from '../tak710/film.mjs';
import { CHAPTERS, DESIGN_CUT, DURATION, FILE, FPS, FRAME_COUNT, KIT_CUT, chapterAt } from '../tak710/story.mjs';
import { FILE as BULAT } from '../bulat/story.mjs';
import { FILE as GAME } from '../game/story.mjs';
import { FILE as RHYTHM } from '../story.mjs';

test('TAK710 is a separate 30-second edition with frame-aligned chapters and recorded narration', async () => {
  assert.ok(![BULAT, GAME, RHYTHM].includes(FILE));
  assert.equal(DURATION, 30);
  assert.equal(FPS * DURATION, FRAME_COUNT);
  assert.equal(CHAPTERS[0].start, 0);
  assert.equal(CHAPTERS.length, 5);
  assert.ok(CHAPTERS[1].start < DESIGN_CUT && DESIGN_CUT < CHAPTERS[2].start);
  assert.ok(CHAPTERS[2].start < KIT_CUT && KIT_CUT < CHAPTERS[3].start);
  for (const time of [DESIGN_CUT, KIT_CUT, ...CHAPTERS.map(({ start }) => start)]) {
    assert.ok(Math.abs(time * FPS - Math.round(time * FPS)) < 1e-9);
  }
  for (const [i, { start, voice }] of CHAPTERS.entries()) {
    assert.equal(chapterAt(start), i);
    assert.ok(start + voice.offset < (CHAPTERS[i + 1]?.start ?? DURATION));
    assert.ok((await stat(new URL(`../vo/${voice.file}`, import.meta.url))).size > 0);
  }
  const voiceText = await readFile(new URL('../tak710/vo_text.txt', import.meta.url), 'utf8');
  assert.equal(voiceText.trim(), CHAPTERS.map(({ narration }) => narration).join('\n'));
  assert.match(CHAPTERS[3].label, /112/);
  assert.match(CHAPTERS[3].narration, /Следуйте указаниям диспетчера/);
});

test('TAK710 renders an animated product, distinct close-ups, civil context and end cards', () => {
  const { draw, canvas } = createFilm(.5);
  assert.equal(canvas.width, 270);
  assert.equal(canvas.height, 480);
  const hash = (time) => {
    const rgba = draw(time).data();
    assert.equal(rgba[3], 255);
    assert.equal(rgba.at(-1), 255);
    return createHash('sha256').update(rgba).digest('hex');
  };
  const times = [2.1, 2.3, ...CHAPTERS.slice(1).map(({ start }) => start + .6), DESIGN_CUT + .6, KIT_CUT + .6];
  const frames = times.map(hash);
  assert.equal(new Set(frames).size, times.length);
  assert.equal(hash(times[0]), frames[0]);
});
