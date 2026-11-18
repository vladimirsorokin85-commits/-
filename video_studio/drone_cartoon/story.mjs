export const TITLE = 'Дрон над объектом';
export const DURATION = 24;
export const FPS = 30;
export const WIPE = 0.46;

export const CHAPTERS = [
  {
    start: 0,
    label: 'Вечер у «Маяка»',
    kicker: 'ВЕЧЕР У «МАЯКА»',
    heading: ['Дрон над', 'объектом.'],
    body: ['Обычный вечер. Над центром «Маяк»', 'появляется неизвестный дрон.'],
  },
  {
    start: 5.6,
    label: 'Заметить и сообщить',
    kicker: 'В ДЕЖУРНОЙ',
    heading: ['Заметить', 'и сообщить.'],
    body: ['Дежурная сообщает о дроне', 'ответственным за безопасность.'],
  },
  {
    start: 11.6,
    label: 'Какую роль играет РЭБ',
    kicker: 'КАКУЮ РОЛЬ ИГРАЕТ РЭБ',
    heading: ['РЭБ против', 'дронов.'],
    body: [
      'Радиоэлектронная борьба помогает',
      'противодействовать дронам.',
      'Её применяют уполномоченные службы.',
    ],
  },
  {
    start: 18.2,
    label: 'Магазин «В Окопе»',
    kicker: 'ПОСЛЕСЛОВИЕ',
    heading: ['Безопасность', 'начинается', 'с внимания.'],
    body: ['Магазин «В Окопе».'],
  },
];

export function chapterAt(time) {
  return CHAPTERS.findLastIndex(({ start }) => time >= start);
}
