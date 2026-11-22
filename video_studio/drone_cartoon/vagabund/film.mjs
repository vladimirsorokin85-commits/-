import { createCanvas, GlobalFonts, loadImage } from '@napi-rs/canvas';
import { fileURLToPath } from 'node:url';
import { DURATION, HEIGHT_LABEL, PACKSHOT, PHOTOS, SHOTS, WEIGHT_LABEL, WEIGHT_NOTE, WIPE } from './story.mjs';

export const WIDTH = 540;
export const HEIGHT = 960;
const W = WIDTH, H = HEIGHT;
const PAPER = '#f3ecd9', INK = '#25352b', RUST = '#973b27', COPPER = '#cd7653';
const SAGE = '#dbe2cf', MINT = '#adc1a7', WHEAT = '#ebd1ae', CLAY = '#c66d4f';
const images = Object.fromEntries(await Promise.all(PHOTOS.map(async (name) => [
  name, await loadImage(fileURLToPath(new URL(`./assets/${name}.png`, import.meta.url))),
])));
for (const weight of ['Black', 'Medium']) {
  const font = fileURLToPath(new URL(`../../fonts/Roboto-${weight}.woff`, import.meta.url));
  if (!GlobalFonts.registerFromPath(font, `Vagabund${weight}`)) throw new Error(`Не загружен шрифт ${weight}`);
}
const clamp = (x, lo, hi) => Math.min(hi, Math.max(lo, x));
const ease = n => { const t = clamp(n, 0, 1); return t*t*(3 - 2*t); };
function fill(c, color, x=0, y=0, w=W, h=H) { c.fillStyle=color; c.fillRect(x,y,w,h); }
function line(c, points, color, width=2) {
  c.beginPath(); points.forEach(([x,y],i)=>i?c.lineTo(x,y):c.moveTo(x,y));
  c.strokeStyle=color; c.lineWidth=width; c.stroke();
}
function text(c, value, x, y, px, color=INK, { max=455, face='Black' }={}) {
  c.save(); c.translate(x,y); c.font=`${px}px Vagabund${face}`; c.textBaseline='alphabetic';
  c.scale(Math.min(1,max/c.measureText(value).width),1);
  c.fillStyle=color; c.fillText(value,0,0); c.restore();
}
function tag(c, value, x=44, y=138, color=INK) {
  c.font='17px VagabundMedium'; c.textBaseline='alphabetic'; c.fillStyle=color;
  for(const ch of value) { c.fillText(ch,x,y); x+=c.measureText(ch).width+1.72; }
}
function note(c, value, x, y, px=30, color=INK) { text(c,value,x,y,px,color,{face:'Medium'}); }
function mark(c, x, y, color) { line(c,[[x-6,y],[x+6,y]],color,1.4); line(c,[[x,y-6],[x,y+6]],color,1.4); }
function photo(c, name, [x,y,w,h], [u,v,a,b]=[0,0,1,1]) {
  const im=images[name], sx=u*im.width,sy=v*im.height,sw=a*im.width,sh=b*im.height;
  const scale=Math.min(w/sw,h/sh), dw=sw*scale,dh=sh*scale;
  c.drawImage(im,sx,sy,sw,sh,x+(w-dw)/2,y+(h-dh)/2,dw,dh);
}
function ground(c, color, x, y, w, h) {
  c.beginPath();c.ellipse(x,y,w,h,0,0,2*Math.PI);c.fillStyle=color;c.fill();
}
function tread(c, x, y, w, h, color, turns=7) {
  const pitch=w/turns;
  c.beginPath(); c.moveTo(x,y);
  for(let i=0;i<turns;i++){
    const l=x+i*pitch;
    c.lineTo(l+.08*pitch,y);c.lineTo(l+.23*pitch,y+h*.38);
    c.lineTo(l+.74*pitch,y+h*.38);c.lineTo(l+.93*pitch,y);
  }
  c.lineTo(x+w,y);c.lineTo(x+w,y+h);c.lineTo(x,y+h);c.closePath();c.fillStyle=color;c.fill();
}
function field(c, y, tone, lower, delta=0) {
  fill(c,tone,0,y,W,930-y);
  c.beginPath();c.moveTo(0,y+158+delta);c.lineTo(W,y+45+delta);c.lineTo(W,930);c.lineTo(0,930);c.closePath();
  c.fillStyle=lower;c.fill();
}
function gauge(c,x,top,bottom,progress) {
  // Printed reference marks, not a measurement of the photograph.
  const end=top+(bottom-top)*progress;
  line(c,[[x-14,top],[x,top],[x,end],[x-14,end]],RUST,2.6);
  for(let y=top+15,i=1;y<end-3;y+=15,i++)line(c,[[x-(i%4===0?12:6),y],[x,y]],RUST,1.35);
}
function macro(c, name, frame, crop, background, border) {
  const [x,y,w,h]=frame;
  fill(c,border,x+5,y+7,w,h);fill(c,background,x,y,w,h);
  c.save();c.beginPath();c.rect(x,y,w,h);c.clip();photo(c,name,[x-2,y-2,w+4,h+4],crop);c.restore();
  mark(c,x-10,y-10,border);mark(c,x+w+10,y+h+10,border);
}
function grain() {
  const s=createCanvas(173,191),g=s.getContext('2d'),id=g.createImageData(s.width,s.height);
  let seed=708;
  for(let i=0;i<id.data.length;i+=4){
    seed=(Math.imul(seed,1664525)+1013904223)>>>0;
    const v=seed>>>24,light=v>124;
    id.data[i]=light?248:29;id.data[i+1]=light?232:41;id.data[i+2]=light?200:31;
    id.data[i+3]=v%12+(v<12?11:0);
  }
  g.putImageData(id,0,0);return s;
}
const paperGrain=grain();

function hero(c,t,cover=false) {
  const a=cover ? .68 : ease(t/4.45);
  fill(c,PAPER);
  field(c,385,SAGE,'#c0cdb4',60-22*a);
  tread(c,-22,709,590,144,'#9eb495',8);
  ground(c,'#25352b28',269,764,235,24);
  photo(c,'pair',[18-5*a,431-15*a,504+10*a,369+7*a]);
  tag(c,'В НАЛИЧИИ  /  PRABOS');
  text(c,'VAGABUND',39,250,99);
  text(c,'ANKLE FIELD',41,333,83,RUST);
  if(cover)tag(c,'БОТИНКИ  ·  14,5 СМ',45,837);
  else tag(c,'МЕЖДУ КРОССОВКАМИ И САПОГАМИ',45,837);
}
function side(c,t) {
  const a=ease(t/2.4);
  fill(c,INK);
  text(c,'Рабочая',40,224,102,PAPER);
  text(c,'середина',40,322,101,'#e9a784');
  tag(c,'ФОРМАТ БОТИНКА',45,134,MINT);
  field(c,384,'#405245','#36493c',72-13*a);
  tread(c,-14,652,572,134,'#536753',8);
  photo(c,'angle',[26+5*a,393-8*a,485,418]);
}
function height(c,t) {
  const a=ease(t/3.3);
  fill(c,PAPER); field(c,374,SAGE,'#c4d1b8',45);
  tag(c,'ВЫСОТА БОТИНКА');
  text(c,HEIGHT_LABEL,39,282,149,RUST);
  gauge(c,494,402,760,ease(.52+t/1.8));
  ground(c,'#25352b23',242,747,214,20);
  photo(c,'profile',[32,389-9*a,441,364]);
  tag(c,'СРЕДНЯЯ ВЫСОТА',45,819);
}
function ankle(c,t) {
  const a=ease(t/3);
  fill(c,WHEAT);
  tag(c,'ПОСАДКА'); text(c,'Щиколотка',39,224,96); text(c,'закрыта',41,309,88,RUST);
  macro(c,'profile',[38,396-10*a,465,369],[.435,.002,.565,.611],'#c7ceb8',INK);
  note(c,'Голень остаётся свободной',44,823,32);
}
function laces(c,t) {
  const a=ease(t/3.45);
  fill(c,INK); tag(c,'КРУПНЫЙ ПЛАН  /  01',45,138,MINT);
  text(c,'Шнуровка',39,241,102,PAPER);
  macro(c,'pair',[39,321-10*a,464,405],[.092,.105,.564,.602],'#586954',COPPER);
  note(c,'Снизу — текстильные петли',43,811,33,PAPER);
}
function hooks(c,t) {
  const a=ease(t/2.2);
  fill(c,PAPER);tag(c,'КРУПНЫЙ ПЛАН  /  02');
  text(c,'Крючки',40,238,122,INK);
  note(c,'Металлические, в верхней части',44,309,29);
  macro(c,'profile',[36,424-8*a,467,305],[.45,.10,.46,.396],SAGE,RUST);
}
function lining(c,t) {
  const a=ease(t/3.9);
  fill(c,SAGE); tag(c,'ТЕКСТИЛЬНАЯ ПОДКЛАДКА');
  text(c,'DRI-LEX',40,242,127);
  note(c,'PES + PA',46,306,37,RUST);
  macro(c,'angle',[39,417-9*a,463,306],[.018,.003,.554,.401],'#b7c4a9',INK);
  text(c,'Без мембраны',41,821,47);
}
function sole(c,t) {
  const a=ease(t/3.2);
  fill(c,INK);
  tag(c,'ПОДОШВА',44,138,MINT);
  text(c,'PHOBOS',39,255,127,PAPER);
  note(c,'Двойная плотность',45,326,38,'#efa68a');
  field(c,401,'#465a49','#3b5041',55);
  tread(c,-16,688,572,139,COPPER,8);
  photo(c,'profile',[12-5*a,405-9*a,516+10*a,402]);
}
function materials(c,t) {
  const a=ease(t/2.05);
  fill(c,PAPER);tag(c,'ДВА МАТЕРИАЛА  /  PHOBOS');
  text(c,'Полиуретан',40,235,86);text(c,'+ резина',42,321,88,RUST);
  fill(c,SAGE,0,469,W,339);tread(c,0,673,W,135,'#a4b69d',8);
  macro(c,'profile',[29,479-7*a,480,225],[.005,.555,.994,.444],'#e1e6d5',INK);
}
function insert(c,t) {
  const a=ease(t/4.15);
  fill(c,WHEAT); tag(c,'ВНУТРИ ПОДОШВЫ');
  text(c,'Кевларовая',40,230,86);text(c,'вставка',40,319,102,RUST);
  field(c,375,'#dfb792','#d6a681',25);
  photo(c,'angle',[35,372-9*a,470,400]);
  line(c,[[44,788],[174,788]],INK,2.2);mark(c,188,788,INK);
  note(c,'Помогает защитить от проколов',45,833,29);
}
function limits(c,t) {
  const a=ease(t/2.02);
  fill(c,RUST); tag(c,'ВСТАВКА ОТ ПРОКОЛОВ',44,139,WHEAT);
  text(c,'Не броня.',40,256,112,PAPER);
  tread(c,-15,528,575,193,CLAY,8);
  photo(c,'profile',[44,400-6*a,452,386]);
}
function days(c,t) {
  const a=ease(t/4.8);
  fill(c,PAPER);tag(c,'НА КАЖДЫЙ ДЕНЬ');
  text(c,'Город',40,238,112);text(c,'и выезды',40,339,102,RUST);
  field(c,392,SAGE,'#bfceb4',59);
  for(let i=0;i<7;i++)line(c,[[0,562+i*23],[275,487+i*24],[540,464+i*23]],'#6b856b43',1.4);
  photo(c,'pair',[25-4*a,438-9*a,490+7*a,363]);
  note(c,'Без глубокой грязи',45,838,31);
}
function weight(c,t) {
  const a=ease(t/3.6);
  fill(c,SAGE);
  tag(c,'ВЕС  /  ПО ДАННЫМ PRABOS');text(c,WEIGHT_LABEL,36,269,158);
  note(c,WEIGHT_NOTE,45,331,33,RUST);
  field(c,407,'#c3cfb8','#b4c2a9',43);
  ground(c,'#25352b30',260,760,210,18);
  photo(c,'angle',[45+6*a,399-8*a,451,399]);
}
function stock(c,t) {
  const a=ease(t/1.64);
  fill(c,INK);tag(c,'PRABOS  /  VAGABUND',44,138,MINT);
  text(c,'В наличии',38,252,101,PAPER);
  tread(c,-12,601,568,180,'#50644f',7);
  photo(c,'pair',[18-3*a,367-8*a,504+6*a,429]);
}
function packshot(c,t) {
  const a=ease(t/3.8);
  fill(c,PAPER);
  tag(c,'PRABOS VAGABUND ANKLE FIELD',45,137,INK);
  text(c,PACKSHOT.lines[0],42,222,62);
  text(c,PACKSHOT.lines[1],40,311,79,RUST);
  field(c,397,SAGE,'#b7c8ac',56);
  tread(c,-16,721,576,142,'#96af93',8);
  ground(c,'#26352c28',268,774,225,19);
  photo(c,'pair',[24-5*a,435-5*a,492+10*a,370]);
}
const scenes={hero,side,height,ankle,laces,hooks,lining,sole,materials,insert,limits,days,weight,stock,packshot};
const paint=(c,{kind,start},time)=>scenes[kind](c,Math.max(0,time-start));

// A notched edge echoes the rubber lugs. The wipe reveals the next real photo, not a simulated test.
function wipe(c, t, draw) {
  if (t<=0) return;
  const x=-140+(W+300)*ease(t/WIPE);
  const edge=[[x-56,0]];
  for(let y=0;y<H;y+=60){
    const left=x+(y/H-.5)*112;
    edge.push([left+22,y+17],[left+22,y+44],[left-37,y+60]);
  }
  c.save();c.beginPath();c.moveTo(-50,0);edge.forEach(pt=>c.lineTo(...pt));c.lineTo(-50,H);
  c.closePath();c.clip();draw();c.restore();
  line(c,edge,COPPER,5);
}
export function createFilm(scale=1) {
  const canvas=createCanvas(Math.round(W*scale),Math.round(H*scale)),ctx=canvas.getContext('2d');
  ctx.scale(canvas.width/W,canvas.height/H);ctx.imageSmoothingQuality='high';
  const pattern=ctx.createPattern(paperGrain,'repeat');
  const finish=()=>{fill(ctx,pattern);return canvas;};
  function draw(seconds) {
    const time=clamp(seconds,0,DURATION), index=SHOTS.findLastIndex(({start})=>time>=start);
    const shot=SHOTS[index],local=time-shot.start;
    if(index&&local<WIPE){paint(ctx,SHOTS[index-1],shot.start);wipe(ctx,local,()=>paint(ctx,shot,time));}
    else paint(ctx,shot,time);
    return finish();
  }
  function drawCover(){hero(ctx,2,true);return finish();}
  return {canvas,draw,drawCover};
}
