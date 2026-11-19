import { buildMaster as mix, STORM_RIDERS } from '../mix.mjs';
import { CHAPTERS, DURATION, SHOTS, SLUG } from './story.mjs';

const major = new Set(CHAPTERS.map(({ start }) => start));
const cues = SHOTS.slice(1).map(({ start, kind }) => {
  if (kind === 'end') return [start, 'text_reveal_soft', .33];
  return major.has(start) ? [start, 'swipe_paper', .29] : [start, 'cut_tick', .20];
});
export function buildMaster(ffmpeg, outputDir) {
  return mix(ffmpeg, outputDir, { chapters: CHAPTERS, duration: DURATION, cues, slug: SLUG,
    music: STORM_RIDERS, signalAt: null, peakTarget: -2.65 });
}
