import { BPM } from '../story.mjs';
export { BPM };

export const MODEL = 'Prabos Vagabund Ankle Field';
export const TITLE = `${MODEL} — между кроссовками и сапогами`;
export const SLUG = 'prabos-vagabund-ankle';
export const FILE = 'v_okope_prabos_vagabund_ankle.mp4';
export const DURATION = 51;
export const FPS = 30;
export const FRAME_COUNT = DURATION * FPS;
export const WIPE = 8 / FPS;
export const CONTACTS = [];
export const PHOTOS = ['pair', 'angle', 'profile'];
export const HEIGHT_LABEL = '14,5 см';
export const WEIGHT_LABEL = '620 г';
export const WEIGHT_NOTE = 'Один ботинок · 42-й размер';
const beat = n => Math.round(n * 60 / BPM * FPS) / FPS;
const voice = (name, tempo, offset) => ({ file: `vagabund-${name}.mp3`, tempo, offset });
export const CHAPTERS = [
  { start: 0, label: 'Между кроссовками и сапогами', heading: ['Высота 14,5 см'],
    narration: 'На складе — ботинки Prabos Vagabund Ankle Field. Между кроссовками и сапогами. Высота — четырнадцать с половиной сантиметров: щиколотка закрыта, голень остаётся свободной.',
    voice: voice('01-height', 1.14, .52) },
  { start: beat(39), label: 'Шнуровка и подкладка', heading: ['Текстильные петли, крючки и DRI-LEX'],
    narration: 'Смотрите на шнуровку: внизу текстильные петли, сверху металлические крючки. Внутри — подкладка DRI-LEX. Мембраны здесь нет.',
    voice: voice('02-upper', 1.14, .32) },
  { start: beat(69), label: 'Подошва и вставка', heading: ['PHOBOS и кевларовая вставка'],
    narration: 'Теперь подошва PHOBOS двойной плотности. Полиуретан и резина. Внутри — кевларовая вставка: она помогает защитить стопу от проколов снизу. Но это не броня.',
    voice: voice('03-sole', 1.145, .34) },
  { start: beat(104), label: 'На каждый день', heading: ['Город, выезды и вес одного ботинка'],
    narration: 'Такая пара — на каждый день в городе и для выездов без глубокой грязи. В сорок втором размере один ботинок весит шестьсот двадцать граммов. Пара есть в наличии.',
    voice: voice('04-stock', 1.14, .33) },
];
export const PACKSHOT = Object.freeze({
  start: beat(135),
  lines: Object.freeze(['Не будь мишенью.', 'Будь «В окопе»']),
});
export const SHOTS = [
  { start: 0, kind: 'hero' },
  { start: beat(13), kind: 'side' },
  { start: beat(20), kind: 'height' },
  { start: beat(30), kind: 'ankle' },
  { start: CHAPTERS[1].start, kind: 'laces' },
  { start: beat(50), kind: 'hooks' },
  { start: beat(57), kind: 'lining' },
  { start: CHAPTERS[2].start, kind: 'sole' },
  { start: beat(79), kind: 'materials' },
  { start: beat(85), kind: 'insert' },
  { start: beat(98), kind: 'limits' },
  { start: CHAPTERS[3].start, kind: 'days' },
  { start: beat(119), kind: 'weight' },
  { start: beat(130), kind: 'stock' },
  { start: PACKSHOT.start, kind: 'packshot' },
];
export function chapterAt(time) { return CHAPTERS.findLastIndex(({ start }) => time >= start); }
