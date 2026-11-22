import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFileSync, statSync } from 'node:fs';
import test from 'node:test';
import { createCanvas, loadImage } from '@napi-rs/canvas';
import { createFilm } from '../vagabund/film.mjs';
import { BPM, CHAPTERS, DURATION, FPS, FRAME_COUNT, HEIGHT_LABEL, PACKSHOT, PHOTOS, SHOTS, TITLE, WEIGHT_LABEL,
  WEIGHT_NOTE, WIPE, chapterAt } from '../vagabund/story.mjs';
import { STORM_RIDERS } from '../mix.mjs';

const digest = data => createHash('sha256').update(data).digest('hex');

test('Prabos copy uses the model height, one-boot weight and a qualified description of the insert', () => {
  assert.equal(HEIGHT_LABEL,'14,5 см');
  assert.equal(WEIGHT_LABEL,'620 г');
  assert.equal(WEIGHT_NOTE,'Один ботинок · 42-й размер');
  const copy=readFileSync(new URL('../vagabund/publish.txt',import.meta.url),'utf8');
  assert.ok(copy.startsWith(`Заголовок\n${TITLE}\n\nОписание\n`));
  assert.match(copy,/вес одного ботинка 42-го размера — 620 г/);
  assert.match(copy,/не делает ботинок непробиваемым/);
  assert.match(copy,/Доставка СДЭК по России/);
  assert.match(CHAPTERS[2].narration,/помогает защитить стопу от проколов снизу/);
  assert.deepEqual(PHOTOS,['pair','angle','profile']);
  assert.deepEqual(SHOTS.map(s=>s.kind), ['hero','side','height','ankle','laces','hooks','lining','sole','materials',
    'insert','limits','days','weight','stock','packshot']);
});

test('the second boot cutout omits the separate puncture illustration', async () => {
  const im=await loadImage(readFileSync(new URL('../vagabund/assets/angle.png',import.meta.url)));
  const ctx=createCanvas(im.width,im.height).getContext('2d');
  ctx.drawImage(im,0,0);
  // This region was the center of the circular callout in the source photo.
  const {data}=ctx.getImageData(Math.floor(.79*im.width),Math.floor(.23*im.height),24,24);
  assert.ok(data.every(value=>value===0));
});

test('Prabos holds the verbatim final slogan after all takes on the original owner track', () => {
  assert.equal(FPS,30);
  assert.equal(FRAME_COUNT/FPS,DURATION);
  assert.ok(DURATION>=45 && DURATION<=60);
  assert.equal(PACKSHOT.lines.join(' '),'Не будь мишенью. Будь «В окопе»');
  assert.deepEqual(SHOTS.at(-1),{start:PACKSHOT.start,kind:'packshot'});
  assert.ok(DURATION-PACKSHOT.start-WIPE>=4);
  const measured=[14.09,10.78,12.82,11.33];
  for(const [i,{start,voice}] of CHAPTERS.entries()){
    const next=CHAPTERS[i+1]?.start??PACKSHOT.start;
    assert.equal(chapterAt(start),i);
    assert.ok(SHOTS.some(shot=>shot.start===start));
    assert.ok(next-start-voice.offset-measured[i]/voice.tempo>.3);
    assert.ok(voice.offset>WIPE);
    assert.ok(statSync(new URL(`../vo/${voice.file}`,import.meta.url)).size>0);
  }
  assert.equal(SHOTS[0].start,0);
  for(const [i,{start}] of SHOTS.entries()){
    assert.ok(Math.abs(start-Math.round(start*BPM/60)*60/BPM)<=.5/FPS);
    if(i)assert.ok(start-SHOTS[i-1].start>1.35+WIPE);
  }
  assert.equal(BPM,STORM_RIDERS.bpm);
  assert.equal(digest(readFileSync(STORM_RIDERS.file)),'85e506fcd419bc253b65ec0665946aab791d4e0f24e63e923bba694e273d196b');
});

test('Prabos renders separate portrait shots and an intervening tread wipe', () => {
  const {canvas,draw,drawCover}=createFilm(.5);
  assert.deepEqual([canvas.width,canvas.height],[270,480]);
  const hash=frame=>{
    const pixels=frame.data();
    assert.equal(pixels[3],255);
    assert.equal(pixels.at(-1),255);
    return digest(pixels);
  };
  const shots=SHOTS.map(({start})=>hash(draw(start+1)));
  assert.equal(new Set(shots).size,SHOTS.length);
  const start=CHAPTERS[2].start;
  const mid=hash(draw(start+WIPE/2));
  assert.notEqual(mid,hash(draw(start)));
  assert.notEqual(mid,hash(draw(start+WIPE)));
  assert.ok(!shots.includes(hash(drawCover())));
  assert.equal(hash(draw(DURATION)),hash(draw(DURATION+3)));
});
