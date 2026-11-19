import { buildMaster as mix, STORM_RIDERS } from '../mix.mjs';
import { CHAPTERS, DURATION, PACKSHOT, SHOTS, SLUG } from './story.mjs';

const major = new Set(CHAPTERS.map(({ start }) => start));
const cues = SHOTS.slice(1).map(({ start, kind }) => kind === 'packshot'
  ? [start, 'text_reveal_soft', .29]
  : major.has(start) ? [start, 'swipe_paper', .26] : [start, 'cut_tick', .19]);

// Bring up the same recording when the narration ends; leave the spoken sections untouched.
const riseAt = (PACKSHOT.start - .12).toFixed(3);
const music = {
  ...STORM_RIDERS,
  bedFilter: `${STORM_RIDERS.bedFilter},` +
    `volume='if(isnan(t),1,1+1.6*clip((t-${riseAt})/.46,0,1))':eval=frame`,
};

export function buildMaster(ffmpeg, outputDir) {
  return mix(ffmpeg, outputDir, { chapters: CHAPTERS, duration: DURATION, cues, slug: SLUG,
    music, signalAt: null, peakTarget: -3.7 });
}
