import { createCanvas, GlobalFonts, loadImage } from '@napi-rs/canvas';
import { fileURLToPath } from 'node:url';
import { DURATION, DETAILS, MODEL, SHOTS, WIPE } from './story.mjs';

export const WIDTH = 540;
export const HEIGHT = 960;
const W = WIDTH, H = HEIGHT, TAU = Math.PI * 2;
const PAPER = '#f1ecde', INK = '#153f36', TEAL = '#0d5e51', BERRY = '#a62559', PINK = '#f2a2b7';
const files = { rim: 'rim.png', open: 'open.jpg', winding: 'winding.jpg', cases: 'cases.jpg', type: 'type.jpg', length: 'length.jpg' };
const photos = Object.fromEntries(await Promise.all(Object.entries(files).map(async ([key,file]) => [
  key, await loadImage(fileURLToPath(new URL(`./assets/${file}`, import.meta.url))),
])));
for (const kind of ['Black','Medium']) {
  const path = fileURLToPath(new URL(`../../fonts/Roboto-${kind}.woff`, import.meta.url));
  if (!GlobalFonts.registerFromPath(path, `Fiber${kind}`)) throw new Error(`Не загружен шрифт: ${kind}`);
}
const clamp = (v, min, max) => Math.min(max, Math.max(min, v));
const move = (v) => { const a = clamp(v,0,1); return a*a*(3-2*a); };
function fill(ctx, color, x=0, y=0, w=W, h=H) {
  ctx.fillStyle = color;
  ctx.fillRect(x,y,w,h);
}
function text(ctx, value, x,y,px,color, max=450, face='Black') {
  ctx.save();
  ctx.translate(x,y);
  ctx.font = `${px}px Fiber${face}`;
  ctx.textBaseline = 'alphabetic';
  ctx.scale(Math.min(1, max / ctx.measureText(value).width),1);
  ctx.fillStyle = color;
  ctx.fillText(value,0,0);
  ctx.restore();
}
function caption(ctx, value, x,y,color=INK) {
  ctx.font = '17px FiberMedium';
  ctx.textBaseline = 'alphabetic';
  ctx.fillStyle = color;
  for (const ch of value) {
    ctx.fillText(ch,x,y);
    x += ctx.measureText(ch).width + 1.6;
  }
}
function oval(ctx, x,y,rx,ry, tilt=0) {
  ctx.beginPath();
  ctx.ellipse(x,y,rx,ry,tilt,0,TAU);
}
function disc(ctx, x,y,rx,ry,tone,tilt=0) {
  oval(ctx,x,y,rx,ry,tilt); ctx.fillStyle=tone; ctx.fill();
}
function through(ctx, x,y,rx,ry,tilt, draw) {
  ctx.save(); oval(ctx,x,y,rx,ry,tilt); ctx.clip(); draw(); ctx.restore();
}
function image(ctx, name, [x,y,w,h], { focusX=.5, focusY=.5, zoom=1 } = {}) {
  const im=photos[name], ratio=Math.max(w/im.width,h/im.height)*zoom;
  const sw=w/ratio,sh=h/ratio;
  const sx=clamp(im.width*focusX-sw/2,0,im.width-sw);
  const sy=clamp(im.height*focusY-sh/2,0,im.height-sh);
  ctx.drawImage(im,sx,sy,sw,sh,x,y,w,h);
}
function labelStrip(ctx, name, x,y,w,tilt) {
  const im=photos[name], h=w*im.height/im.width;
  ctx.save(); ctx.translate(x,y); ctx.rotate(tilt);
  // Slightly offset ink under a photograph of the actual relevant line.
  fill(ctx,BERRY,5,7,w,h);
  ctx.drawImage(im,0,0,w,h);
  ctx.restore();
}
function paperTexture() {
  const tile=createCanvas(213,179), ctx=tile.getContext('2d');
  const pixels=ctx.createImageData(tile.width,tile.height);
  let seed=162014887;
  for (let i=0;i<pixels.data.length;i+=4) {
    seed=(Math.imul(seed,1664525)+1013904223)>>>0;
    const n=seed>>>24, light=n>104;
    pixels.data[i]=light?249:29; pixels.data[i+1]=light?241:47; pixels.data[i+2]=light?220:34;
    pixels.data[i+3]=n%10+(n<12?13:0);
  }
  ctx.putImageData(pixels,0,0); return tile;
}
const grain=paperTexture();

// A single poster stroke goes tangentially from a loose line into the contour of a reel.
// This is graphic framing only: no depiction of the fibre being fed or installed.
function strand(ctx, a, cx,cy,rx,ry, color, { width=3, phase=0, tail=111 }={}) {
  const start=2.42+phase;
  const x=cx+rx*Math.cos(start), y=cy+ry*Math.sin(start);
  ctx.beginPath();
  ctx.moveTo(-35,y+tail);
  ctx.bezierCurveTo(22,y+tail+4,x+49,y+tail*.73,x,y);
  const steps=100;
  for(let i=1;i<=steps;i++) {
    const t=i/steps*a, theta=start+TAU*t;
    const inset=t*5.5;
    ctx.lineTo(cx+(rx-inset)*Math.cos(theta),cy+(ry-inset)*Math.sin(theta));
  }
  ctx.strokeStyle=color; ctx.lineWidth=width; ctx.lineCap='round'; ctx.lineJoin='round'; ctx.stroke();
}
function hero(ctx,t,cover=false) {
  fill(ctx,PAPER);
  const a=cover ? .72 : move(t/2.8);
  const x=47+14*a,y=385-9*a,w=491;
  const photo=photos.rim;
  disc(ctx,293,597,242,199,'#a625592e',.106);
  strand(ctx,.81+.20*move(t/1.8),291,591,252,210,BERRY,{width:4.3,tail:84});
  ctx.drawImage(photo,x,y,w,w*photo.height/photo.width);
  // The fine edge of the same ink stroke stays visible where it passes in front of the print.
  ctx.beginPath(); ctx.ellipse(293,596,248,204,.04,.22,1.43);
  ctx.strokeStyle=BERRY;ctx.lineWidth=2.7;ctx.stroke();
  caption(ctx,'ФОТООБЗОР',46,135);
  text(ctx,'ОПТОВОЛОКНО',42,226,89,INK,448);
  text(ctx,MODEL,41,335,109,BERRY);
  caption(ctx,'КАТУШКА И МАРКИРОВКА',47,837);
}
function type(ctx,t) {
  fill(ctx,TEAL);
  const a=move(t/4.1);
  disc(ctx,302,494,218,158,'#115144',.06);
  strand(ctx,.88+.17*a,300,495,233,168,PINK,{width:3.6,tail:65});
  labelStrip(ctx,'type',26+11*a,424-4*a,490,-.066+.015*a);
  caption(ctx,'ТИП ВОЛОКНА',46,142,PAPER);
  text(ctx,MODEL,42,255,105,PAPER);
  text(ctx,'Одномодовое',45,730,57,PAPER);
  text(ctx,'волокно',45,796,61,PAPER);
}
function diameter(ctx,t) {
  fill(ctx,PAPER);
  const a=move(t/4.6), y=567;
  disc(ctx,268,y+9,303,213,BERRY,-.09);
  through(ctx,270,y,302,210,-.09,()=>image(ctx,'open',[-37,348,620,432],{focusX:.52,focusY:.47,zoom:1+.045*a}));
  strand(ctx,.87+.16*a,267,y,315,226,INK,{width:2.5,phase:-.12});
  caption(ctx,'ДИАМЕТР ПО КАРТОЧКЕ',46,141);
  text(ctx,DETAILS.diameter,41,282,132,BERRY);
  caption(ctx,'ПРОЗРАЧНОЕ ВОЛОКНО',47,846);
}
function winding(ctx,t) {
  const a=move(t/3.4);
  image(ctx,'winding',[0,0,W,H],{focusX:.65+.025*a,focusY:.50,zoom:1.015+.09*a});
  disc(ctx,240,60,402,263,BERRY,.045);
  disc(ctx,236,48,402,263,PAPER,.045);
  caption(ctx,'КРУПНЫЙ ПЛАН',46,140);
  text(ctx,'НАМОТКА',41,237,100,INK);
  ctx.beginPath(); ctx.ellipse(420,557,302,262,.09,.39,2.18);
  ctx.strokeStyle=PINK;ctx.lineWidth=4;ctx.stroke();
}
function listed(ctx,t) {
  fill(ctx,TEAL);
  const a=move(t/4), y=586;
  disc(ctx,277,y+8,311,205,PINK,.055);
  through(ctx,277,y,310,204,.055,()=>image(ctx,'cases',[-42,376,638,424],{focusX:.52,focusY:.46,zoom:1+.045*a}));
  strand(ctx,.84+.17*a,279,y,318,222,PINK,{width:3.2,phase:-.14});
  caption(ctx,'ДЛИНА ПО КАРТОЧКЕ',46,142,PAPER);
  text(ctx,DETAILS.fromCard,40,288,141,PAPER);
}
function label(ctx,t) {
  fill(ctx,PAPER);
  const a=move(t/4.6);
  disc(ctx,285,502,245,148,'#12473b13',.03);
  strand(ctx,.87+.18*a,287,498,248,154,BERRY,{width:3.8});
  labelStrip(ctx,'length',29+9*a,454-5*a,479,-.053+.010*a);
  caption(ctx,'НА ЭТИКЕТКЕ ОДНОЙ КАТУШКИ',46,141);
  text(ctx,DETAILS.fromLabel,40,280,128,BERRY);
  caption(ctx,'В КАРТОЧКЕ',46,738);
  text(ctx,DETAILS.fromCard,43,803,60,INK);
}

const scenes={ hero,type,diameter,winding,listed,label };
const paint=(ctx,{kind,start},time)=>scenes[kind](ctx,Math.max(0,time-start));
function loopCut(ctx,t,draw) {
  // Expand the contour of the reel into the next image, on the beat.
  if (t<=0) return;
  const r=780*move(t/WIPE), x=288, y=552;
  through(ctx,x,y,r,r*.95,.13,draw);
  oval(ctx,x,y,r+2,r*.95+2,.13);
  ctx.strokeStyle=BERRY;ctx.lineWidth=4.2;ctx.stroke();
}
export function createFilm(scale=1) {
  const canvas=createCanvas(Math.round(W*scale),Math.round(H*scale));
  const ctx=canvas.getContext('2d');
  ctx.scale(canvas.width/W,canvas.height/H);
  ctx.imageSmoothingQuality='high';
  const texture=ctx.createPattern(grain,'repeat');
  const finish=()=>{ fill(ctx,texture); return canvas; };
  function draw(seconds) {
    const now=clamp(seconds,0,DURATION);
    const i=SHOTS.findLastIndex(({ start })=>now>=start), shot=SHOTS[i], local=now-shot.start;
    if (i && local<WIPE) {
      paint(ctx,SHOTS[i-1],shot.start);
      loopCut(ctx,local,()=>paint(ctx,shot,now));
    } else paint(ctx,shot,now);
    return finish();
  }
  function drawCover(){ hero(ctx,1.83,true); return finish(); }
  return { canvas,draw,drawCover };
}
