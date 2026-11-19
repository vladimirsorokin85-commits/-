import { BPM } from '../story.mjs';
export { BPM };

export const MODEL = 'G.657.A2';
export const TITLE = `Оптоволокно ${MODEL} — намотка и маркировка`;
export const SLUG = 'fiber-g657a2';
export const FILE = 'v_okope_fiber_g657a2.mp4';
export const DURATION = 29;
export const FPS = 30;
export const FRAME_COUNT = DURATION * FPS;
export const WIPE = 8 / FPS;
export const CONTACTS = [];
export const DETAILS = Object.freeze({ diameter: '0,25 мм', fromCard: '50,4 км', fromLabel: '51,395 км' });

const beat = (n) => Math.round(n * 60 / BPM * FPS) / FPS;
const take = (name, tempo, offset) => ({ file: `fiber-${name}.mp3`, tempo, offset });
export const CHAPTERS = [
  { start: 0, label: 'Тип волокна', heading: ['Маркировка G657A2'],
    narration: 'Оптоволокно на катушке. G.657.A2 — обозначение категории одномодового волокна.',
    voice: take('01-type', 1.10, .47) },
  { start: beat(25), label: 'Диаметр и намотка', heading: ['Прозрачное волокно и намотка'],
    narration: 'По карточке, волокно прозрачное, диаметром в четверть миллиметра. Вот как выглядит намотка крупным планом.',
    voice: take('02-winding', 1.11, .32) },
  { start: beat(50), label: 'Что указано о длине', heading: ['Карточка и этикетка катушки'],
    narration: `В карточке — ${DETAILS.fromCard}. На этикетке этой катушки — ${DETAILS.fromLabel}.`,
    voice: take('03-length', 1.10, .33) },
];
export const SHOTS = [
  { start: 0, kind: 'hero' },
  { start: beat(9), kind: 'type' },
  { start: CHAPTERS[1].start, kind: 'diameter' },
  { start: beat(40), kind: 'winding' },
  { start: CHAPTERS[2].start, kind: 'listed' },
  { start: beat(64), kind: 'label' },
];
export function chapterAt(time) { return CHAPTERS.findLastIndex(({ start }) => time >= start); }
