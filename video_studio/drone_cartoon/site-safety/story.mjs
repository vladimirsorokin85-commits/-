export const TITLE = 'Дрон над объектом: памятка';
export const SLUG = 'bezopasnost-na-obekte';
export const FILE = 'v_okope_bezopasnost_na_obekte.mp4';
export const DURATION = 60;
export const FPS = 30;
export const FRAME_COUNT = DURATION * FPS;
export const BPM = 170;
export const WIPE = .16;
export const CONTACTS = [];
const beat = (n) => Math.round(n * 60 / BPM * FPS) / FPS;

export const CHAPTERS = [
  {
    start: 0, label: 'Обычная смена', heading: ['Если замечен дрон'],
    narration: 'Обычная смена на предприятии. Если рядом замечен незнакомый беспилотник, важно заранее знать порядок действий.',
    voice: { file: 'site-01-intro.mp3', offset: .24, tempo: 1.01 },
  },
  {
    start: beat(27), label: 'Фотографии «Стрижа»', heading: ['Фото, не испытания'],
    narration: 'На фотографиях — «Стриж». Это общий вид устройства, а не запись испытаний. По таким кадрам нельзя судить о его работе.',
    voice: { file: 'site-02-photo.mp3', offset: .25, tempo: 1.03 },
  },
  {
    start: beat(55), label: 'Кому сообщить', heading: ['Сообщите ответственному'],
    narration: 'На предприятии важно знать, кому сообщать о наблюдении. Сделайте это из безопасного места и следуйте указаниям ответственного.',
    voice: { file: 'site-03-report.mp3', offset: .27, tempo: 1.01 },
  },
  {
    start: beat(87), label: 'План объекта', heading: ['Следуйте плану'],
    narration: 'Не выходите на открытую площадку ради съёмки. Услышав оповещение, действуйте по плану объекта и указаниям служб.',
    voice: { file: 'site-04-plan.mp3', offset: .22, tempo: 1.01 },
  },
  {
    start: beat(118), label: 'Если найдены обломки', heading: ['Держите дистанцию'],
    narration: 'Если видите упавший аппарат или обломки, не подходите и не трогайте их. Из безопасного места сообщите экстренным службам.',
    voice: { file: 'site-05-debris.mp3', offset: .25, tempo: 1.01 },
  },
  {
    start: beat(150), label: 'Три правила', heading: ['Дистанция. Сообщение. План.'],
    narration: 'Держите дистанцию. Сообщите ответственному. Действуйте по плану объекта.',
    voice: { file: 'site-06-final.mp3', offset: .28, tempo: 1.015 },
  },
];

export const SHOTS = [
  { start: 0, kind: 'yard' },
  { start: beat(10), kind: 'warehouse' },
  { start: beat(22), kind: 'aisle' },
  { start: CHAPTERS[1].start, kind: 'archive', photo: 16 },
  { start: beat(41), kind: 'archive', photo: 4 },
  { start: CHAPTERS[2].start, kind: 'landscape' },
  { start: beat(63), kind: 'report' },
  { start: beat(77), kind: 'report', close: true },
  { start: CHAPTERS[3].start, kind: 'camera' },
  { start: beat(100), kind: 'plan' },
  { start: beat(110), kind: 'plan', close: true },
  { start: CHAPTERS[4].start, kind: 'distance' },
  { start: beat(132), kind: 'help' },
  { start: CHAPTERS[5].start, kind: 'final' },
];

export function chapterAt(time) {
  return CHAPTERS.findLastIndex(({ start }) => time >= start);
}
