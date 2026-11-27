import { BPM } from '../story.mjs';
export { BPM };
export const TITLE = 'GONGTEX Reversible Jacket — мультикам и койот в одной куртке';
export const SLUG = 'gongtex-reversible';
export const FILE = 'v_okope_gongtex_reversible_jacket.mp4';
export const DURATION = 36;
export const FPS = 30;
export const FRAME_COUNT = DURATION * FPS;
export const WIPE = .15;
export const CONTACTS = [];
const beat = (n) => Math.round(n * 60 / BPM * FPS) / FPS;

export const SPECS = {
  polyester: 96, spandex: 4, shell: 110, insulation: 120,
  insulationBrand: 'DuPont', zipper: 'SBS', season: 'Демисезон и зима',
};
export const PHOTOS = ['camo-front', 'camo-collar', 'coyote-detail', 'camo-pocket', 'coyote-back', 'coyote-side', 'camo-side', 'coyote-front'];
const vo = (file, tempo, offset = .17) => ({ file: `gongtex-${file}.mp3`, tempo, offset });
export const CHAPTERS = [
  { start: 0, label: 'Две стороны', heading: ['Мультикам и койот'],
    narration: 'GONGTEX Reversible — мужская двусторонняя куртка. С одной стороны мультикам, с другой — койот.',
    voice: vo('01-sides', 1.025, .22) },
  { start: beat(24), label: 'Ткань и утеплитель', heading: ['Состав и плотность'],
    narration: 'Верх куртки — полиэстер со спандексом. Внутри утеплитель DuPont — 120 граммов на квадратный метр.',
    voice: vo('02-material', 1.025) },
  { start: beat(47), label: 'Молния, воротник, карман', heading: ['Детали куртки'],
    narration: 'Центральная молния SBS, воротник на липучке и боковой карман на молнии.',
    voice: vo('03-details', 1.035) },
  { start: beat(65), label: 'Посадка', heading: ['Манжеты и утяжка'],
    narration: 'Эластичные манжеты облегают запястья, а шнурок по низу позволяет отрегулировать посадку.',
    voice: vo('04-fit', 1.06) },
  { start: beat(85), label: 'Демисезон и зима', heading: ['Сезон'],
    narration: 'Демисезон и зима. GONGTEX Reversible — две стороны одной куртки.',
    voice: vo('05-end', 1.04) },
];
export const SHOTS = [
  { start: 0, kind: 'opener' },
  { start: beat(8), kind: 'colour', side: 0 },
  { start: beat(16), kind: 'colour', side: 1 },
  { start: CHAPTERS[1].start, kind: 'shell' },
  { start: beat(34), kind: 'insulation' },
  { start: beat(41), kind: 'insulation', photo: true },
  { start: CHAPTERS[2].start, kind: 'zip' },
  { start: beat(56), kind: 'details' },
  { start: CHAPTERS[3].start, kind: 'cuff' },
  { start: beat(74), kind: 'hem' },
  { start: CHAPTERS[4].start, kind: 'season' },
  { start: beat(93), kind: 'end' },
];
export function chapterAt(time) { return CHAPTERS.findLastIndex(({ start }) => time >= start); }
