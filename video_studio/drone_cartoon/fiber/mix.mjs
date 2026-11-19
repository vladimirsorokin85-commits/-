import { buildMaster as mix, STORM_RIDERS } from '../mix.mjs';
import { CHAPTERS, DURATION, SHOTS, SLUG } from './story.mjs';

const cues = SHOTS.slice(1).map(({ start, kind }) => [start,
  kind === 'mark' || kind === 'packshot' ? 'text_reveal_soft' : 'swipe_paper', .25]);
export function buildMaster(ffmpeg, outputDir) {
  return mix(ffmpeg, outputDir, { slug: SLUG, chapters: CHAPTERS, duration: DURATION, cues,
    peakTarget: -2.55, music: STORM_RIDERS, signalAt: null });
}
