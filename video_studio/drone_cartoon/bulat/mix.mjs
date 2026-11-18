import { buildMaster as buildMix } from '../mix.mjs';
import { BEEP_AT, CHAPTERS, SITES, SLUG } from './story.mjs';

const CUES = [
  [.08, 'whoosh_short', .32],
  [CHAPTERS[1].start, 'swipe_paper', .38],
  [BEEP_AT, 'countdown_beeps', .92, .19],
  [CHAPTERS[2].start, 'impact_bright', .38, .42],
  ...SITES.map(({ start }, i) => [start, 'cut_tick', .34 + .02 * i]),
  [CHAPTERS[3].start, 'whoosh_short', .33],
  [CHAPTERS[4].start, 'logo_sting', .30, .64],
];

export function buildMaster(ffmpeg, outputDir) {
  return buildMix(ffmpeg, outputDir, {
    chapters: CHAPTERS,
    cues: CUES,
    slug: SLUG,
    signalAt: BEEP_AT,
    musicStartsInFullAt: CHAPTERS[2].start,
    // Extra headroom for the short cue after AAC encoding.
    peakTarget: -3.5,
  });
}
