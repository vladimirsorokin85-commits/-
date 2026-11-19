import { BPM } from '../story.mjs';
export { BPM };

export const MODEL = 'Инкубатор 3.30';
export const TITLE = `«${MODEL}» — короткий обзор усилителя сигнала`;
export const SLUG = 'incubator-330';
export const FILE = 'v_okope_incubator_330.mp4';
export const FPS = 30;
export const DURATION = 28;
export const FRAME_COUNT = DURATION * FPS;
export const WIPE = 8 / FPS;
export const CONTACTS = [];
// Physical characteristics from the owner's product card, not our measurements.
export const PHYSICAL = Object.freeze({ size: '330 × 300 × 70 мм', mass: '4,05 кг' });

const beat = (n) => Math.round(n * 60 / BPM * FPS) / FPS;
const voice = (name, tempo, offset) => ({ file: `incubator-${name}.mp3`, tempo, offset });
export const CHAPTERS = [
  { start: 0, label: 'Назначение', heading: ['Усилитель сигнала'],
    narration: '«Инкубатор 3.30» — антенно-усилительный блок. Его задача — усиливать радиосигнал.',
    voice: voice('01-purpose', 1.09, .53) },
  { start: beat(25), label: 'Корпус и габариты', heading: ['Корпус и габариты'],
    narration: 'По карточке изделия, корпус из анодированного алюминия, кожух пластиковый. Блок весит чуть больше четырёх килограммов.',
    voice: voice('02-body', 1.11, .32) },
  { start: beat(52), label: 'Кейс и техпаспорт', heading: ['Кейс и техпаспорт'],
    narration: 'Для перевозки предусмотрен кейс с ложементом. На фото — маркировка ящика номер один и обложка технического паспорта.',
    voice: voice('03-case', 1.09, .31) },
];
export const SHOTS = [
  { start: 0, kind: 'hero' },
  { start: beat(14), kind: 'purpose' },
  { start: CHAPTERS[1].start, kind: 'materials' },
  { start: beat(42), kind: 'dimensions' },
  { start: CHAPTERS[2].start, kind: 'case' },
  { start: beat(59), kind: 'tray' },
  { start: beat(63), kind: 'mark' },
  { start: beat(71), kind: 'passport' },
];
export function chapterAt(time) { return CHAPTERS.findLastIndex(({ start }) => time >= start); }
