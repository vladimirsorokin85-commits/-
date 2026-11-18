import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { createCanvas } from '@napi-rs/canvas';
import { FPS } from './story.mjs';

const W = 480, H = 270, BYTES = W * H * 4;
// These are the reviewed, silent excerpts, not the original recordings.
export const EXCERPTS = {
  warehouse: { frames: 127, sha256: '429b3c02ac5e7b7b1ace07f663bba9c2a669e70442480ad6d68fc6352a7ef17f' },
  landscape: { frames: 85, sha256: '1ec8c497116f0e10e8c5658d4cd5b7bf95adfafd748b9bbafd14327d746e6393' },
};

function decode(ffmpeg, name, { frames, sha256 }) {
  const source = fileURLToPath(new URL(`./assets/${name}.mp4`, import.meta.url));
  if (createHash('sha256').update(readFileSync(source)).digest('hex') !== sha256) {
    throw new Error(`Файл ${name}.mp4 отличается от проверенной вставки (см. site-safety/README.md).`);
  }
  const decoded = spawnSync(ffmpeg, [
    '-v', 'error', '-i', source, '-map', '0:v:0', '-an', '-sn', '-vf', 'format=rgba', '-f', 'rawvideo', 'pipe:1',
  ], { maxBuffer: (frames + 1) * BYTES });
  if (decoded.error) throw decoded.error;
  if (decoded.status !== 0) throw new Error(`FFmpeg не прочитал ${name}.mp4: ${decoded.stderr.toString().trim()}`);
  if (decoded.stdout.length !== frames * BYTES) throw new Error(`Неверная длина вставки ${name}.mp4.`);
  return decoded.stdout;
}

export function openBroll(ffmpeg) {
  const buffers = Object.fromEntries(Object.entries(EXCERPTS).map(([name, clip]) => [name, decode(ffmpeg, name, clip)]));
  const canvas = createCanvas(W, H), ctx = canvas.getContext('2d'), image = ctx.createImageData(W, H);
  return (name, time) => {
    const frame = Math.max(0, Math.min(EXCERPTS[name].frames - 1, Math.round(time * FPS)));
    image.data.set(buffers[name].subarray(frame * BYTES, (frame + 1) * BYTES));
    ctx.putImageData(image, 0, 0);
    return canvas;
  };
}
