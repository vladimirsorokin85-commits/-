import { buildMaster as mix, STORM_RIDERS } from '../mix.mjs';
import { CHAPTERS, DURATION, PACKSHOT, SHOTS, SLUG } from './story.mjs';

const major = new Set(CHAPTERS.map(({ start }) => start));
const cues = SHOTS.slice(1).map(({ start, kind }) => kind === 'packshot'
  ? [start, 'text_reveal_soft', .30]
  : major.has(start) ? [start, 'swipe_paper', .29] : [start, 'cut_tick', .19]);

const riseAt = (PACKSHOT.start - .10).toFixed(3);
const music = {
  ...STORM_RIDERS,
  bedFilter: `${STORM_RIDERS.bedFilter},` +
    `volume='if(isnan(t),1,1+1.06*clip((t-${riseAt})/.42,0,1))':eval=frame`,
};

export function buildMaster(ffmpeg, outputDir) {
  return mix(ffmpeg, outputDir, { chapters: CHAPTERS, duration: DURATION, cues, slug: SLUG,
    music, signalAt: null, peakTarget: -3.25 });
}
