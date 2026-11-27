import { buildMaster as buildMix, STORM_RIDERS } from '../mix.mjs';
import { CHAPTERS, DURATION, SHOTS, SLUG } from './story.mjs';

const cues = [
  [1.38, 'swipe_paper', .24],
  ...SHOTS.slice(1).map(({ start, kind }, i) => [
    start, kind === 'end' ? 'text_reveal_soft' : i % 2 ? 'cut_tick' : 'swipe_paper', .25,
  ]),
];
export function buildMaster(ffmpeg, outputDir) {
  return buildMix(ffmpeg, outputDir, {
    chapters: CHAPTERS, duration: DURATION, cues, slug: SLUG,
    music: STORM_RIDERS, signalAt: null, peakTarget: -2.65,
  });
}
