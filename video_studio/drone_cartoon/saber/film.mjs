import { createCanvas, GlobalFonts, loadImage } from '@napi-rs/canvas';
import { fileURLToPath } from 'node:url';
import { DURATION, FRAME_COLORS, LENSES, PACKSHOT, PHOTOS, SHOTS, WIPE } from './story.mjs';

export const WIDTH = 540;
export const HEIGHT = 960;
const W = WIDTH, H = HEIGHT;
const PAPER = '#f4ecda', INK = '#352047', PLUM = '#4b2e60', RED = '#bf4127', RUST = '#e86b36';
const LILAC = '#d4bbdf', PEACH = '#fae2c9';
const photos = Object.fromEntries(await Promise.all(PHOTOS.map(async key => [
  key, await loadImage(fileURLToPath(new URL(`./assets/${key}.jpg`, import.meta.url))),
])));
for (const kind of ['Black', 'Medium']) {
  const path = fileURLToPath(new URL(`../../fonts/Roboto-${kind}.woff`, import.meta.url));
  if (!GlobalFonts.registerFromPath(path, `Saber${kind}`)) throw new Error(`Не загружен шрифт: ${kind}`);
}
const clamp = (v, min, max) => Math.min(max, Math.max(min,v));
const ease = (v) => { const a = clamp(v,0,1); return a*a*(3-2*a); };
function fill(c,tone,x=0,y=0,w=W,h=H) { c.fillStyle=tone; c.fillRect(x,y,w,h); }
function text(c,value,x,y,px,tone,{ max=448, face='Black' }={}) {
  c.save(); c.translate(x,y); c.font=`${px}px Saber${face}`; c.textBaseline='alphabetic';
  c.scale(Math.min(1,max/c.measureText(value).width),1);
  c.fillStyle=tone; c.fillText(value,0,0); c.restore();
}
function caption(c,value,x,y,tone=INK) {
  c.font='17px SaberMedium'; c.textBaseline='alphabetic'; c.fillStyle=tone;
  for(const ch of value) { c.fillText(ch,x,y); x+=c.measureText(ch).width+1.55; }
}
function photo(c,name,[x,y,w,h],src=[0,0,1,1],{ zoom=1, contain=false }={}) {
  const im=photos[name]; let [sx,sy,sw,sh]=src.map((u,i)=>u*(i%2?im.height:im.width));
  if (contain) {
    const s=Math.min(w/sw,h/sh);
    c.drawImage(im,sx,sy,sw,sh,x+(w-sw*s)/2,y+(h-sh*s)/2,sw*s,sh*s);
    return;
  }
  const a=w/h;
  if(sw/sh>a) { const nw=sh*a; sx+=(sw-nw)/2; sw=nw; }
  else { const nh=sw/a; sy+=(sh-nh)/2; sh=nh; }
  sx+=sw*(1-1/zoom)/2; sy+=sh*(1-1/zoom)/2; sw/=zoom; sh/=zoom;
  c.drawImage(im,sx,sy,sw,sh,x,y,w,h);
}

// This contour follows the broad brow, rounded corners and nose notch of the real lens.
function visor(c,x,y,w,h) {
  const pt=(u,v)=>[x+u*w,y+v*h];
  const curve=(a,b,d,e,f,g)=>c.bezierCurveTo(...pt(a,b),...pt(d,e),...pt(f,g));
  c.beginPath(); c.moveTo(...pt(.016,.52));
  curve(.011,.23,.13,.096,.27,.06);
  curve(.408,.008,.55,.002,.69,.064);
  curve(.83,.105,.965,.23,.987,.47);
  curve(1.012,.64,.994,.836,.94,.914);
  curve(.881,1,.744,.994,.648,.964);
  curve(.597,.945,.581,.886,.556,.784);
  curve(.53,.67,.53,.51,.5,.49);
  curve(.459,.479,.444,.661,.419,.766);
  curve(.394,.872,.379,.937,.329,.963);
  curve(.241,1,.111,1,.056,.926);
  curve(.014,.849,.006,.667,.016,.52);
  c.closePath();
}
function inkVisor(c,x,y,w,h,tone) { visor(c,x,y,w,h); c.fillStyle=tone; c.fill(); }
function outline(c,x,y,w,h,tone,width=2.5) { visor(c,x,y,w,h); c.strokeStyle=tone; c.lineWidth=width; c.stroke(); }
function through(c,x,y,w,h,draw) { c.save(); visor(c,x,y,w,h); c.clip(); draw(); c.restore(); }
function heading(c,tag,title,{ dark=false, size=81, color=dark?PAPER:INK, max=448 }={}) {
  caption(c,tag,46,138,dark?LILAC:INK);
  text(c,title,41,236,size,color,{max});
}
function grain() {
  const tile=createCanvas(193,207),ctx=tile.getContext('2d'),data=ctx.createImageData(tile.width,tile.height);
  let seed=4387414;
  for(let i=0;i<data.data.length;i+=4) {
    seed=(Math.imul(1664525,seed)+1013904223)>>>0;
    const n=seed>>>24,light=n>121;
    data.data[i]=light?253:45;data.data[i+1]=light?240:26;data.data[i+2]=light?217:61;
    data.data[i+3]=n%10+(n<16?12:0);
  }
  ctx.putImageData(data,0,0);return tile;
}
const stock=grain();

function hero(c,t,cover=false) {
  fill(c,PAPER);
  const a=cover?.72:ease(t/2.8);
  inkVisor(c,-66,421,665,451,RED);
  inkVisor(c,-73,413,665,451,PLUM);
  photo(c,'olive',[26,398-11*a,487,455],[0,0,1,1],{zoom:1+.045*a,contain:false});
  outline(c,17,393-11*a,506,466,INK,2.5);
  caption(c,'НА СКЛАДЕ  /  WILEY X',46,134);
  text(c,'SABER',40,258,142,INK);
  text(c,'ADVANCED',40,349,94,RED);
}
function stack(c,t) {
  fill(c,INK);
  const a=ease(t/2.6);
  const x=136-8*a,y=279,w=382,h=499;
  fill(c,RUST,x+6,y+7,w,h);
  photo(c,'stack',[x,y,w,h],[0,0,1,1],{zoom:1+.04*a});
  heading(c,'СО СКЛАДА','Wiley X',{dark:true,size:117});
  text(c,'Saber Advanced',44,827,33,PAPER,{face:'Medium'});
}
function colors(c,t) {
  fill(c,PAPER);
  text(c,'Три оправы',41,217,90,INK);
  const samples=[['black',[.225,.028,.775,.365],'#332b3d'],['olive',[.245,.037,.724,.367],'#747d53'],['tan',[.111,.105,.600,.224],'#c9b782']];
  const a=ease(t/3.5);
  samples.forEach(([name,src,ink],i)=>{
    const y=297+i*167;
    inkVisor(c,189,y+6,349,153,ink);
    through(c,183,y,349,153,()=>photo(c,name,[180,y,361,154],src,{zoom:1+.06*a}));
    outline(c,183,y,349,153,INK,1.65);
    text(c,FRAME_COLORS[i],44,y+81,36,INK,{max:139,face:'Medium'});
  });
}
function box(c,t) {
  fill(c,PLUM);
  const a=ease(t/3.1);
  heading(c,'ОДИН ИЗ КОМПЛЕКТОВ','Упаковка',{dark:true,size:104});
  inkVisor(c,-45,353,638,391,RUST);
  photo(c,'box',[22,383-7*a,494,287],[0,0,1,1],{zoom:1+.035*a});
  caption(c,'СМЕННЫЕ ЛИНЗЫ',45,767,PAPER);
}
function lenses(c,t) {
  fill(c,PAPER);
  heading(c,'SABER ADVANCED','Три линзы',{size:95});
  const a=ease(t/2.3);
  inkVisor(c,-81,343,705,467,'#d7c2de');
  photo(c,'tan',[42,290-9*a,344,532],[.106,.096,.598,.774],{contain:true});
  // The printed count is a crop from a different face-on photo of the real box.
  photo(c,'label',[394,609,95,110],[.797,.183,.113,.191],{contain:true});
}
const LENS_CROPS={ clear:[.125,.616,.575,.243], smoke:[.116,.211,.594,.174], rust:[.138,.389,.551,.224] };
const LENS_INKS={ clear:[PAPER,'#d9c9e4',INK,INK], smoke:[INK,PLUM,PAPER,LILAC], rust:[PEACH,RUST,INK,RED] };
function lens(c,t,name) {
  const a=ease(t/3), [bg,mark,ink,sub]=LENS_INKS[name], {name:label,title,note}=LENSES[name];
  fill(c,bg);
  inkVisor(c,2,361,542,346,name==='smoke'?RUST:RED);
  inkVisor(c,-5,349,542,346,mark);
  // Keep the lens photograph unfiltered. The two inks behind it are a print motif, not an optical comparison.
  photo(c,'tan',[28,417-10*a,481,223],LENS_CROPS[name],{contain:true});
  outline(c,-4,350,541,348,name==='smoke'?LILAC:INK,2.4);
  caption(c,label.toUpperCase(),46,139,sub);
  text(c,title,41,239,90,ink);
  text(c,note,44,782,32,ink,{face:'Medium'});
}
function profile(c,t) {
  fill(c,PLUM);
  heading(c,'ПОСАДКА','Широкая линза',{dark:true,size:83});
  const a=ease(t/4.4);
  inkVisor(c,-82,394,698,409,RUST);
  photo(c,'black',[27,330-9*a,484,465],[0,0,1,1],{zoom:1+.063*a});
  text(c,'Изогнута по бокам',45,837,36,PAPER,{face:'Medium'});
}
function arm(c,t) {
  fill(c,PAPER);
  heading(c,'ПОСАДКА','Дужки',{size:111});
  text(c,'Регулируются по длине',45,298,35,INK,{face:'Medium'});
  const a=ease(t/2.6);
  inkVisor(c,-72,419,684,368,'#d9c1dd');
  photo(c,'olive',[27,411-8*a,488,331],[.205,.012,.794,.446],{zoom:1+.069*a});
  outline(c,10,389,523,388,RED,2.8);
}
function nose(c,t) {
  fill(c,PEACH);
  heading(c,'ПОСАДКА','Носовой упор',{size:84});
  text(c,'Гибкий, можно подогнать',45,295,31,INK,{face:'Medium'});
  const a=ease(t/3.4);
  inkVisor(c,-57,391,661,388,RUST);
  photo(c,'tan',[35,409-7*a,471,343],[.281,.259,.262,.137],{zoom:1+.065*a});
  outline(c,17,383,507,396,INK,2.35);
}
function extras(c,t) {
  fill(c,PAPER);
  heading(c,'ЧТО В КОМПЛЕКТЕ','Ремешок',{size:109});
  text(c,'и салфетка',45,311,68,RED);
  const a=ease(t/3.7);
  inkVisor(c,-72,410,692,402,'#e0cbde');
  photo(c,'tan',[41,357,133,440],[.001,.302,.12,.488],{contain:true});
  photo(c,'tan',[202,385-9*a,292,408],[.715,.264,.272,.409],{contain:true});
}
function caseView(c,t) {
  fill(c,INK);
  heading(c,'ЧТО В КОМПЛЕКТЕ','Футляр',{dark:true,size:113});
  text(c,'Молния по краю',46,298,34,PAPER,{face:'Medium'});
  const a=ease(t/2.6);
  inkVisor(c,-50,432,653,380,RED);
  photo(c,'case',[62+7*a,346,417,505],[0,0,1,1],{contain:true});
}
function clasp(c,t) {
  fill(c,PAPER);
  heading(c,'ДЕТАЛЬ ФУТЛЯРА','Карабин',{size:108});
  const a=ease(t/2.04);
  inkVisor(c,-66,402,684,392,PLUM);
  photo(c,'case',[53,363-5*a,432,464],[.021,.703,.346,.296],{contain:true});
}
function full(c,t) {
  fill(c,PAPER);
  text(c,'Весь набор',41,229,91,INK);
  const a=ease(t/2.07);
  inkVisor(c,-70,393,683,478,'#d6c2df');
  photo(c,'tan',[32,303-5*a,474,434],[.001,.099,.989,.757],{contain:true});
  photo(c,'case',[321,652,184,183],[0,0,1,1],{contain:true});
}
function packshot(c,t) {
  fill(c,PAPER);
  const a=ease(t/3.8);
  caption(c,'WILEY X SABER ADVANCED',46,139);
  text(c,PACKSHOT.lines[0],44,224,61,INK);
  text(c,PACKSHOT.lines[1],43,309,78,RED);
  inkVisor(c,-60,395,662,444,RED); inkVisor(c,-67,386,662,444,INK);
  photo(c,'olive',[29,418-7*a,482,252],[.132,.017,.864,.495]);
  fill(c,PEACH,183,673,328,163);
  photo(c,'group',[187,677,320,155],[0,0,1,1],{zoom:1});
}
const scene={hero,stack,colors,box,lenses,clear:(c,t)=>lens(c,t,'clear'),smoke:(c,t)=>lens(c,t,'smoke'),
  rust:(c,t)=>lens(c,t,'rust'),profile,arm,nose,extras,case:caseView,clasp,full,packshot};
const paint=(c,{kind,start},time)=>scene[kind](c,Math.max(0,time-start));
function transition(c,t,draw) {
  if(t<=0)return;
  const p=ease(t/WIPE);
  const w=2500*p,h=2900*p,x=274-w*.50,y=521-h*.279;
  // The same rounded lens opens over the previous shot; the aperture never represents a view through the lens.
  through(c,x,y,w,h,draw);
  outline(c,x,y,w,h,RUST,4.6);
}
export function createFilm(scale=1) {
  const canvas=createCanvas(Math.round(W*scale),Math.round(H*scale)),ctx=canvas.getContext('2d');
  ctx.scale(canvas.width/W,canvas.height/H);ctx.imageSmoothingQuality='high';
  const grain=ctx.createPattern(stock,'repeat');
  const finish=()=>{fill(ctx,grain);return canvas;};
  function draw(seconds) {
    const now=clamp(seconds,0,DURATION), i=SHOTS.findLastIndex(({start})=>now>=start), shot=SHOTS[i], local=now-shot.start;
    if(i&&local<WIPE) {paint(ctx,SHOTS[i-1],shot.start);transition(ctx,local,()=>paint(ctx,shot,now));}
    else paint(ctx,shot,now);
    return finish();
  }
  function drawCover(){hero(ctx,1.75,true);return finish();}
  return {canvas,draw,drawCover};
}
