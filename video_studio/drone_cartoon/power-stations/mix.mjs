import { fileURLToPath } from 'node:url';
import { buildMaster as buildMix } from '../mix.mjs';
import { BPM, CHAPTERS, DURATION, SHOTS, SLUG } from './story.mjs';

const music = {
  file: fileURLToPath(new URL('../../music_downloaded/isaiah658-final-hour.ogg', import.meta.url)),
  start: '60.018', bpm: BPM,
  bedFilter: 'volume=6.2dB,alimiter=limit=.86:level=0:attack=3:release=85',
};
const cues = SHOTS.slice(1).map(({ start, kind }, i) => [
  start, kind === 'outro' ? 'text_reveal_soft' : i % 2 ? 'swipe_paper' : 'cut_tick', .29,
]);
export function buildMaster(ffmpeg, outputDir) {
  return buildMix(ffmpeg, outputDir, {
    chapters: CHAPTERS, duration: DURATION, cues, slug: SLUG, music, signalAt: null, peakTarget: -2.65,
  });
}
