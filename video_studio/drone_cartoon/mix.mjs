import { spawnSync } from 'node:child_process';
import { rmSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { BEEP_AT, BPM, CAT_AT, CHAPTERS, DURATION, SLUG, WORK_CUTS } from './story.mjs';

const SR = 48000;
const asset = (path) => fileURLToPath(new URL(path, import.meta.url));
const checkMusic = asset('../toolkit/music_check.py');
// The owner-uploaded MP3; permitted editions are listed in MUSIC_POLICY.md.
export const STORM_RIDERS = Object.freeze({
  file: asset('../../StockTune-Storm Riders Unleashed_1794986419.mp3'),
  start: '55.154',
  bpm: BPM,
  bedFilter: 'equalizer=f=78:t=o:w=2.4:g=1.8,volume=1.4dB,alimiter=limit=.91:level=0',
});
const signalTime = CHAPTERS[1].start + BEEP_AT;
const CUES = [
  [2.13, 'whoosh_short', .35],
  [CHAPTERS[1].start + .06, 'swipe_paper', .45],
  [signalTime, 'countdown_beeps', .91, .19],
  [CHAPTERS[2].start + .06, 'swipe_paper', .41],
  ...WORK_CUTS.slice(1).map((time, i) => [CHAPTERS[2].start + time, 'cut_tick', i % 2 ? .21 : .29]),
  [CHAPTERS[3].start + .06, 'swipe_paper', .43],
  [CHAPTERS[3].start + CAT_AT, 'pop_bubble', .46],
  [CHAPTERS[4].start + .06, 'swipe_paper', .45],
  [CHAPTERS[4].start + .86, 'text_reveal_soft', .38],
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

export function buildMaster(ffmpeg, outputDir, {
  chapters = CHAPTERS, cues = CUES, slug = SLUG, signalAt = signalTime,
  music = STORM_RIDERS, musicStart = music.start, musicStartsInFullAt, peakTarget = -1.8,
} = {}) {
  const dipStart = (signalAt - .07).toFixed(3);
  const dipEnd = (signalAt + .19).toFixed(3);
  const dip = signalAt == null ? '' :
    `,volume='if(between(t,${dipStart},${dipEnd}),1-0.66*pow(sin(PI*(t-${dipStart})/0.26),2),1)':eval=frame`;
  const lift = musicStartsInFullAt == null ? '' :
    `volume='if(isnan(t),0.61,0.61+0.39*clip((t-${(musicStartsInFullAt - .26).toFixed(3)})/0.26,0,1))':eval=frame,`;
  const stem = fileURLToPath(new URL(`.mix-${process.pid}.wav`, outputDir));
  const bed = fileURLToPath(new URL(`.bed-${process.pid}.wav`, outputDir));
  const master = fileURLToPath(new URL(`master-${slug}.wav`, outputDir));
  const voiceChain = 'highpass=f=78,equalizer=f=250:t=q:w=1:g=-2,equalizer=f=3300:t=q:w=1:g=2.2,' +
    'acompressor=threshold=.1:ratio=2.55:attack=6:release=95:makeup=2,alimiter=limit=.84:level=0';
  const graph = [
    ...chapters.map(({ start, voice }, i) => {
      const room = (chapters[i + 1]?.start ?? DURATION) - start - voice.offset - .035;
      const radio = voice.radio ? 'highpass=f=300,lowpass=f=3250,equalizer=f=1180:t=q:w=1.3:g=2.9,' : '';
      return `[${i + 1}:a]${format},${radio}${voiceChain},atempo=${voice.tempo},atrim=duration=${room.toFixed(3)},` +
        `${place(start + voice.offset)}[v${i}]`;
    }),
    ...cues.map(([t, , gain, length], i) => {
      const slice = length ? `atrim=duration=${length},afade=t=out:st=${(length - .035).toFixed(3)}:d=0.035,` : '';
      return `[${i + 1 + chapters.length}:a]${format},${slice}volume=${gain},${place(t)}[f${i}]`;
    }),
    sum('v', chapters.length, 'voices'),
    sum('f', cues.length, 'effects'),
    '[voices]aformat=sample_fmts=fltp:channel_layouts=stereo,asplit=2[vo][key]',
    `[0:a]${format},atrim=duration=${DURATION},equalizer=f=2200:t=o:w=1.7:g=-2.6,volume=1.08,${lift}` +
      `alimiter=limit=.87:level=0,afade=t=in:st=0:d=0.045,afade=t=out:st=${DURATION - .47}:d=0.47,` +
      'aformat=sample_fmts=fltp:channel_layouts=stereo[music]',
    `[music][key]sidechaincompress=threshold=.043:ratio=8:attack=8:release=203:knee=2.3${dip}[ducked]`,
    `[ducked][vo][effects]amix=inputs=3:duration=first,volume=3,alimiter=limit=.92:level=0,atrim=duration=${DURATION}[mix]`,
  ].join(';');
  try {
    // Trim and level a recorded excerpt, then verify the actual bed entering the mix.
    ff(ffmpeg, [
      '-loglevel', 'warning', '-ss', musicStart, '-i', music.file, '-t', String(DURATION),
      '-map', '0:a:0', '-af', music.bedFilter, '-ar', String(SR), '-c:a', 'pcm_f32le', bed,
    ]);
    const verified = spawnSync(process.env.PYTHON || 'python3', [checkMusic, '--tempo-hint', String(music.bpm), bed], {
      env: { ...process.env, FFMPEG_BIN: ffmpeg }, stdio: 'inherit',
    });
    if (verified.error || verified.status !== 0) {
      throw new Error('Проверка музыки не пройдена. Для неё нужны Python 3, NumPy и FFmpeg.');
    }
    ff(ffmpeg, [
      '-loglevel', 'warning', '-i', bed,
      ...chapters.flatMap(({ voice }) => ['-i', asset(`./vo/${voice.file}`)]),
      ...cues.flatMap(([, name]) => ['-i', asset(`../toolkit/sfx/${name}.mp3`)]),
      '-filter_complex', graph, '-map', '[mix]', '-ar', String(SR), '-c:a', 'pcm_f32le', stem,
    ]);
    const target = `loudnorm=I=-14:TP=${peakTarget}:LRA=7`;
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
    rmSync(bed, { force: true });
  }
}
