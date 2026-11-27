import { BEAT, BPM, CONTACTS, DURATION, FPS, FRAME_COUNT } from '../story.mjs';
export { BPM, CONTACTS, DURATION, FPS, FRAME_COUNT };

export const TITLE = 'XMETIX TAK710 · автоматический жгут';
export const SLUG = 'xmetix-tak710';
export const FILE = 'v_okope_xmetix_tak710.mp4';
export const WIPE = .14;
const beat = (n) => Math.round(n * BEAT * FPS) / FPS;
export const HERO_CUTS = [0, beat(4), beat(9)];
export const DETAIL_CUTS = [beat(15), beat(22), beat(27)];
export const AUTO_CUTS = [beat(30), beat(35), beat(40), beat(46)];
export const EXAMPLES = [
  { start: beat(52), label: 'В цехе', context: 'ПРОИЗВОДСТВО' },
  { start: beat(56), label: 'В дороге', context: 'АВТОМОБИЛЬ' },
  { start: beat(59), label: 'В походе', context: 'МАРШРУТ' },
];
export const RECAP = beat(65);
export const OUTRO = beat(72);
export const CUTS = [...HERO_CUTS, ...DETAIL_CUTS, ...AUTO_CUTS, ...EXAMPLES.map(({ start }) => start), RECAP, OUTRO];

export const CHAPTERS = [
  {
    start: 0, label: 'XMETIX TAK710', heading: ['Автоматический жгут'],
    narration: 'Иксметикс Так семьсот десять. Автоматический жгут.',
    voice: { file: 'tak-01-intro.mp3', offset: .07, tempo: 1.20 },
  },
  {
    start: DETAIL_CUTS[0], label: 'Кнопка, чека и ремень', heading: ['Устройство крупным планом'],
    narration: 'Одна кнопка на корпусе. Сбоку — защитная чека.',
    voice: { file: 'tak-02-design.mp3', offset: .13, tempo: 1.03 },
  },
  {
    start: AUTO_CUTS[0], label: 'Автоматическое натяжение', heading: ['Как устроен жгут'],
    narration: 'Натяжение ремня регулирует автоматика. Жгут предназначен для опасного кровотечения из руки или ноги.',
    voice: { file: 'tak-03-auto.mp3', offset: .15, tempo: 1.16 },
  },
  {
    start: EXAMPLES[0].start, label: 'Цех, дорога и поход', heading: ['Где может понадобиться первая помощь'],
    narration: 'В цехе. В дороге. В походе. Там, где важна первая помощь.',
    voice: { file: 'tak-04-context.mp3', offset: .12, tempo: 1.02 },
  },
  {
    start: OUTRO, label: 'Магазин и контакты', heading: ['Магазин «В Окопе»'],
    narration: 'Магазин «В окопе». Изучите инструкцию заранее.',
    voice: { file: 'tak-05-final.mp3', offset: .37, tempo: 1 },
  },
];

export function chapterAt(time) {
  return CHAPTERS.findLastIndex(({ start }) => time >= start);
}
