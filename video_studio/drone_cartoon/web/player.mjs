import { CHAPTERS, CONTACTS, DURATION, FPS, WIPE, chapterAt } from './story.mjs';

const video = document.querySelector('#film');
const watch = document.querySelector('#watch');
const watchLabel = document.querySelector('#watch-label');
const status = document.querySelector('#status');
const chapters = document.querySelector('#chapters');
const transcript = document.querySelector('#transcript');
const contacts = document.querySelector('#contacts');
for (const { href, label } of CONTACTS) {
  const link = document.createElement('a');
  link.href = href;
  link.target = '_blank';
  link.rel = 'noopener noreferrer';
  link.textContent = label;
  contacts.append(link);
}
const formatTime = (seconds) => {
  const mm = String(Math.floor(seconds / 60)).padStart(2, '0');
  const ss = String(Math.floor(seconds % 60)).padStart(2, '0');
  return `${mm}:${ss}`;
};
function message(text) {
  status.textContent = text;
  status.hidden = !text;
}
function play() {
  message('');
  video.play().catch((error) => {
    if (error.name !== 'AbortError') message('Не удалось запустить плеер. Попробуйте скачать MP4.');
  });
}
function bringPlayerIntoView() {
  const box = video.getBoundingClientRect();
  if (box.top < 0 || box.bottom > innerHeight) {
    video.scrollIntoView({ block: 'nearest', behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth' });
  }
}
watch.addEventListener('click', () => {
  if (!video.paused) { video.pause(); return; }
  bringPlayerIntoView();
  play();
});
const buttons = CHAPTERS.map(({ start, label, heading, narration }, index) => {
  const item = document.createElement('li');
  const button = document.createElement('button');
  button.type = 'button';
  button.className = 'chapter';
  button.disabled = video.readyState === 0;
  const stamp = document.createElement('time');
  stamp.dateTime = `PT${start}S`;
  stamp.textContent = formatTime(start);
  button.append(stamp, document.createTextNode(label));
  item.append(button);
  chapters.append(item);
  button.addEventListener('click', () => {
    bringPlayerIntoView();
    video.currentTime = start + (index ? WIPE + .02 : 0);
    play();
  });
  const line = document.createElement('p');
  const intro = document.createElement('strong');
  intro.textContent = `${formatTime(start)} · ${heading.join(' ')}`;
  line.append(intro, document.createElement('br'), document.createTextNode(narration));
  transcript.append(line);
  return button;
});
function refresh() {
  const i = chapterAt(video.currentTime);
  buttons.forEach((button, index) => {
    if (i === index) button.setAttribute('aria-current', 'true');
    else button.removeAttribute('aria-current');
  });
  watchLabel.textContent = video.ended ? 'Смотреть снова' : video.paused ? 'Смотреть' : 'Пауза';
}
function unavailable() {
  watch.disabled = true;
  buttons.forEach((button) => { button.disabled = true; });
  message('Плеер не загрузил видео. Если файл собран, его можно скачать в MP4.');
}
video.addEventListener('loadedmetadata', () => {
  buttons.forEach((button) => { button.disabled = false; });
});
for (const event of ['timeupdate', 'seeking', 'play', 'pause', 'ended']) video.addEventListener(event, refresh);
video.addEventListener('error', unavailable);
video.querySelector('source')?.addEventListener('error', unavailable);
if (video.error || video.networkState === video.NETWORK_NO_SOURCE) unavailable();
document.querySelector('#running-time').textContent = formatTime(DURATION);
document.querySelector('#frame-rate').textContent = `${FPS} кадров/с`;
document.querySelector('#count').textContent = String(CHAPTERS.length).padStart(2, '0');
refresh();
