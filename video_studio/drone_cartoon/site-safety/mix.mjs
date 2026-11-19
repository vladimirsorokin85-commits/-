import { fileURLToPath } from 'node:url';
import { buildMaster as buildMix } from '../mix.mjs';
import { BPM, CHAPTERS, DURATION, SHOTS, SLUG } from './story.mjs';

const FINAL_HOUR = {
  file: fileURLToPath(new URL('../../music_downloaded/isaiah658-final-hour.ogg', import.meta.url)),
  start: '60.018',
  bpm: BPM,
  bedFilter: 'volume=6.2dB,alimiter=limit=.86:level=0:attack=3:release=85',
};
const cues = SHOTS.slice(1).map(({ start, kind }) => [
  start, ['archive', 'warehouse', 'landscape'].includes(kind) ? 'swipe_paper' : 'cut_tick', .25,
]);

export function buildMaster(ffmpeg, outputDir) {
  return buildMix(ffmpeg, outputDir, {
    chapters: CHAPTERS, duration: DURATION, cues, slug: SLUG,
    music: FINAL_HOUR, signalAt: null, peakTarget: -2.65,
  });
}
