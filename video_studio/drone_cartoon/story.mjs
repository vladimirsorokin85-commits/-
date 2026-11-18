export const TITLE = 'Знать вовремя';
export const SLUG = 'znat-vovremya';
export const FPS = 30;
export const FRAME_COUNT = 900;
export const DURATION = FRAME_COUNT / FPS;
export const WIPE = 0.46;
export const ALERT_AT = 76 / FPS;

export const CHAPTERS = [
  {
    start: 0,
    label: 'Обычный день на заводе',
    kicker: 'ПРОИЗВОДСТВО / РАБОЧИЙ ДЕНЬ',
    heading: ['Дрон над', 'заводом.'],
    body: ['В небе появляется', 'неизвестный дрон.'],
    narration: 'Обычный день на заводе. В небе появляется неизвестный дрон.',
    voice: { file: '01-zavod.mp3', offset: .38, tempo: 1.06 },
  },
  {
    start: 5,
    label: 'Время важно',
    kicker: 'КОГДА ВАЖНА КАЖДАЯ МИНУТА',
    heading: ['Время', 'важно.'],
    body: ['Ответственному за безопасность', 'важно узнать об этом как можно раньше.'],
    narration: 'Ответственному за безопасность важно узнать об этом как можно раньше.',
    voice: { file: '02-vremya.mp3', offset: .48, tempo: 1.10 },
  },
  {
    start: 10,
    label: 'Уведомление о дроне',
    kicker: 'АВТОМАТИЧЕСКОЕ ОПОВЕЩЕНИЕ',
    heading: ['Дрон', 'замечен.'],
    body: ['Когда детектор замечает дрон,', 'ответственный за безопасность', 'получает уведомление.'],
    narration: 'Когда детектор замечает дрон, он отправляет уведомление ответственному за безопасность. Теперь можно оценить ситуацию.',
    voice: { file: '03-detektor.mp3', offset: .5, tempo: 1.10 },
  },
  {
    start: 18,
    label: 'Офис, склад и производство',
    kicker: 'ТРИ РАБОЧИЕ ПЛОЩАДКИ',
    heading: ['Офис, склад,', 'производство.'],
    body: ['Где бы ни работала команда,', 'важно вовремя узнать о дроне.'],
    narration: 'Офис, склад или производство. Где бы ни работала команда, важно вовремя узнать о дроне.',
    voice: { file: '04-obekty.mp3', offset: .47, tempo: 1.05 },
  },
  {
    start: 25,
    label: 'Магазин «В Окопе»',
    kicker: 'В ОКОПЕ / ФИНАЛ',
    heading: ['Важно знать', 'вовремя.'],
    body: ['Магазин «В Окопе». Автоматические детекторы дронов.'],
    narration: 'Важно знать вовремя. Автоматические детекторы дронов. Магазин «В Окопе».',
    voice: { file: '04-final.mp3', offset: .42, tempo: 1.12 },
  },
];

export function chapterAt(time) {
  return CHAPTERS.findLastIndex(({ start }) => time >= start);
}
