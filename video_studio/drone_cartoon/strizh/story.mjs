export const TITLE = '«Стриж» — визуальный обзор';
export const SLUG = 'strizh';
export const FILE = 'v_okope_strizh_obzor.mp4';
export const DURATION = 60;
export const FPS = 30;
export const FRAME_COUNT = DURATION * FPS;
export const BPM = 170;
export const WIPE = .16;
export const CONTACTS = [];
const beat = (n) => Math.round(n * 60 / BPM * FPS) / FPS;

export const VIEWS = [
  { id: 1, name: 'В три четверти', title: ['В три', 'четверти.'], note: 'Оливковый оттенок и общий силуэт' },
  { id: 4, name: 'Прямой ракурс', title: ['Прямой', 'ракурс.'], note: 'Корпус в центре кадра' },
  { id: 16, name: 'По диагонали', title: ['По', 'диагонали.'], note: 'Свет и форма с другой стороны' },
];
export const CHAPTERS = [
  {
    start: 0, label: '«Стриж»', heading: ['Внешний вид'],
    narration: 'Это «Стриж», дрон-перехватчик. В этом обзоре посмотрим на его внешний вид: три фотографии с разных ракурсов.',
    voice: { file: 'strizh-01-intro.mp3', offset: .28, tempo: 1.02 },
  },
  {
    start: beat(28), label: VIEWS[0].name, heading: ['В три четверти'],
    narration: 'Первый снимок — в три четверти. На нём виден весь аппарат: вытянутый силуэт и оливковый цвет корпуса. Фотография показывает объём лучше, чем плоский рисунок.',
    voice: { file: 'strizh-02-angle.mp3', offset: .26, tempo: 1.085 },
  },
  {
    start: beat(60), label: VIEWS[1].name, heading: ['Прямой ракурс'],
    narration: 'Второй снимок — прямой ракурс. Корпус в центре кадра, а элементы по обе стороны почти симметричны. Здесь лучше всего читается его общий контур.',
    voice: { file: 'strizh-03-contour.mp3', offset: .26, tempo: 1.025 },
  },
  {
    start: beat(92), label: VIEWS[2].name, heading: ['По диагонали'],
    narration: 'На третьем снимке аппарат расположен по диагонали. Под этим углом свет иначе ложится на грани корпуса, и хорошо видна его форма.',
    voice: { file: 'strizh-04-diagonal.mp3', offset: .26, tempo: 1.015 },
  },
  {
    start: beat(125), label: 'Три ракурса рядом', heading: ['Фото и рисунок'],
    narration: 'Теперь все три ракурса рядом. Рисованные перебивки выделяют общий силуэт, а фотографии дают сравнить форму и цвет корпуса.',
    voice: { file: 'strizh-05-gallery.mp3', offset: .26, tempo: 1.015 },
  },
  {
    start: beat(154), label: 'Финальный кадр', heading: ['«Стриж»'],
    narration: 'Это был визуальный обзор «Стрижа».',
    voice: { file: 'strizh-06-end.mp3', offset: .23, tempo: 1 },
  },
];
export const SHOTS = [
  { start: 0, kind: 'hero' },
  { start: beat(7), kind: 'hero', view: 2 },
  { start: beat(19), kind: 'diptych', left: 2 },
  { start: CHAPTERS[1].start, kind: 'angle', view: 0 },
  { start: beat(44), kind: 'folio', view: 0 },
  { start: CHAPTERS[2].start, kind: 'angle', view: 1 },
  { start: beat(76), kind: 'print', view: 1 },
  { start: CHAPTERS[3].start, kind: 'angle', view: 2 },
  { start: beat(109), kind: 'folio', view: 2 },
  { start: CHAPTERS[4].start, kind: 'gallery' },
  { start: beat(139), kind: 'diptych', left: 0 },
  { start: CHAPTERS[5].start, kind: 'end' },
];
export function chapterAt(time) {
  return CHAPTERS.findLastIndex(({ start }) => time >= start);
}
