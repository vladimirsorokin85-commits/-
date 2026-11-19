import { buildMaster as mix, STORM_RIDERS } from '../mix.mjs';
import { CHAPTERS, DURATION, SHOTS, SLUG } from './story.mjs';

const cues = SHOTS.slice(1).map(({ start, kind }) => [start,
  kind === 'passport' ? 'text_reveal_soft' : 'swipe_paper', .23]);

export function buildMaster(ffmpeg, outputDir) {
  return mix(ffmpeg, outputDir, { chapters: CHAPTERS, duration: DURATION, cues, slug: SLUG,
    music: STORM_RIDERS, signalAt: null, peakTarget: -2.6 });
}
