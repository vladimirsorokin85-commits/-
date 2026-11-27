import { buildMaster as buildMix, STORM_RIDERS } from '../mix.mjs';
import { BPM, CHAPTERS, DURATION, SHOTS, SLUG } from './story.mjs';

// Fit the supplied recording to the existing cut grid, without altering pitch or video.
const music = {
  ...STORM_RIDERS,
  bpm: BPM,
  bedFilter: `atempo=${(BPM / STORM_RIDERS.bpm).toFixed(6)},${STORM_RIDERS.bedFilter}`,
};
const cues = SHOTS.slice(1).map(({ start, kind }, i) => [
  start, kind === 'outro' ? 'text_reveal_soft' : i % 2 ? 'swipe_paper' : 'cut_tick', .29,
]);
export function buildMaster(ffmpeg, outputDir) {
  return buildMix(ffmpeg, outputDir, {
    chapters: CHAPTERS, duration: DURATION, cues, slug: SLUG, music, signalAt: null, peakTarget: -2.65,
  });
}
