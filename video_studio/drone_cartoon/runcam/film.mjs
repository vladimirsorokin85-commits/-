import { createCanvas, GlobalFonts, loadImage } from '@napi-rs/canvas';
import { fileURLToPath } from 'node:url';
import { ease, ellipse, fill, line, path, rounded } from '../bulat/art.mjs';
import { CHAPTERS, DURATION, PHOTOS, SHOTS, SPECS, WIPE, chapterAt } from './story.mjs';

export const WIDTH = 540;
export const HEIGHT = 960;
const W = WIDTH, H = HEIGHT, M = 36, LIVE = 468;
const DARK = { bg: '#112028', end: '#172b35', card: '#233541', ink: '#fff3df', sub: '#b4c8c6', accent: '#ffa560', line: '#657f82', mark: '#45636864' };
const PALE = { bg: '#f4f0e5', end: '#d8dedd', card: '#fff6e8', ink: '#1b303b', sub: '#48656a', accent: '#9b4927', line: '#9bafb0', mark: '#96aeb05e' };
const assets = Object.fromEntries(await Promise.all(PHOTOS.map(async (name) => [
  name, await loadImage(fileURLToPath(new URL(`./assets/${name}.jpg`, import.meta.url))),
])));
const logo = await loadImage(fileURLToPath(new URL('../bulat/assets/v-okope-white.png', import.meta.url)));
const section = ['ОБЪЕКТИВ', 'КАЧЕСТВО ЗАПИСИ', 'ПИТАНИЕ', 'УПРАВЛЕНИЕ', 'КОМПЛЕКТ'];
let loaded = false;
function fonts() {
  if (loaded) return;
  for (const face of ['Black','Medium']) {
    if (!GlobalFonts.registerFromPath(fileURLToPath(new URL(`../../fonts/Roboto-${face}.woff`, import.meta.url)), `Runcam${face}`)) {
      throw new Error(`Не найден шрифт Roboto ${face}`);
    }
  }
  loaded = true;
}
function txt(ctx, text, x, y, px, color, { max = LIVE, align = 'left', medium = false, track = 0 } = {}) {
  const chars = [...text], font = `Runcam${medium ? 'Medium' : 'Black'}`;
  ctx.font = `${px}px ${font}`;
  const measured = track ? chars.reduce((sum, ch) => sum + ctx.measureText(ch).width, 0) : ctx.measureText(text).width;
  const spacing = track * (chars.length - 1);
  if (measured + spacing > max) ctx.font = `${px * (max - spacing) / measured}px ${font}`;
  ctx.fillStyle = color;
  ctx.textBaseline = 'alphabetic';
  if (!track) { ctx.textAlign = align; ctx.fillText(text, x, y); return; }
  const letters = chars.map(ch => [ch, ctx.measureText(ch).width + track]);
  const span = letters.reduce((sum, [,w]) => sum + w, -track);
  ctx.textAlign = 'left';
  x -= align === 'center' ? span / 2 : align === 'right' ? span : 0;
  for (const [ch, step] of letters) { ctx.fillText(ch, x, y); x += step; }
}
function small(ctx, content, x, y, p, opts = {}) {
  txt(ctx, content, x, y, 13, p.sub, { track: 1.18, ...opts });
}
function sceneStart(ctx, p, t, tag) {
  const bg = ctx.createLinearGradient(130, 0, W, H);
  bg.addColorStop(0, p.bg); bg.addColorStop(1, p.end);
  fill(ctx, bg, 0, 0, W, H);
  path(ctx, [[W-109,0],[W,0],[W,752],[W-109,793]], p === DARK ? '#46727c26' : '#8caeb126');
  path(ctx, [[0,687],[W,407],[W,459],[0,741]], p === DARK ? '#6c898518' : '#a8b9a034');
  for (let y = 29 + t * 8 % 24; y < H; y += 24) {
    for (let x = 13; x < W; x += 24) fill(ctx, p.mark, x, y, 1.1, 1.1);
  }
  const index = chapterAt(t);
  fill(ctx, p.accent, M, 55, 13, 13);
  small(ctx, tag ?? section[index], 61, 66, p);
  small(ctx, `${String(index+1).padStart(2,'0')} / ${String(CHAPTERS.length).padStart(2,'0')}`, W-M, 66, p, { align: 'right' });
  line(ctx, M, 87, LIVE, p.line, 1);
  line(ctx, M, 894, LIVE, p.line, 1);
  line(ctx, M, 894, LIVE * t / DURATION, p.accent, 2.1);
  small(ctx, 'RUNCAM   /   HELMET CAMERA 2', M, 923, p);
  small(ctx, `00:${String(Math.floor(t)).padStart(2,'0')}`, W-M, 923, p, { align: 'right' });
}
function headline(ctx, p, top, bottom, size = 78) {
  txt(ctx, top, 33, 176, size, p.ink);
  txt(ctx, bottom, 33, 261, size, p.accent);
}
function note(ctx, p, label, value, y = 786) {
  small(ctx,label,M,y,p);
  txt(ctx,value,M,y+56,38,p.ink,{ max: LIVE });
}
function image(ctx, name, rect, src, zoom = 1) {
  const im = assets[name], [x,y,w,h] = rect;
  let [sx,sy,sw,sh] = src;
  const naturalAspect = im.width / im.height, aspect = w / h;
  if (sw * naturalAspect / sh > aspect) {
    const want=sh*aspect/naturalAspect; sx+=(sw-want)/2;sw=want;
  } else {
    const want=sw*naturalAspect/aspect;sy+=(sh-want)/2;sh=want;
  }
  sx += sw*(1-1/zoom)/2; sy += sh*(1-1/zoom)/2; sw /= zoom; sh /= zoom;
  ctx.imageSmoothingQuality = 'high';
  ctx.drawImage(im,sx*im.width,sy*im.height,sw*im.width,sh*im.height,x,y,w,h);
}
function corners(ctx, x,y,w,h, tone, span = 12) {
  for (const [a,b] of [[0,0],[0,1],[1,0],[1,1]]) {
    const tx=x+a*w,ty=y+b*h;
    path(ctx, [[tx+span*(a?-1:1),ty],[tx,ty],[tx,ty+span*(b?-1:1)]], null, tone, 2.25);
  }
}
function panel(ctx, p, name, rect, crop, { label, zoom } = {}) {
  const [x,y,w,h] = rect;
  rounded(ctx,p === DARK ? '#11171f71' : '#34526123',x-4,y-3,w+10,h+(label?36:10),7);
  rounded(ctx,p.card,x-4,y-4,w+8,h+(label?32:8),5,p.line,1.2);
  image(ctx,name,rect,crop,zoom);
  corners(ctx,x+12,y+12,w-24,h-24,p === DARK ? '#f8b579' : '#9e582e',11);
  if(label) small(ctx,label,x+7,y+h+18.5,p,{max:w-14,track:.95});
}
function animate(t, span) { return ease(t / span); }
const heroCrop = [0, .045, 1, .91];
function model(ctx,p) {
  txt(ctx,'RunCam',33,178,86,p.ink);
  txt(ctx,'Helmet Camera 2',M,254,63,p.accent);
}
function hero(ctx,t,abs) {
  const p=DARK;
  sceneStart(ctx,p,abs,'КАМЕРА НА ШЛЕМ');
  model(ctx,p);
  panel(ctx,p,'camera',[40,304+(1-animate(t,.55))*15,460,398],heroCrop,{label:'КОРПУС  /  ТРУБКА  /  ОБЪЕКТИВ',zoom:1+Math.min(.055,t*.017)});
  rounded(ctx,'#294650',M,770,LIVE,77,8,'#6f8b8a',1.25);
  txt(ctx,'Съёмка от первого лица',270,819,36,p.ink,{align:'center',max:425});
}
function lens(ctx,t,abs) {
  const p=PALE;
  sceneStart(ctx,p,abs);
  headline(ctx,p,'Выносной','объектив',82);
  panel(ctx,p,'lens',[40,308,460,415],[.15,.225,.71,.577],{label:'ФОТО  /  КРУПНЫЙ ПЛАН',zoom:1+.06*animate(t,2.5)});
  note(ctx,p,'КОНСТРУКЦИЯ','На гибкой трубке');
}
function flexDrawing(ctx,t) {
  const a=animate(t-.16,1.1), x=380, y=556-94*a;
  fill(ctx,'#334952',65,604,410,1.2);
  ellipse(ctx,'#0e2129',241,611,158,12);
  for (const [dy,color] of [[3,'#132a34'],[0,'#607b82'],[-5,'#a4c5bc']]) {
    ctx.beginPath(); ctx.moveTo(217,506+dy); ctx.bezierCurveTo(279,506+dy,305+38*a,552-69*a+dy,x,y+dy);
    ctx.strokeStyle=color; ctx.lineWidth=dy===3?23:dy===0?17:2.4; ctx.stroke();
  }
  ctx.setLineDash([7,7]);
  path(ctx,[[416,482],[472,445-41*a]],null,'#e8ac709d',1.8);
  ctx.setLineDash([]);
  rounded(ctx,'#30444a',91,436,133,155,15,'#82a2a0',2.0);
  rounded(ctx,'#263940',83,440,30,146,7,'#829692',1.6);
  rounded(ctx,'#1b2e3a',128,477,59,41,8,'#a4b8ad',1.6);
  ellipse(ctx,'#e2a86b',197,499,7,7);
  ctx.save(); ctx.translate(x,y); ctx.rotate(-a*.31);
  rounded(ctx,'#2a4950',-10,-36,49,72,10,'#93b1a7',2.2);
  ellipse(ctx,'#acb9b2',35,0,16,32);
  ellipse(ctx,'#3b6068',37,0,10,24);
  ellipse(ctx,'#e4bb83',37,-6,3,9);
  ctx.restore();
}
function angle(ctx,t,abs) {
  const p=DARK;
  sceneStart(ctx,p,abs);
  headline(ctx,p,'Меняйте угол','съёмки',72);
  rounded(ctx,'#24414b',M,309,LIVE,404,8,p.line,1.4);
  ellipse(ctx,'#2e535a',284,500,155,154);
  corners(ctx,56,329,428,364,'#7f9a9585');
  flexDrawing(ctx,t);
  small(ctx,'УСЛОВНАЯ СХЕМА',55,681,p);
  note(ctx,p,'КОРПУС ОСТАЁТСЯ НА МЕСТЕ','Гибкая трубка');
}
function video(ctx,t,abs) {
  const p=DARK;
  sceneStart(ctx,p,abs);
  txt(ctx,'Full HD',31,229,122,p.ink);
  small(ctx,`${SPECS.width} × ${SPECS.height} ПИКСЕЛЕЙ`,M,269,p,{track:1.75});
  panel(ctx,p,'camera',[40,321,460,280],[.05,.18,.90,.67],{label:'ФОТО  /  КОРПУС И ТРУБКА',zoom:1+.04*animate(t,2.55)});
  txt(ctx,String(SPECS.fps),32,803,156,p.accent,{max:190});
  txt(ctx,'кадров/с',241,792,52,p.ink,{max:255});
  small(ctx,'МАКСИМАЛЬНАЯ ЧАСТОТА',M,850,p,{track:1.35});
}
function aperture(ctx,t,abs) {
  const p=PALE;
  sceneStart(ctx,p,abs);
  txt(ctx,'Диафрагма',M,177,67,p.ink);
  txt(ctx,`f/${SPECS.aperture}`,28,339,145,p.accent);
  panel(ctx,p,'lens',[39,389,462,354],[.265,.335,.508,.405],{label:'ФОТО  /  ОПТИКА',zoom:1+.048*animate(t,2.6)});
  note(ctx,p,'СВЕТОСИЛА ОБЪЕКТИВА','Для слабого света');
}
function waterIcon(ctx,x,y,color) {
  ctx.beginPath(); ctx.moveTo(x,y-22);
  ctx.bezierCurveTo(x+6,y-10,x+17,y-1,x+17,y+9);
  ctx.bezierCurveTo(x+17,y+30,x-17,y+30,x-17,y+9);
  ctx.bezierCurveTo(x-17,y-1,x-6,y-10,x,y-22);
  ctx.strokeStyle=color;ctx.lineWidth=3;ctx.stroke();
}
function shell(ctx,t,abs) {
  const p=PALE;
  sceneStart(ctx,p,abs);
  headline(ctx,p,'Защита','корпуса',82);
  panel(ctx,p,'base',[40,310,460,343],[0,.225,1,.738],{label:'ФОТО  /  ОБРАТНАЯ СТОРОНА',zoom:1+(1-animate(t,.6))*.048});
  for (const [i, word] of ['Пыль','Брызги'].entries()) {
    const x=M+239*i;
    rounded(ctx,p.card,x,738,229,111,7,p.line,1.2);
    if (i) waterIcon(ctx,x+43,790,p.accent);
    else for (const [dx,dy,r] of [[-13,-9,4],[5,-12,4],[10,4,5],[-7,12,4],[-20,7,3],[17,14,3]]) ellipse(ctx,p.accent,x+47+dx,791+dy,r,r);
    txt(ctx,word,x+81,806,34,p.ink,{max:137});
  }
}
function cell(ctx,x,y,moment) {
  rounded(ctx,'#365969',x+364,y+20,26,31,4,'#c5d3bc',1.5);
  rounded(ctx,'#162e39',x,y,369,70,9,'#b5c6bd',2.2);
  rounded(ctx,'#506c69',x+9,y+9,351*animate(moment,.84),52,5);
  txt(ctx,SPECS.battery,x+183,y+47,30,'#fff3df',{align:'center',max:220});
}
function battery(ctx,t,abs) {
  const p=DARK;
  sceneStart(ctx,p,abs);
  headline(ctx,p,'Сменный','аккумулятор',77);
  panel(ctx,p,'power',[40,314,460,330],[.005,.19,.985,.732],{label:'ФОТО  /  КРЫШКА БАТАРЕИ'});
  cell(ctx,75,730,t);
  small(ctx,'ФОРМАТ ПИТАНИЯ  /  СХЕМА',M,849,p);
}
function runtime(ctx,t,abs) {
  const p=PALE;
  sceneStart(ctx,p,abs);
  small(ctx,'ПО ДАННЫМ ПРОИЗВОДИТЕЛЯ',M,139,p,{track:1.5});
  txt(ctx,'Время записи',34,221,75,p.ink);
  rounded(ctx,'#233e46',M,270,LIVE,324,12,'#92a7a3',1.35);
  const pos=animate(t,.76);
  ctx.save();
  ctx.beginPath();ctx.arc(270,431,125,Math.PI*.8,Math.PI*(2.18+.02*pos));ctx.strokeStyle='#66888a';ctx.lineWidth=9;ctx.stroke();
  ctx.beginPath();ctx.arc(270,431,125,Math.PI*.8,Math.PI*(.81+1.38*pos));ctx.strokeStyle='#ffa560';ctx.lineWidth=9;ctx.stroke();
  ctx.restore();
  txt(ctx,`≈ ${SPECS.runtime} ч`,268,464,103,'#fff3df',{align:'center',max:245});
  txt(ctx,'В РЕЖИМЕ 1080p60',270,517,17,'#c2d3cc',{align:'center',track:1.22});
  txt(ctx,'Для аккумулятора',M,673,32,p.ink);
  txt(ctx,`${String(SPECS.referenceCapacity).replace(/(?=\d{3}$)/, '\u00a0')} мА·ч`,M,754,69,p.accent);
  small(ctx,'ДАННЫЕ RUNCAM, НЕ ЗАМЕР ЭТОГО КОМПЛЕКТА',M,826,p,{track:.78});
}
function controls(ctx,t,abs) {
  const p=DARK;
  sceneStart(ctx,p,abs);
  headline(ctx,p,'Автостарт','записи',83);
  panel(ctx,p,'controls',[40,308,460,328],[0,.245,1,.685],{label:'ФОТО  /  ПЕРЕКЛЮЧАТЕЛЬ ПИТАНИЯ',zoom:1+.045*animate(t,3.5)});
  small(ctx,'ПОСЛЕ ВКЛЮЧЕНИЯ',M,734,p,{track:1.38});
  txt(ctx,'Вибрация подтверждает',M,786,35,p.ink);
  txt(ctx,'начало записи',M,831,38,p.accent);
}
function app(ctx,t,abs) {
  const p=PALE;
  sceneStart(ctx,p,abs);
  headline(ctx,p,'Проверка','кадра',82);
  rounded(ctx,'#d3dfda',M,306,LIVE,397,9,p.line,1.5);
  const y=335+(1-animate(t,.56))*16;
  rounded(ctx,'#264552',159,y,222,310,23,'#6b9391',2.5);
  rounded(ctx,'#335e65',174,y+26,192,237,12,'#76948d',1.35);
  corners(ctx,190,y+43,160,203,'#e4ebcf');
  path(ctx,[[190,y+189],[245,y+143],[280,y+183],[316,y+146],[351,y+172],[351,y+245],[190,y+245]],'#577b75');
  ellipse(ctx,'#b48d5c',303,y+110,24,24);
  ellipse(ctx,'#c4d6c7',270,y+285,7,7);
  small(ctx,'СХЕМА, НЕ КАДР С КАМЕРЫ',54,681,p,{track:1.12});
  small(ctx,'ПРЕДПРОСМОТР В RUNCAM APP',M,766,p);
  txt(ctx,`Wi-Fi ${SPECS.wifiGHz} ГГц`,M,833,60,p.ink);
}
function kit(ctx,t,abs) {
  const p=PALE;
  sceneStart(ctx,p,abs);
  headline(ctx,p,'Крепления','и липучки',79);
  panel(ctx,p,'kit-top',[46,303,448,430],[.014,.04,.973,.918],{label:'ФОТО  /  КОМПЛЕКТ',zoom:1+.012*animate(t,2.8)});
  txt(ctx,'Зарядный кабель',M,836,41,p.ink);
}
function unbox(ctx,t,abs) {
  const p=DARK;
  sceneStart(ctx,p,abs);
  headline(ctx,p,'Что в','коробке',84);
  panel(ctx,p,'open-box',[40,306,460,243],[.01,.11,.96,.823],{label:'КАМЕРА И ИНСТРУКЦИЯ'});
  panel(ctx,p,'kit-angle',[40,613+(1-animate(t,.5))*14,460,195],[.12,.333,.83,.53],{label:'КРЕПЛЕНИЯ, ЛИПУЧКИ, КАБЕЛЬ'});
}
function finale(ctx,t,abs) {
  const p=DARK;
  sceneStart(ctx,p,abs,'КАМЕРА НА ШЛЕМ');
  model(ctx,p);
  panel(ctx,p,'box',[40,303,460,345],[.025,.143,.95,.82],{label:'RUNCAM  /  УПАКОВКА'});
  rounded(ctx,'#264550',M,713,LIVE,139,9,p.line,1.25);
  ctx.drawImage(logo,347,207,1008,908,52,730+8*(1-animate(t,.48)),109,98);
  txt(ctx,'От первого',193,773,38,p.ink,{max:278});
  txt(ctx,'лица',193,824,49,p.accent,{max:278});
}

const scenes = { hero, lens, angle, video, aperture, shell, battery, runtime, controls, app, kit, unbox, end: finale };
export function createFilm(scale = 2) {
  fonts();
  const canvas = createCanvas(W*scale,H*scale), ctx = canvas.getContext('2d');
  function setup() { ctx.setTransform(scale,0,0,scale,0,0);ctx.lineJoin='round';ctx.lineCap='round'; }
  function drawCover() {
    setup();
    sceneStart(ctx,DARK,0,'КАМЕРА НА ШЛЕМ');
    model(ctx,DARK);
    panel(ctx,DARK,'camera',[40,309,460,403],heroCrop,{label:'ВЫНОСНОЙ ОБЪЕКТИВ  /  ГИБКАЯ ТРУБКА'});
    txt(ctx,'Full HD',M,818,54,DARK.ink);
    txt(ctx,`${SPECS.fps} к/с`,W-M,818,54,DARK.accent,{align:'right'});
    return canvas;
  }
  function draw(seconds) {
    const t = Math.max(0, Math.min(DURATION, seconds));
    const i=SHOTS.findLastIndex(({start})=>start<=t), shot=SHOTS[i], dt=t-shot.start;
    setup(); scenes[shot.kind](ctx,dt,t);
    if(i && dt<WIPE) {
      const x=-200+1020*animate(dt,WIPE);
      path(ctx,[[x,0],[x+24,0],[x-113,H],[x-153,H]],'#ffb36c50');
    }
    return canvas;
  }
  return { canvas, draw, drawCover };
}
