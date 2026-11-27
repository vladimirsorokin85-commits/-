import { buildMaster as buildMix } from '../mix.mjs';
import { BEEP_AT, CHAPTERS, GAME_OVER_AT, POV_SHOTS, SLUG } from './story.mjs';

const CUES = [
  [.06, 'riser_tension', .29, 5.42],
  ...POV_SHOTS.slice(1).map(({ start }, i) => [start, 'cut_tick', .31 + .02 * i]),
  [6.02, 'rewind_sweep', .47, .54],
  [BEEP_AT, 'countdown_beeps', .94, .19],
  [GAME_OVER_AT, 'impact_deep', .51, .40],
  [12.84, 'whoosh_transition', .37, .48],
  [13, 'impact_bright', .56, .45],
  [22, 'cut_tick', .28],
  [23, 'cut_tick', .28],
  [24, 'cut_tick', .30],
  [25, 'logo_sting', .35, .72],
];

export function buildMaster(ffmpeg, outputDir) {
  return buildMix(ffmpeg, outputDir, {
    chapters: CHAPTERS,
    cues: CUES,
    slug: SLUG,
    signalAt: BEEP_AT,
    musicStart: '55.255',
    musicStartsInFullAt: 13,
    peakTarget: -2.15,
  });
}
