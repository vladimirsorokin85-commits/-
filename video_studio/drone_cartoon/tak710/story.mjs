import { CONTACTS, DURATION, FPS, FRAME_COUNT } from '../story.mjs';
export { CONTACTS, DURATION, FPS, FRAME_COUNT };

export const TITLE = 'XMETIX TAK710 · автоматический жгут';
export const SLUG = 'xmetix-tak710';
export const FILE = 'v_okope_xmetix_tak710.mp4';
// Grid of the downloaded Final Hour excerpt. Cuts round to a whole frame.
export const BPM = 170;
export const WIPE = .21;
const BEAT = 60 / BPM;
const beat = (n) => Math.round(n * BEAT * FPS) / FPS;
export const DESIGN_CUT = beat(26);
export const KIT_CUT = beat(46);

export const CHAPTERS = [
  {
    start: 0, label: 'Что такое XMETIX TAK710', heading: ['Автоматический жгут'],
    narration: 'Иксметикс Так семьсот десять. Автоматический кровоостанавливающий жгут.',
    voice: { file: 'tak-01-intro.mp3', offset: .22, tempo: 1.015 },
  },
  {
    start: beat(20), label: 'Ремень, экран и автоматика', heading: ['Ремень и экран'],
    narration: 'На корпусе — экран. Натяжение ремня регулируется автоматически.',
    voice: { file: 'tak-02-design.mp3', offset: .20, tempo: 1 },
  },
  {
    start: beat(37), label: 'Назначение жгута', heading: ['Первая помощь'],
    narration: 'Жгут — средство первой помощи при опасном кровотечении из руки или ноги.',
    voice: { file: 'tak-03-purpose.mp3', offset: .22, tempo: 1 },
  },
  {
    start: beat(56), label: 'Экстренная помощь: 112', heading: ['Вызов помощи'],
    narration: 'Звоните сто двенадцать. Следуйте указаниям диспетчера.',
    voice: { file: 'tak-04-help.mp3', offset: .25, tempo: 1.04 },
  },
  {
    start: beat(70), label: 'Магазин и контакты', heading: ['Магазин «В Окопе»'],
    narration: 'Магазин «В окопе». Изучите инструкцию заранее.',
    voice: { file: 'tak-05-final.mp3', offset: .43, tempo: 1 },
  },
];

export function chapterAt(time) {
  return CHAPTERS.findLastIndex(({ start }) => time >= start);
}
