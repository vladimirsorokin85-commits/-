import { BPM } from '../story.mjs';
export { BPM };

export const MODEL = 'G.657.A2';
export const TITLE = `Оптоволокно ${MODEL} на складе`;
export const SLUG = 'fiber-g657a2';
export const FILE = 'v_okope_fiber_g657a2.mp4';
export const DURATION = 31;
export const FPS = 30;
export const FRAME_COUNT = DURATION * FPS;
export const WIPE = 8 / FPS;
export const CONTACTS = [];

const beat = (n) => Math.round(n * 60 / BPM * FPS) / FPS;
const take = (name, tempo, offset) => ({ file: `fiber-${name}.mp3`, tempo, offset });
export const CHAPTERS = [
  { start: 0, label: 'Что на складе', heading: ['Катушки в футлярах'],
    narration: 'Вот что у нас на складе: прозрачное оптоволокно на катушках. Чёрные катушки лежат в полупрозрачных футлярах с ручками.',
    voice: take('01-stock', 1.12, .42) },
  { start: beat(26), label: 'Намотка крупным планом', heading: ['Намотка крупным планом'],
    narration: 'В открытом футляре видно само волокно — светлую намотку под чёрной плёнкой. Посмотрим ближе: витки лежат плотно, один к одному.',
    voice: take('02-winding', 1.125, .32) },
  { start: beat(56), label: 'Маркировка на катушке', heading: ['Маркировка на катушке'],
    narration: 'На этикетке — G657A2. Вот так оптоволокно выглядит в упаковке.',
    voice: take('03-marking', 1.11, .33) },
];
export const PACKSHOT = Object.freeze({
  start: beat(79),
  lines: Object.freeze(['Не будь мишенью.', 'Будь «В окопе»']),
});
export const SHOTS = [
  { start: 0, kind: 'hero' },
  { start: beat(14), kind: 'packed' },
  { start: CHAPTERS[1].start, kind: 'open' },
  { start: beat(43), kind: 'winding' },
  { start: CHAPTERS[2].start, kind: 'mark' },
  { start: beat(69), kind: 'end' },
  { start: PACKSHOT.start, kind: 'packshot' },
];
export function chapterAt(time) { return CHAPTERS.findLastIndex(({ start }) => time >= start); }
