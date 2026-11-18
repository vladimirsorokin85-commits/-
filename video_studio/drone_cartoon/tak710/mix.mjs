import { buildMaster as buildMix, STORM_RIDERS } from '../mix.mjs';
import { AUTO_CUTS, CHAPTERS, DETAIL_CUTS, EXAMPLES, HERO_CUTS, OUTRO, RECAP, SLUG } from './story.mjs';

// Editorial accents only, not sounds of the device or an activation sequence.
const CUES = [
  [0, 'impact_bright', .31, .32],
  [HERO_CUTS[1], 'whoosh_short', .32],
  [HERO_CUTS[2], 'cut_tick', .30],
  [DETAIL_CUTS[0], 'swipe_paper', .39],
  ...DETAIL_CUTS.slice(1).map((t) => [t, 'cut_tick', .32]),
  [AUTO_CUTS[0], 'impact_deep', .27, .34],
  [AUTO_CUTS[1], 'cut_tick', .25],
  [AUTO_CUTS[2], 'swipe_paper', .31],
  [AUTO_CUTS[3], 'cut_tick', .28],
  ...EXAMPLES.map(({ start }, i) => [start, i ? 'cut_tick' : 'swipe_paper', .33]),
  [RECAP, 'whoosh_short', .33],
  [OUTRO, 'logo_sting', .32, .63],
];

export function buildMaster(ffmpeg, outputDir) {
  return buildMix(ffmpeg, outputDir, {
    chapters: CHAPTERS,
    cues: CUES,
    slug: SLUG,
    // Explicitly requested by the owner: the same uploaded Storm Riders MP3 as Bulat.
    music: STORM_RIDERS,
    signalAt: null,
    peakTarget: -2.65,
  });
}
