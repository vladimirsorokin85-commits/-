import { BEAT, CONTACTS, DURATION, FPS, FRAME_COUNT } from '../story.mjs';
export { CONTACTS, DURATION, FPS, FRAME_COUNT };

export const TITLE = 'Булат v4 · дрон-детектор';
export const SLUG = 'bulat-v4-detektor';
export const FILE = 'v_okope_bulat_v4_detektor.mp4';
export const WIPE = .32;
export const SLOGAN = 'Не будь мишенью. Будь «В окопе»!';

const beat = (n) => Math.round(n * BEAT * FPS) / FPS;
export const BEEP_AT = beat(27);
export const SITES = [
  { start: beat(48), name: 'Склад', shorter: 'СКЛАД', setting: 'Логистическая площадка' },
  { start: beat(51), name: 'Стройплощадка', shorter: 'СТРОЙКА', setting: 'Гражданское строительство' },
  { start: beat(55), name: 'Выездная бригада', shorter: 'БРИГАДА', setting: 'Работы на выезде' },
];

export const CHAPTERS = [
  {
    start: 0, label: 'Что такое «Булат v4»', heading: ['Булат v4'],
    narration: 'Это Булат четвёртой версии. Переносной детектор дронов.',
    voice: { file: 'bulat-01-intro.mp3', offset: .23, tempo: 1.02 },
  },
  {
    start: beat(16), label: 'Как он предупреждает', heading: ['Звуковой сигнал'],
    narration: 'При обнаружении детектор подаёт короткий звуковой сигнал. Он предупреждает, а не глушит связь.',
    voice: { file: 'bulat-02-cue.mp3', offset: .18, tempo: 1.102 },
  },
  {
    start: beat(36), label: 'Зачем гражданским', heading: ['Гражданские задачи'],
    narration: 'Такое предупреждение полезно и в гражданской работе: на складе, на стройплощадке или у выездной бригады.',
    voice: { file: 'bulat-03-civil.mp3', offset: .18, tempo: 1 },
  },
  {
    start: beat(62), label: 'Заметить дрон вовремя', heading: ['Заметить вовремя.'],
    narration: 'Главное — вовремя заметить дрон.',
    voice: { file: 'bulat-04-outro.mp3', offset: .18, tempo: 1 },
  },
  {
    start: beat(72), label: 'Логотип, слоган и контакты', heading: ['Магазин «В Окопе»'],
    narration: SLOGAN,
    voice: { file: 'r4-05-final.mp3', offset: .47, tempo: 1 },
  },
];

export function chapterAt(time) {
  return CHAPTERS.findLastIndex(({ start }) => time >= start);
}
