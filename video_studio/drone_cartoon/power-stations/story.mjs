export const TITLE = 'Портативные электростанции в наличии';
export const SLUG = 'power-stations';
export const FILE = 'v_okope_elektrostancii_v_nalichii.mp4';
export const DURATION = 60;
export const FPS = 30;
export const FRAME_COUNT = DURATION * FPS;
export const BPM = 170;
export const WIPE = .16;
export const CONTACTS = [];
const beat = (count) => Math.round(count * 60 / BPM * FPS) / FPS;

// Availability is the owner's supplied list. A badge can describe a region,
// revision, rated power or capacity; it is never a price or a run-time claim.
export const PAGES = [
  { brand: 'ALLPOWERS', accent: 'amber', shape: 0, items: [
    { model: 'R1500 Lite' },
    { model: 'R2500', revision: 'V.2' },
    { model: 'R3500', revision: 'V.2' },
  ] },
  { brand: 'BLUETTI', accent: 'blue', shape: 1, items: [
    { model: 'AC70P', watts: 1000 },
    { model: 'AC180P', watts: 1800 },
    { model: 'AC200PL', watts: 2400 },
  ] },
  { brand: 'DJI', accent: 'leaf', shape: 2, items: [
    { model: 'Power 1000 Mini', region: 'EU' },
    { model: 'Power 1000 V2', region: 'EU' },
    { model: 'Power 2000', region: 'CN' },
    { model: 'Power Expansion Battery 2000', battery: true },
  ] },
  { brand: 'EcoFlow', accent: 'blue', shape: 3, part: 1, items: [
    { model: 'DELTA 3', wattHours: 1024 },
    { model: 'DELTA 3 Plus' },
    { model: 'DELTA 3 Max' },
  ] },
  { brand: 'EcoFlow', accent: 'blue', shape: 4, part: 2, items: [
    { model: 'DELTA 3 Max Plus' },
    { model: 'DELTA 3 Ultra Plus' },
    { model: 'DELTA Pro 3' },
  ] },
  { brand: 'OUKITEL', accent: 'amber', shape: 5, items: [
    { model: 'P2001E Pro' },
    { model: 'BP3000E Plus' },
    { model: 'BP5000E Pro Max' },
  ] },
  { brand: 'PECRON', accent: 'leaf', shape: 6, items: [
    { model: 'F1000LFP', watts: 1500 },
    { model: 'E3800LFP', watts: 4200 },
    { model: 'F5000LFP', watts: 7200 },
  ] },
];
export const BRANDS = [...new Set(PAGES.map(({ brand }) => brand))];
export const ITEMS = PAGES.flatMap(({ brand, items }) => items.map((item) => ({ brand, ...item })));
export const STATIONS = ITEMS.filter(({ battery }) => !battery).length;
const timepoints = [0, 17, 36, 56, 81, 98, 117, 138, 157].map(beat);
const vo = (file, tempo, offset = .18) => ({ file: `power-${file}.mp3`, offset, tempo });
export const CHAPTERS = [
  { label: 'В наличии', heading: ['Электростанции в наличии'],
    narration: 'Портативные электростанции в наличии. Шесть брендов, двадцать одна станция.', voice: vo('01-intro', 1.10, .24) },
  { label: 'ALLPOWERS', heading: ['ALLPOWERS'],
    narration: 'ALLPOWERS: R1500 Lite и ещё две модели, обе второй версии.', voice: vo('02-allpowers', 1.06) },
  { label: 'BLUETTI', heading: ['BLUETTI'],
    narration: 'У BLUETTI три модели: AC70P, AC180P и AC200PL.', voice: vo('03-bluetti', 1.075) },
  { label: 'DJI', heading: ['DJI Power'],
    narration: 'У DJI — три станции серии Power. И отдельно — Battery 2000: это дополнительный аккумулятор, не электростанция.', voice: vo('04-dji', 1.075) },
  { label: 'EcoFlow · 1/2', heading: ['EcoFlow — первая карточка'],
    narration: 'EcoFlow: DELTA 3, DELTA 3 Plus и DELTA 3 Max.', voice: vo('05-ecoflow', 1.08) },
  { label: 'EcoFlow · 2/2', heading: ['EcoFlow — вторая карточка'],
    narration: 'Дальше — DELTA 3 Max Plus, DELTA 3 Ultra Plus и DELTA Pro 3.', voice: vo('06-ecoflow-more', 1.075) },
  { label: 'OUKITEL', heading: ['OUKITEL'],
    narration: 'У OUKITEL три станции: модель серии P и две серии BP — Plus и Pro Max.', voice: vo('07-oukitel', 1.065) },
  { label: 'PECRON', heading: ['PECRON'],
    narration: 'PECRON: три модели с индексом LFP. Их мощности в ваттах — рядом с названиями.', voice: vo('08-pecron', 1.065) },
  { label: '«В Окопе»', heading: ['Магазин «В Окопе»'],
    narration: 'Электростанции в наличии. Магазин «В Окопе».', voice: vo('09-end', 1.05, .17) },
].map((chapter, i) => ({ ...chapter, start: timepoints[i] }));
export const SHOTS = [
  { start: 0, kind: 'intro' },
  { start: beat(8), kind: 'intro', alternate: true },
  ...PAGES.map((page, i) => ({ start: CHAPTERS[i + 1].start, kind: 'catalogue', page })),
  { start: CHAPTERS.at(-1).start, kind: 'outro' },
];
export const readableNumber = (value) => String(value).replace(/\B(?=(\d{3})+(?!\d))/g, '\u00a0');
export const fullModel = ({ model, revision, region }) => [model, revision, region].filter(Boolean).join(' ');
export function badge(item) {
  if (item.watts) return { caption: 'МОЩНОСТЬ', value: `${readableNumber(item.watts)} Вт` };
  if (item.wattHours) return { caption: 'ЁМКОСТЬ', value: `${readableNumber(item.wattHours)} Вт·ч` };
  if (item.region) return { caption: 'ВЕРСИЯ', value: item.region };
  if (item.revision) return { caption: 'ВЕРСИЯ', value: item.revision };
  return null;
}
export function chapterAt(seconds) {
  return CHAPTERS.findLastIndex(({ start }) => seconds >= start);
}

export function formatCatalogue() {
  const groups = BRANDS.map((brand) => {
    const rows = ITEMS.filter((item) => item.brand === brand).map((item) => {
      const spec = item.watts ? ` — ${readableNumber(item.watts)} Вт, мощность` :
        item.wattHours ? ` — ${readableNumber(item.wattHours)} Вт·ч, ёмкость` : '';
      return `${fullModel(item)}${spec}${item.battery ? ' — дополнительный аккумулятор' : ''}`;
    });
    return [brand, ...rows].join('\n');
  });
  return [TITLE, '21 электростанция и 1 дополнительный аккумулятор. Шесть брендов.', ...groups].join('\n\n') + '\n';
}
