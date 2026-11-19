import { BPM } from '../story.mjs';
export { BPM };
export const TITLE = 'RunCam Helmet Camera 2 — камера на шлем с записью Full HD';
export const SLUG = 'runcam-helmet-2';
export const FILE = 'v_okope_runcam_helmet_camera_2.mp4';
export const DURATION = 47;
export const FPS = 30;
export const FRAME_COUNT = DURATION * FPS;
export const WIPE = .14;
export const CONTACTS = [];
export const PHOTOS = ['box', 'controls', 'base', 'power', 'kit-top', 'lens', 'camera', 'open-box', 'kit-angle'];
// RunCam user manual, §06. Runtime is a manufacturer figure with this battery, not a test of the supplied batch.
export const SPECS = Object.freeze({ width: 1920, height: 1080, fps: 60, aperture: '1.6', battery: '18650', runtime: 8, referenceCapacity: 3500, wifiGHz: 5 });
const beat = (n) => Math.round(n * 60 / BPM * FPS) / FPS;
const voice = (name, tempo, offset = .18) => ({ file: `runcam-${name}.mp3`, tempo, offset });
export const CHAPTERS = [
  { start: 0, label: 'Объектив и угол съёмки', heading: ['Гибкая трубка объектива'],
    narration: 'RunCam Helmet Camera 2. Объектив вынесен на гибкую трубку. Угол съёмки можно менять, не переставляя корпус.',
    voice: voice('01-angle', 1.10, .23) },
  { start: beat(25), label: 'Запись и корпус', heading: ['Full HD, f/1.6 и защита корпуса'],
    narration: 'Full HD, до 60 кадров в секунду. Диафрагма f/1.6. Корпус защищён от пыли и брызг.',
    voice: voice('02-video', 1.125) },
  { start: beat(51), label: 'Аккумулятор 18650', heading: ['Питание и время записи'],
    narration: 'Питание от сменного аккумулятора формата 18650. Около восьми часов записи — по данным RunCam при 1080p60 для аккумулятора на 3 500 мА·ч.',
    voice: voice('03-battery', 1.11) },
  { start: beat(82), label: 'Запуск и Wi-Fi', heading: ['Автостарт и предпросмотр'],
    narration: 'После включения запись стартует автоматически, с вибросигналом. Через приложение RunCam можно проверить кадр по Wi-Fi.',
    voice: voice('04-app', 1.09) },
  { start: beat(108), label: 'Что в коробке', heading: ['Комплект на фотографиях'],
    narration: 'На фото комплекта — крепления, липучки и зарядный кабель. Так можно снимать от первого лица, оставляя руки свободными.',
    voice: voice('05-kit', 1.08) },
];
export const SHOTS = [
  { start: 0, kind: 'hero' },
  { start: beat(9), kind: 'lens' },
  { start: beat(17), kind: 'angle' },
  { start: CHAPTERS[1].start, kind: 'video' },
  { start: beat(34), kind: 'aperture' },
  { start: beat(42), kind: 'shell' },
  { start: CHAPTERS[2].start, kind: 'battery' },
  { start: beat(63), kind: 'runtime' },
  { start: CHAPTERS[3].start, kind: 'controls' },
  { start: beat(95), kind: 'app' },
  { start: CHAPTERS[4].start, kind: 'kit' },
  { start: beat(117), kind: 'unbox' },
  { start: beat(127), kind: 'end' },
];
export function chapterAt(time) { return CHAPTERS.findLastIndex(({ start }) => time >= start); }
