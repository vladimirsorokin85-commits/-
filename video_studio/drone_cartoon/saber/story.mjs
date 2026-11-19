import { BPM } from '../story.mjs';
export { BPM };

export const MODEL = 'Wiley X Saber Advanced';
export const TITLE = `${MODEL} на складе — три сменные линзы`;
export const SLUG = 'wiley-x-saber-advanced';
export const FILE = 'v_okope_wiley_x_saber_advanced.mp4';
export const DURATION = 52;
export const FPS = 30;
export const FRAME_COUNT = DURATION * FPS;
export const WIPE = 8 / FPS;
export const CONTACTS = [];
export const PHOTOS = ['stack','black','case','box','tan','olive','label','group'];
export const FRAME_COLORS = ['Чёрная','Оливковая','Песочная'];
export const LENSES = Object.freeze({
  clear: { name: 'Clear', title: 'Прозрачная', note: 'Без сильного затемнения' },
  smoke: { name: 'Smoke Grey', title: 'Дымчато-серая', note: 'Для яркого света' },
  rust: { name: 'Light Rust', title: 'Оранжевая', note: 'Контраст при рассеянном свете' },
});
const beat = (n) => Math.round(n * 60 / BPM * FPS) / FPS;
const voice = (name, tempo, offset) => ({ file: `saber-${name}.mp3`, tempo, offset });
export const CHAPTERS = [
  { start: 0, label: 'Расцветки на складе', heading: ['Чёрная, оливковая и песочная оправы'],
    narration: 'На складе — защитные очки Wiley X Saber Advanced. Есть чёрная, оливковая и песочная оправа. Давайте разложим комплект и посмотрим на линзы.',
    voice: voice('01-stock', 1.12, .52) },
  { start: beat(35), label: 'Три сменные линзы', heading: ['Прозрачная, дымчато-серая и Light Rust'],
    narration: 'Вот три сменные линзы. Прозрачная — когда не нужно сильное затемнение. Дымчато-серая — для яркого света. А оранжевая, Light Rust, помогает различать детали при рассеянном свете.',
    voice: voice('02-lenses', 1.12, .31) },
  { start: beat(72), label: 'Посадка очков', heading: ['Дужки и носовой упор'],
    narration: 'Теперь о посадке. Широкая линза изогнута по бокам. Дужки выдвигаются, чтобы подобрать длину, а гибкий носовой упор можно подогнать под переносицу.',
    voice: voice('03-fit', 1.10, .31) },
  { start: beat(105), label: 'Ремешок и футляр', heading: ['Что лежит рядом с очками'],
    narration: 'Рядом с очками — эластичный ремешок и салфетка для линз. А вот чёрный футляр: молния по краю, сбоку небольшой карабин. И ещё раз — весь набор.',
    voice: voice('04-kit', 1.115, .32) },
];
export const PACKSHOT = Object.freeze({
  start: beat(138),
  lines: Object.freeze(['Не будь мишенью.', 'Будь «В окопе»']),
});
export const SHOTS = [
  { start: 0, kind: 'hero' },
  { start: beat(8), kind: 'stack' },
  { start: beat(15), kind: 'colors' },
  { start: beat(26), kind: 'box' },
  { start: CHAPTERS[1].start, kind: 'lenses' },
  { start: beat(42), kind: 'clear' },
  { start: beat(50), kind: 'smoke' },
  { start: beat(58), kind: 'rust' },
  { start: CHAPTERS[2].start, kind: 'profile' },
  { start: beat(86), kind: 'arm' },
  { start: beat(93), kind: 'nose' },
  { start: CHAPTERS[3].start, kind: 'extras' },
  { start: beat(118), kind: 'case' },
  { start: beat(126), kind: 'clasp' },
  { start: beat(132), kind: 'full' },
  { start: PACKSHOT.start, kind: 'packshot' },
];
export function chapterAt(time) { return CHAPTERS.findLastIndex(({ start }) => time >= start); }
