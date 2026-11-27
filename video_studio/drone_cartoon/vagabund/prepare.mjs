import { createCanvas, loadImage } from '@napi-rs/canvas';
import { mkdir, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';

const inputs = [['01.jpg', 'pair'], ['02.jpg', 'angle'], ['03.jpg', 'profile']];
const source = process.argv[2];
if (!source) throw new Error('Использование: node vagabund/prepare.mjs <папка с 01.jpg, 02.jpg и 03.jpg>');
const target = new URL('./assets/', import.meta.url);
await mkdir(target, { recursive: true });

// The inserted diagram in 02.jpg is a separate component; retain only the boot.
function isolate(image) {
  const { width: w, height: h } = image;
  const sheet = createCanvas(w,h), ctx = sheet.getContext('2d');
  ctx.drawImage(image,0,0);
  const src = ctx.getImageData(0,0,w,h).data;
  const labels = new Uint32Array(w*h), queue = new Int32Array(w*h);
  const dark = p => 255 - Math.min(src[p*4],src[p*4+1],src[p*4+2]);
  let id=0,best=0,maximum=0;
  for (let p=0;p<labels.length;p++) {
    if (labels[p] || dark(p)<26) continue;
    let n=1; labels[p]=++id; queue[0]=p;
    for(let i=0;i<n;i++) {
      const at=queue[i], x=at%w, y=Math.floor(at/w);
      for(let dy=-1;dy<=1;dy++)for(let dx=-1;dx<=1;dx++){
        const xx=x+dx, yy=y+dy, q=yy*w+xx;
        if(xx<0||yy<0||xx>=w||yy>=h||labels[q]||dark(q)<26)continue;
        labels[q]=id;queue[n++]=q;
      }
    }
    if(n>maximum){maximum=n;best=id;}
  }
  if(maximum<w*h*.1)throw new Error('Не удалось выделить обувь на светлом фоне');
  let x0=w,y0=h,x1=0,y1=0;
  for(let i=0;i<labels.length;i++)if(labels[i]===best){
    const x=i%w,y=Math.floor(i/w);x0=Math.min(x,x0);x1=Math.max(x,x1);y0=Math.min(y,y0);y1=Math.max(y,y1);
  }
  const padding=5;
  x0=Math.max(0,x0-padding);y0=Math.max(0,y0-padding);x1=Math.min(w-1,x1+padding);y1=Math.min(h-1,y1+padding);
  const cropped=createCanvas(x1-x0+1,y1-y0+1), out=cropped.getContext('2d'), rgba=out.createImageData(cropped.width,cropped.height);
  for(let y=y0;y<=y1;y++)for(let x=x0;x<=x1;x++){
    const p=y*w+x,d=dark(p);
    if(d<4)continue;
    let strongest=0, fringe=labels[p]!==best;
    for(let dy=-2;dy<=2;dy++)for(let dx=-2;dx<=2;dx++){
      const xx=x+dx,yy=y+dy;
      if(xx<0||yy<0||xx>=w||yy>=h)continue;
      const q=yy*w+xx;
      if(labels[q]===best)strongest=Math.max(strongest,dark(q));
      else fringe=true;
    }
    if(!strongest)continue;
    const a=fringe?Math.min(1,d/strongest):1;
    const at=((y-y0)*cropped.width+x-x0)*4;
    for(let ch=0;ch<3;ch++)rgba.data[at+ch]=255-(255-src[p*4+ch])/a;
    rgba.data[at+3]=Math.round(a*255);
  }
  out.putImageData(rgba,0,0);
  return cropped;
}

for(const [name,key] of inputs){
  const image=await loadImage(resolve(source,name));
  const crop=isolate(image);
  await writeFile(new URL(`${key}.png`,target),crop.toBuffer('image/png'));
  console.log(`${name} -> ${key}.png (${crop.width} x ${crop.height})`);
}
