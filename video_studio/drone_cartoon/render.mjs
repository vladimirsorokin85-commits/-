import { spawn, spawnSync } from 'node:child_process';
import { mkdir, rename, rm, writeFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { createFilm, WIDTH, HEIGHT } from './film.mjs';
import { CHAPTERS, DURATION, FPS } from './story.mjs';

const require = createRequire(import.meta.url);
function ffmpegPath() {
  if (process.env.FFMPEG_BIN) return process.env.FFMPEG_BIN;
  if (spawnSync('ffmpeg', ['-version'], { stdio: 'ignore' }).status === 0) return 'ffmpeg';
  try {
    return require('@ffmpeg-installer/ffmpeg').path;
  } catch {
    throw new Error('FFmpeg не найден. Установите FFmpeg (с libx264) или задайте FFMPEG_BIN.');
  }
}

// Timestamp, CC0 sound effect from toolkit/sfx, linear gain. No music or speech.
const CUES = [
  [.21, 'swipe_paper', .38],
  [1.77, 'text_reveal_soft', .38],
  [CHAPTERS[1].start + .07, 'swipe_paper', .45],
  [CHAPTERS[1].start + 2.42, 'cut_tick', .47],
  [CHAPTERS[1].start + 2.59, 'pop_bubble', .40],
  [CHAPTERS[2].start + .07, 'whoosh_short', .48],
  [CHAPTERS[2].start + .94, 'text_reveal_soft', .40],
  [CHAPTERS[3].start + .07, 'swipe_paper', .42],
  [CHAPTERS[3].start + .92, 'logo_sting', .46],
];
const SR = 48000;
const sfx = (name) => fileURLToPath(new URL(`../toolkit/sfx/${name}.mp3`, import.meta.url));
const audioGraph = CUES.map(([time, , gain], i) => {
  const ms = Math.round(time * 1000);
  return `[${i + 1}:a]aresample=${SR},aformat=channel_layouts=stereo,asetpts=PTS-STARTPTS,` +
    `volume=${gain},adelay=${ms}|${ms},apad=whole_len=${DURATION * SR}[cue${i}]`;
}).join(';') + ';' + CUES.map((_, i) => `[cue${i}]`).join('') +
  `amix=inputs=${CUES.length}:duration=longest,volume=${CUES.length},alimiter=limit=0.85:level=0[a]`;

async function render({ draft }) {
  const scale = draft ? 1 : 2;
  const film = createFilm(scale);
  const output = new URL('./output/', import.meta.url);
  const basename = `dron-nad-obektom${draft ? '-draft' : ''}`;
  const destination = new URL(`${basename}.mp4`, output);
  const temp = new URL(`.${basename}.${process.pid}.mp4`, output);
  await mkdir(output, { recursive: true });
  const encoder = spawn(ffmpegPath(), [
    '-hide_banner', '-loglevel', 'warning', '-y',
    '-f', 'rawvideo', '-pixel_format', 'rgba', '-video_size', `${WIDTH * scale}x${HEIGHT * scale}`,
    '-framerate', String(FPS), '-i', 'pipe:0',
    ...CUES.flatMap(([, name]) => ['-i', sfx(name)]),
    '-filter_complex', audioGraph, '-map', '0:v:0', '-map', '[a]',
    '-t', String(DURATION), '-c:v', 'libx264', '-preset', 'veryfast', '-crf', draft ? '23' : '19',
    '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-ar', String(SR), '-b:a', '160k',
    '-movflags', '+faststart', '-f', 'mp4', fileURLToPath(temp),
  ], { stdio: ['pipe', 'ignore', 'inherit'] });
  const exited = new Promise((resolve) => {
    encoder.once('error', (error) => resolve({ error }));
    encoder.once('close', (code, signal) => resolve({ code, signal }));
  });
  let pipeError;
  encoder.stdin.on('error', (error) => { pipeError = error; });
  try {
    for (let frame = 0; frame < DURATION * FPS; frame++) {
      if (pipeError) throw pipeError;
      const pixels = film.draw(frame / FPS).data();
      // A write callback bounds memory and lets FFmpeg apply back pressure.
      await new Promise((resolve, reject) => encoder.stdin.write(pixels, (error) => error ? reject(error) : resolve()));
      if (frame % (FPS * 4) === 0) console.log(`Рендер: ${frame / FPS} / ${DURATION} с`);
    }
    encoder.stdin.end();
    const { code, signal, error } = await exited;
    if (error) throw error;
    if (code !== 0) throw new Error(`FFmpeg завершился: ${signal || code}`);
    if (!draft) await writeFile(new URL('cover.jpg', output), film.draw(2.7).toBuffer('image/jpeg', 91));
    await rename(temp, destination);
    console.log(`Готово: ${fileURLToPath(destination)}`);
  } catch (error) {
    encoder.stdin.destroy();
    encoder.kill();
    const result = await exited;
    throw result.error ?? error;
  } finally {
    await rm(temp, { force: true });
  }
}

const args = process.argv.slice(2);
if (args.some((arg) => arg !== '--draft')) {
  console.error('Использование: npm run render [-- --draft]');
  process.exitCode = 2;
} else {
  try {
    await render({ draft: args.includes('--draft') });
  } catch (error) {
    console.error(error.message);
    process.exitCode = 1;
  }
}
