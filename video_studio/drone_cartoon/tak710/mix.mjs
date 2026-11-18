import { fileURLToPath } from 'node:url';
import { buildMaster as buildMix } from '../mix.mjs';
import { BPM, CHAPTERS, DESIGN_CUT, KIT_CUT, SLUG } from './story.mjs';

const FINAL_HOUR = {
  file: fileURLToPath(new URL('../../music_downloaded/isaiah658-final-hour.ogg', import.meta.url)),
  start: '75.900',
  bpm: BPM,
  bedFilter: 'volume=6.2dB,alimiter=limit=.86:level=0:attack=3:release=85',
};

const CUES = [
  [.08, 'whoosh_short', .28],
  [CHAPTERS[1].start, 'swipe_paper', .30],
  [DESIGN_CUT, 'cut_tick', .28],
  [CHAPTERS[2].start, 'swipe_paper', .32],
  [KIT_CUT, 'cut_tick', .26],
  [CHAPTERS[3].start, 'text_reveal_soft', .27, .44],
  [CHAPTERS[4].start, 'logo_sting', .29, .63],
];

export function buildMaster(ffmpeg, outputDir) {
  return buildMix(ffmpeg, outputDir, {
    chapters: CHAPTERS,
    cues: CUES,
    slug: SLUG,
    music: FINAL_HOUR,
    // A slight music dip marks the emergency reminder, not an alarm or device sound.
    signalAt: CHAPTERS[3].start,
    musicStartsInFullAt: CHAPTERS[4].start,
    peakTarget: -2.45,
  });
}
