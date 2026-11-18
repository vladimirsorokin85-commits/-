export const TITLE = 'В своём ритме';
export const SLUG = 'v-svoem-ritme';
export const FILE = 'v_okope_v_svoem_ritme.mp4';
export const FPS = 30;
export const FRAME_COUNT = 900;
export const DURATION = FRAME_COUNT / FPS;
export const BPM = 170;
export const BEAT = 60 / BPM;
export const WIPE = 0.46;
export const ALERT_AT = 36 / FPS;
export const CAT_AT = 91 / FPS;

const onBeat = (n) => Math.round(n * BEAT * FPS) / FPS;

export const CONTACTS = [
  { label: 'Telegram', handle: '@vokope_ru', href: 'https://t.me/vokope_ru' },
  { label: 'ВКонтакте', handle: '@vokope_rus', href: 'https://vk.com/vokope_rus' },
  { label: 'Авито', handle: '«В Окопе»', href: 'https://www.avito.ru/brands/5d48ea870de5a9f3ca08a6024efbe241' },
];

export const CHAPTERS = [
  {
    start: 0,
    label: 'Дрон на подлёте',
    kicker: 'ПРОМЗОНА / РАБОЧИЙ ДЕНЬ',
    heading: ['Дрон на', 'подлёте.'],
    body: ['В небе появляется', 'неизвестный дрон.'],
    narration: 'Обычный день на заводе. На подлёте — неизвестный дрон.',
    voice: { file: '01-podlet.mp3', offset: .45, tempo: 1.03 },
  },
  {
    start: onBeat(16),
    label: 'Автоматическое оповещение',
    kicker: 'НА ПОДЛЁТЕ / АВТОМАТИЧЕСКИ',
    heading: ['Дрон', 'замечен.'],
    body: ['Детектор автоматически уведомляет', 'ответственного за безопасность.'],
    narration: 'Детектор замечает дрон на подлёте. Уведомление автоматически приходит ответственному за безопасность.',
    voice: { file: '02-signal.mp3', offset: .48, tempo: 1.05 },
  },
  {
    start: onBeat(36),
    label: 'Цех в своём ритме',
    kicker: 'ЦЕХ / РАБОЧИЙ РИТМ',
    heading: ['Работа', 'идёт.'],
    body: ['В цехе день идёт', 'своим чередом.'],
    narration: 'А в цехе день идёт своим чередом.',
    voice: { file: '03-ritm.mp3', offset: .55, tempo: 1.02 },
  },
  {
    start: onBeat(56),
    label: 'Кто не заметил?',
    kicker: 'ПОСЛЕСЛОВИЕ / ЗА КАДРОМ',
    heading: ['Кот не', 'заметил.'],
    body: ['У него обед по расписанию.'],
    narration: 'Кто ничего не заметил? Кот. У него обед по расписанию.',
    voice: { file: '04-kot.mp3', offset: .5, tempo: 1 },
  },
  {
    start: onBeat(72),
    label: 'Магазин «В Окопе» и контакты',
    kicker: 'В ОКОПЕ / КОНТАКТЫ',
    heading: ['Знать', 'вовремя.'],
    body: ['Магазин «В Окопе». Автоматическое оповещение о дронах.'],
    narration: 'Магазин «В Окопе». Автоматическое оповещение о дронах.',
    voice: { file: '05-kontakty.mp3', offset: .48, tempo: 1.03 },
  },
];

export function chapterAt(time) {
  return CHAPTERS.findLastIndex(({ start }) => time >= start);
}
