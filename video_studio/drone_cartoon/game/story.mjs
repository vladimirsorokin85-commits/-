import { CONTACTS, DURATION, FPS, FRAME_COUNT } from '../story.mjs';
export { CONTACTS, DURATION, FPS, FRAME_COUNT };

export const TITLE = 'Game Over для дрона';
export const SLUG = 'game-over-dlya-drona';
export const FILE = 'v_okope_game_over.mp4';
export const WIPE = 0.32;
export const BEEP_AT = 200 / FPS;
export const GAME_OVER_AT = 317 / FPS;
export const SLOGAN = 'Не будь мишенью. Будь «В окопе»!';

const sites = [
  { name: 'Склад', map: 'СКЛАД', id: '01' },
  { name: 'Спецтехника', map: 'ПЛОЩАДКА', id: '02' },
  { name: 'Офис', map: 'ОФИС', id: '03' },
];
export const POV_SHOTS = sites.map((site, i) => ({ ...site, start: [0, 73 / FPS, 129 / FPS][i] }));
export const SITE_SHOTS = [sites[1], sites[0], sites[2]].map((site, i) => ({ ...site, start: 22 + i }));

export const CHAPTERS = [
  {
    start: 0, label: 'Вид из камеры', heading: ['Игровая камера'],
    speaker: 'Голос из игры',
    narration: 'Так, в кадре склад. Теперь площадка. А вот и офис.',
    voice: { file: 'game-01-camera.mp3', offset: .18, tempo: 1.105, radio: true },
  },
  {
    start: 6, label: 'Сигнал и Game Over', heading: ['Конец игрового уровня'],
    speaker: 'Голос из игры',
    narration: 'Стоп, что это за звук? Это часть уровня? А, всё. Конец игры.',
    voice: { file: 'game-02-radio.mp3', offset: .72, tempo: 1.18, radio: true },
  },
  {
    start: 13, label: 'Заметить на подлёте', heading: ['Заметить вовремя.'],
    speaker: 'Диктор',
    narration: 'Вне игры важно заметить дрон ещё на подлёте. Детектор подаёт короткий звуковой сигнал прямо на объекте.',
    voice: { file: 'game-03-signal.mp3', offset: .33, tempo: 1 },
  },
  {
    start: 22, label: 'Площадка, склад и офис', heading: ['Объекты'],
    speaker: 'Диктор',
    narration: 'Магазин «В окопе».',
    voice: { file: 'game-04-store.mp3', offset: .13, tempo: 1 },
  },
  {
    start: 25, label: 'Слоган и контакты', heading: ['Магазин «В Окопе»'],
    speaker: 'Диктор', narration: SLOGAN,
    voice: { file: 'r4-05-final.mp3', offset: .48, tempo: 1 },
  },
];

export function chapterAt(time) {
  return CHAPTERS.findLastIndex(({ start }) => time >= start);
}
