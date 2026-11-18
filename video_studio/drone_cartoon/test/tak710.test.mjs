import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFile, stat } from 'node:fs/promises';
import test from 'node:test';
import { createFilm } from '../tak710/film.mjs';
import { CHAPTERS, CUTS, DURATION, EXAMPLES, FILE, FPS, FRAME_COUNT, OUTRO, chapterAt } from '../tak710/story.mjs';
import { FILE as BULAT } from '../bulat/story.mjs';
import { FILE as GAME } from '../game/story.mjs';
import { BEAT, FILE as RHYTHM } from '../story.mjs';

test('TAK710 has five voice chapters, 15 beat-aligned cuts and three distinct settings', async () => {
  assert.ok(![BULAT, GAME, RHYTHM].includes(FILE));
  assert.equal(DURATION, 30);
  assert.equal(FPS * DURATION, FRAME_COUNT);
  assert.equal(CHAPTERS[0].start, 0);
  assert.equal(CHAPTERS.length, 5);
  assert.equal(CUTS.length, 15);
  assert.equal(CUTS.at(-1), OUTRO);
  assert.ok(OUTRO < DURATION);
  assert.deepEqual(EXAMPLES.map(({ label }) => label), ['В цехе', 'В дороге', 'В походе']);
  for (const [i, time] of CUTS.entries()) {
    assert.ok(!i || time > CUTS[i - 1]);
    assert.ok(Math.abs(time * FPS - Math.round(time * FPS)) < 1e-9);
    assert.ok(Math.abs(time - Math.round(time / BEAT) * BEAT) <= .5 / FPS);
  }
  for (const [i, { start, voice }] of CHAPTERS.entries()) {
    assert.ok(CUTS.includes(start));
    assert.equal(chapterAt(start), i);
    assert.ok(start + voice.offset < (CHAPTERS[i + 1]?.start ?? DURATION));
    assert.ok((await stat(new URL(`../vo/${voice.file}`, import.meta.url))).size > 0);
  }
  const voiceText = await readFile(new URL('../tak710/vo_text.txt', import.meta.url), 'utf8');
  assert.equal(voiceText.trim(), CHAPTERS.map(({ narration }) => narration).join('\n'));
  assert.match(voiceText, /защитная чека/);
  assert.match(voiceText, /Натяжение ремня регулирует автоматика/);
  assert.doesNotMatch(voiceText, /112|диспетчер|сто двенадцать/iu);
});

test('TAK710 renders every shot and visibly animates within the same shot', () => {
  const { draw, canvas } = createFilm(.5);
  assert.equal(canvas.width, 270);
  assert.equal(canvas.height, 480);
  const hash = (time) => {
    const rgba = draw(time).data();
    assert.equal(rgba[3], 255);
    assert.equal(rgba.at(-1), 255);
    return createHash('sha256').update(rgba).digest('hex');
  };
  const frames = CUTS.map((start) => hash(start + .42));
  assert.equal(new Set(frames).size, CUTS.length);
  assert.equal(hash(.42), frames[0]);
  // Compare the interior of the road illustration, excluding the title and progress bar.
  const interior = (t) => createHash('sha256').update(draw(t).getContext('2d').getImageData(38, 200, 200, 143).data).digest('hex');
  assert.notEqual(interior(EXAMPLES[1].start + .18), interior(EXAMPLES[1].start + .69));
});
