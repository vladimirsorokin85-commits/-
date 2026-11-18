import { spawn, spawnSync } from 'node:child_process';
import { mkdir, rename, rm, writeFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

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

async function render({ draft, prefix, posterAt }) {
  const [{ createFilm, WIDTH, HEIGHT }, { DURATION, FPS, FRAME_COUNT, SLUG }, { buildMaster }] =
    await Promise.all(['film.mjs', 'story.mjs', 'mix.mjs'].map((module) => import(prefix + module)));
  const scale = draft ? 1 : 2;
  const output = new URL('./output/', import.meta.url);
  const basename = `${SLUG}${draft ? '-draft' : ''}`;
  const destination = new URL(`${basename}.mp4`, output);
  const temp = new URL(`.${basename}.${process.pid}.mp4`, output);
  await mkdir(output, { recursive: true });
  const ffmpeg = ffmpegPath();
  const film = createFilm(scale, { ffmpeg });
  console.log('Сведение: диктор, музыка и монтажные эффекты');
  const audio = buildMaster(ffmpeg, output);
  const encoder = spawn(ffmpeg, [
    '-hide_banner', '-loglevel', 'warning', '-y',
    '-f', 'rawvideo', '-pixel_format', 'rgba', '-video_size', `${WIDTH * scale}x${HEIGHT * scale}`,
    '-framerate', String(FPS), '-i', 'pipe:0',
    '-i', audio, '-map', '0:v:0', '-map', '1:a:0',
    '-t', String(DURATION), '-c:v', 'libx264', '-preset', 'veryfast', '-crf', draft ? '23' : '19',
    '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-ar', '48000', '-b:a', '192k',
    '-movflags', '+faststart', '-f', 'mp4', fileURLToPath(temp),
  ], { stdio: ['pipe', 'ignore', 'inherit'] });
  const exited = new Promise((resolve) => {
    encoder.once('error', (error) => resolve({ error }));
    encoder.once('close', (code, signal) => resolve({ code, signal }));
  });
  let pipeError;
  encoder.stdin.on('error', (error) => { pipeError = error; });
  try {
    for (let frame = 0; frame < FRAME_COUNT; frame++) {
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
    if (!draft) await writeFile(new URL(`${SLUG}.jpg`, output), film.draw(posterAt).toBuffer('image/jpeg', 91));
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

const editions = {
  '--game-over': { prefix: './game/', posterAt: 11.3 },
  '--bulat': { prefix: './bulat/', posterAt: 2.9 },
  '--tak710': { prefix: './tak710/', posterAt: 2.7 },
  '--site-safety': { prefix: './site-safety/', posterAt: 1.7 },
};
const args = process.argv.slice(2);
const selected = args.filter((flag) => Object.hasOwn(editions, flag));
if (selected.length > 1 || args.some((arg) => arg !== '--draft' && !Object.hasOwn(editions, arg))) {
  console.error('Использование: npm run render / render:game / render:bulat / render:tak710 / render:site-safety [-- --draft]');
  process.exitCode = 2;
} else {
  try {
    const edition = editions[selected[0]] ?? { prefix: './', posterAt: 3.2 };
    await render({ draft: args.includes('--draft'), ...edition });
  } catch (error) {
    console.error(error.message);
    process.exitCode = 1;
  }
}
