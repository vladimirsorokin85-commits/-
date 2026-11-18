export const TITLE = 'В своём ритме';
export const SLUG = 'v-svoem-ritme-montazh';
export const FILE = 'v_okope_v_svoem_ritme_montazh.mp4';
export const FPS = 30;
export const FRAME_COUNT = 900;
export const DURATION = FRAME_COUNT / FPS;
// Montage grid from measured drum transients, not the catalog tempo tag.
export const BPM = 174.05;
export const BEAT = 60 / BPM;
export const WIPE = 0.38;

const onBeat = (n) => Math.round(n * BEAT * FPS) / FPS;
export const BEEP_AT = onBeat(7);
export const CAT_AT = onBeat(10);
export const WORK_CUTS = Array.from({ length: 8 }, (_, i) => onBeat(24 + i * 4) - onBeat(24));

export const CONTACTS = [
  { label: 'Telegram', handle: '@vokope_ru', href: 'https://t.me/vokope_ru' },
  { label: 'ВКонтакте', handle: '@vokope_rus', href: 'https://vk.com/vokope_rus' },
  { label: 'Авито', handle: '«В Окопе»', href: 'https://www.avito.ru/brands/5d48ea870de5a9f3ca08a6024efbe241' },
];

const slogan = ['Не будь мишенью.', 'Будь «В окопе»!'];

export const CHAPTERS = [
  {
    start: 0,
    label: 'Дрон на подлёте',
    kicker: 'ПРОМЗОНА / РАБОЧИЙ ДЕНЬ',
    heading: ['Дрон на', 'подлёте.'],
    body: ['Важно заметить его вовремя.'],
    narration: 'Дрон на подлёте к заводу. Важно заметить его вовремя.',
    voice: { file: 'r4-01-podlet.mp3', offset: .28, tempo: 1.06 },
  },
  {
    start: onBeat(12),
    label: 'Звуковой сигнал',
    kicker: 'ДЕТЕКТОР / ЗВУКОВОЙ СИГНАЛ',
    heading: ['Дрон', 'замечен.'],
    body: ['Детектор подаёт короткий', 'звуковой сигнал.'],
    narration: 'Детектор замечает дрон. Звучит короткий сигнал.',
    voice: { file: 'r4-02-signal.mp3', offset: .29, tempo: 1.05 },
  },
  {
    start: onBeat(24),
    label: 'Монтаж цеха в ритме музыки',
    kicker: 'ЦЕХ / РАБОЧИЙ РИТМ',
    heading: ['Работа', 'идёт.'],
    body: ['У каждого своя работа.', 'День идёт своим чередом.'],
    narration: 'В офисе, на складе, в цехе — у каждого своя работа. День идёт своим чередом.',
    voice: { file: 'r4-03-ritm.mp3', offset: .55, tempo: 1.02 },
  },
  {
    start: onBeat(56),
    label: 'Даже заводской кот',
    kicker: 'ПОСЛЕСЛОВИЕ / ЗА КАДРОМ',
    heading: ['Кот не', 'заметил.'],
    body: ['Даже заводской кот ничего не заметил.', 'У него по расписанию обед.'],
    narration: 'Даже заводской кот ничего не заметил. У него по расписанию обед.',
    voice: { file: 'r4-04-kot.mp3', offset: .48, tempo: 1.02 },
  },
  {
    start: onBeat(72),
    label: 'Магазин «В Окопе» и контакты',
    kicker: 'В ОКОПЕ / КОНТАКТЫ',
    heading: slogan,
    body: ['Магазин «В Окопе». Детекторы дронов.'],
    narration: slogan.join(' '),
    voice: { file: 'r4-05-final.mp3', offset: .48, tempo: 1 },
  },
];

export function chapterAt(time) {
  return CHAPTERS.findLastIndex(({ start }) => time >= start);
}
