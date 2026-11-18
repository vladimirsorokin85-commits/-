import { spawnSync } from 'node:child_process';
import { rmSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { ALERT_AT, CHAPTERS, DURATION } from './story.mjs';

const SR = 48000;
const musicFile = fileURLToPath(new URL('../music_downloaded/fvi-BeatOne.ogg', import.meta.url));
const checkMusic = fileURLToPath(new URL('../toolkit/music_check.py', import.meta.url));
const asset = (path) => fileURLToPath(new URL(path, import.meta.url));
// Section of the existing 162 BPM master starting just before a drum transient.
const MUSIC_START = '68.185';
const CUES = [
  [2.22, 'whoosh_short', .42],
  [5.07, 'swipe_paper', .43],
  [6.1, 'cut_tick', .34],
  [10.06, 'swipe_paper', .52],
  [10 + ALERT_AT, 'pop_bubble', .65],
  [18.07, 'swipe_paper', .43],
  [20.19, 'cut_tick', .37],
  [22.39, 'cut_tick', .37],
  [25.06, 'swipe_paper', .43],
  [26.12, 'text_reveal_soft', .45],
];

const format = `aresample=${SR},aformat=channel_layouts=stereo,asetpts=PTS-STARTPTS`;
function place(seconds) {
  const ms = Math.round(seconds * 1000);
  return `adelay=${ms}|${ms},apad=whole_len=${DURATION * SR}`;
}
// Equal-length layers let this work on older FFmpeg without amix's normalize option.
function sum(prefix, count, out) {
  return Array.from({ length: count }, (_, i) => `[${prefix}${i}]`).join('') +
    `amix=inputs=${count}:duration=longest,volume=${count}[${out}]`;
}
function ff(ffmpeg, args, capture = false) {
  const result = spawnSync(ffmpeg, ['-hide_banner', '-y', ...args], {
    encoding: 'utf8', maxBuffer: 2 * 1024 * 1024,
    stdio: capture ? ['ignore', 'ignore', 'pipe'] : ['ignore', 'ignore', 'inherit'],
  });
  if (result.error) throw result.error;
  if (result.status !== 0) throw new Error(result.stderr?.trim() || `FFmpeg: код ${result.status}`);
  return result.stderr;
}

export function buildMaster(ffmpeg, outputDir) {
  const verified = spawnSync(process.env.PYTHON || 'python3', [checkMusic, musicFile], {
    env: { ...process.env, FFMPEG_BIN: ffmpeg }, stdio: 'inherit',
  });
  if (verified.error || verified.status !== 0) {
    throw new Error('Проверка музыки не пройдена. Для неё нужны Python 3, NumPy и FFmpeg.');
  }
  const stem = fileURLToPath(new URL(`.mix-${process.pid}.wav`, outputDir));
  const master = fileURLToPath(new URL('master-znat-vovremya.wav', outputDir));
  const voiceChain = 'highpass=f=78,equalizer=f=250:t=q:w=1:g=-2,equalizer=f=3300:t=q:w=1:g=2.2,' +
    'acompressor=threshold=.1:ratio=2.55:attack=6:release=95:makeup=2,alimiter=limit=.84:level=0';
  const graph = [
    ...CHAPTERS.map(({ start, voice }, i) => {
      const room = (CHAPTERS[i + 1]?.start ?? DURATION) - start - voice.offset - .035;
      return `[${i + 1}:a]${format},${voiceChain},atempo=${voice.tempo},atrim=duration=${room.toFixed(3)},` +
        `${place(start + voice.offset)}[v${i}]`;
    }),
    ...CUES.map(([t, , gain], i) =>
      `[${i + 1 + CHAPTERS.length}:a]${format},volume=${gain},${place(t)}[f${i}]`),
    sum('v', CHAPTERS.length, 'voices'),
    sum('f', CUES.length, 'effects'),
    '[voices]aformat=sample_fmts=fltp:channel_layouts=stereo,asplit=2[vo][key]',
    `[0:a]${format},atrim=duration=${DURATION},equalizer=f=2200:t=o:w=1.7:g=-2.3,volume=1.2,` +
      `alimiter=limit=.87:level=0,afade=t=in:st=0:d=0.045,afade=t=out:st=${DURATION - .47}:d=0.47,` +
      'aformat=sample_fmts=fltp:channel_layouts=stereo[music]',
    '[music][key]sidechaincompress=threshold=.043:ratio=8:attack=8:release=203:knee=2.3[ducked]',
    `[ducked][vo][effects]amix=inputs=3:duration=first,volume=3,alimiter=limit=.92:level=0,atrim=duration=${DURATION}[mix]`,
  ].join(';');
  try {
    ff(ffmpeg, [
      '-loglevel', 'warning', '-ss', MUSIC_START, '-t', String(DURATION), '-i', musicFile,
      ...CHAPTERS.flatMap(({ voice }) => ['-i', asset(`./vo/${voice.file}`)]),
      ...CUES.flatMap(([, name]) => ['-i', asset(`../toolkit/sfx/${name}.mp3`)]),
      '-filter_complex', graph, '-map', '[mix]', '-ar', String(SR), '-c:a', 'pcm_f32le', stem,
    ]);
    const target = 'loudnorm=I=-14:TP=-1.8:LRA=7';
    const report = ff(ffmpeg, ['-i', stem, '-af', `${target}:print_format=json`, '-f', 'null', '-'], true);
    const measurement = JSON.parse(report.match(/\{[^{}]*"input_i"[^{}]*\}/s)?.[0] ?? '{}');
    const names = { measured_I: 'input_i', measured_TP: 'input_tp', measured_LRA: 'input_lra',
      measured_thresh: 'input_thresh', offset: 'target_offset' };
    const measured = Object.entries(names).map(([key, name]) => {
      if (!Number.isFinite(Number(measurement[name]))) throw new Error(`Нет измерения громкости: ${name}`);
      return `${key}=${measurement[name]}`;
    });
    ff(ffmpeg, ['-loglevel', 'warning', '-i', stem, '-af', `${target}:${measured.join(':')}:linear=true`,
      '-ar', String(SR), '-c:a', 'pcm_s16le', master]);
    return master;
  } finally {
    rmSync(stem, { force: true });
  }
}
