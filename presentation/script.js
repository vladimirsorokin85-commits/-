/* ============================================================
   НАВИГАЦИЯ ПРЕЗЕНТАЦИИ + ГРАФИК
   ============================================================ */

const TOTAL = 14;
let current = 0;

const deck = document.getElementById('deck');
const slides = document.querySelectorAll('.slide');
const navItems = document.querySelectorAll('.nav-item');
const progressFill = document.querySelector('.progress-fill');

function updateSlide(index) {
  if (index < 0) index = 0;
  if (index >= TOTAL) index = TOTAL - 1;
  current = index;

  slides.forEach((s, i) => {
    s.classList.toggle('active', i === current);
  });

  navItems.forEach((n, i) => {
    n.classList.toggle('active', i === current);
  });

  const pct = ((current + 1) / TOTAL) * 100;
  progressFill.style.width = pct + '%';

  // Запуск анимации графика только на слайде с метриками
  if (current === 8 && window.metricsChart) {
    window.metricsChart.update();
  }
}

function goToSlide(index) {
  updateSlide(index);
}

// Клавиатура
document.addEventListener('keydown', (e) => {
  if (e.key === 'ArrowRight' || e.key === 'PageDown' || e.key === ' ') {
    e.preventDefault();
    goToSlide(current + 1);
  } else if (e.key === 'ArrowLeft' || e.key === 'PageUp') {
    goToSlide(current - 1);
  }
});

// Колесико мыши с задержкой (опционально, чтобы не листать слишком быстро)
let wheelTimeout;
document.addEventListener('wheel', (e) => {
  clearTimeout(wheelTimeout);
  wheelTimeout = setTimeout(() => {
    if (e.deltaY > 0) goToSlide(current + 1);
    else goToSlide(current - 1);
  }, 120);
}, { passive: true });

// Инициализация графика на слайде метрик
function initMetricsChart() {
  const ctx = document.getElementById('metricsChart');
  if (!ctx) return;
  window.metricsChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: ['CTR Shorts', 'Удержание Shorts', 'CTR длинное', 'Досмотр длинное'],
      datasets: [{
        label: 'Цель / Текущий уровень',
        data: [6, 70, 5, 40],
        backgroundColor: [
          'rgba(245,158,11,0.7)',
          'rgba(107,142,35,0.7)',
          'rgba(245,158,11,0.7)',
          'rgba(107,142,35,0.7)'
        ],
        borderColor: [
          'rgba(245,158,11,1)',
          'rgba(107,142,35,1)',
          'rgba(245,158,11,1)',
          'rgba(107,142,35,1)'
        ],
        borderWidth: 1,
        borderRadius: 6
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        title: {
          display: true,
          text: 'Целевые метрики YouTube (в %)',
          color: '#e8e8e8',
          font: { size: 14, family: 'Inter' }
        }
      },
      scales: {
        y: {
          beginAtZero: true,
          max: 100,
          ticks: { color: '#9aa3a6', font: { size: 12 } },
          grid: { color: '#2a3332' }
        },
        x: {
          ticks: { color: '#9aa3a6', font: { size: 12 } },
          grid: { display: false }
        }
      },
      animation: {
        duration: 1200,
        easing: 'easeOutQuart'
      }
    }
  });
}

// Запуск
updateSlide(0);
initMetricsChart();

/* Фильтрация таблицы тем */
function filterTopics(btn, filter) {
  document.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
  btn.classList.add('active');
  const rows = document.querySelectorAll('#topics-table tbody tr');
  rows.forEach(row => {
    const fmt = row.children[2].textContent.toLowerCase();
    let show = false;
    if (filter === 'all') show = true;
    else if (filter === 'shorts') show = fmt.includes('shorts');
    else if (filter === 'long') show = fmt.includes('длинное');
    else if (filter === 'hybrid') show = fmt.includes('оба') || fmt.includes('shorts') && fmt.includes('длинное');
    row.style.display = show ? '' : 'none';
  });
}
