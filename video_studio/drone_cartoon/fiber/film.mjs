import { createCanvas, GlobalFonts, loadImage } from '@napi-rs/canvas';
import { fileURLToPath } from 'node:url';
import { DURATION, MODEL, SHOTS, WIPE } from './story.mjs';

export const WIDTH = 540;
export const HEIGHT = 960;
const W = WIDTH, H = HEIGHT, TAU = Math.PI * 2;
const PAPER = '#f1ecde', INK = '#153f36', TEAL = '#0d5e51', BERRY = '#a62559', PINK = '#f2a2b7';
const files = { rim: 'rim.png', open: 'open.jpg', winding: 'winding.jpg', cases: 'cases.jpg', type: 'type.jpg' };
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
  caption(ctx,'ЧТО У НАС НА СКЛАДЕ',46,135);
  text(ctx,'ОПТОВОЛОКНО',42,226,89,INK,448);
  text(ctx,MODEL,41,335,109,BERRY);
  caption(ctx,'ПРОЗРАЧНОЕ ВОЛОКНО',47,837);
}
function packed(ctx,t) {
  fill(ctx,TEAL);
  const a=move(t/4.2);
  disc(ctx,268,562,316,240,PINK,.055);
  through(ctx,270,555,316,240,.055,()=>image(ctx,'cases',[-49,311,638,488],{focusX:.51,focusY:.47,zoom:1+.045*a}));
  strand(ctx,.90+.13*a,267,555,323,250,PINK,{width:3,phase:-.12,tail:64});
  text(ctx,'В футлярах',44,229,86,PAPER);
}
function open(ctx,t) {
  fill(ctx,PAPER);
  const a=move(t/5.4);
  disc(ctx,308,572,302,258,BERRY,-.10);
  through(ctx,310,562,301,256,-.10,()=>image(ctx,'open',[-32,288,685,552],{
    focusX:.58+.026*a,focusY:.46,zoom:1+.113*a,
  }));
  strand(ctx,.88+.16*a,313,565,312,270,INK,{width:2.6,phase:-.09,tail:64});
  text(ctx,'Под плёнкой',44,227,83,INK);
}
function winding(ctx,t) {
  const a=move(t/4.4);
  image(ctx,'winding',[0,0,W,H],{focusX:.65+.027*a,focusY:.50,zoom:1.015+.104*a});
  disc(ctx,240,47,402,240,BERRY,.045);
  disc(ctx,236,36,402,240,PAPER,.045);
  text(ctx,'Виток к витку',43,207,70,INK);
  ctx.beginPath(); ctx.ellipse(420,557,302,262,.09,.39,2.18);
  ctx.strokeStyle=PINK;ctx.lineWidth=4;ctx.stroke();
}
function mark(ctx,t) {
  fill(ctx,PAPER);
  const a=move(t/4.1), photo=photos.rim;
  strand(ctx,.88+.17*a,350,603,231,195,BERRY,{width:3.7,tail:54});
  const width=407;
  ctx.drawImage(photo,172-10*a,439-11*a,width,width*photo.height/photo.width);
  labelStrip(ctx,'type',37+11*a,391-3*a,440,-.066+.015*a);
  text(ctx,'На этикетке',44,227,84,INK);
}
function end(ctx,t) {
  fill(ctx,TEAL);
  const a=move(t/4);
  disc(ctx,301,524,294,252,PINK,.09);
  through(ctx,301,515,294,252,.09,()=>image(ctx,'cases',[-18,250,627,535],{
    focusX:.62-.015*a,focusY:.51,zoom:1.065+.05*a,
  }));
  strand(ctx,.90+.15*a,300,519,308,261,PINK,{width:2.8,tail:47});
  caption(ctx,'ОПТОВОЛОКНО',46,151,PAPER);
  text(ctx,MODEL,42,832,75,PAPER);
}

const scenes={ hero,packed,open,winding,mark,end };
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
