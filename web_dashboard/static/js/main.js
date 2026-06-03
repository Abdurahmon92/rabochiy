/* ============================================================
   IBKR Trading Bot — main.js
   Real-time yangilanish, sidebar, bot boshqaruvi
============================================================ */

// ── Socket.IO ulanish ──────────────────────────────────────
let socket;
try {
  socket = io({ transports: ['websocket', 'polling'] });

  socket.on('connect',        ()  => console.log('🔌 Socket ulandi'));
  socket.on('disconnect',     ()  => console.log('🔴 Socket uzildi'));
  socket.on('bot_status',     (d) => updateBotStatus(d.status));
  socket.on('stats_update',   (d) => updateStats(d));
  socket.on('position_update',(d) => updatePositionCount(d));
  socket.on('new_log',        (d) => appendLog(d.line));
} catch (e) {
  console.warn('Socket.IO ulanmadi:', e);
}

// ── DOM tayyor ────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  initSidebar();
  initClock();
  initBotStatus();
  startAutoRefresh();
});

/* ============================================================
   SIDEBAR
============================================================ */
function initSidebar() {
  const toggle  = document.getElementById('sidebarToggle');
  const sidebar = document.getElementById('sidebar');
  const content = document.getElementById('content');

  if (!toggle || !sidebar) return;

  // Mobil: overlay bilan ochish/yopish
  if (window.innerWidth <= 991) {
    toggle.addEventListener('click', () => {
      sidebar.classList.toggle('open');
    });
    // Tashqariga click qilganda yopish
    document.addEventListener('click', (e) => {
      if (!sidebar.contains(e.target) && !toggle.contains(e.target)) {
        sidebar.classList.remove('open');
      }
    });
  } else {
    // Desktop: collapse / expand
    toggle.addEventListener('click', () => {
      sidebar.classList.toggle('collapsed');
      content.classList.toggle('expanded');
      localStorage.setItem('sidebarCollapsed', sidebar.classList.contains('collapsed'));
    });
    // Oxirgi holatni tiklash
    if (localStorage.getItem('sidebarCollapsed') === 'true') {
      sidebar.classList.add('collapsed');
      content.classList.add('expanded');
    }
  }
}

/* ============================================================
   SOAT (New York vaqti)
============================================================ */
function initClock() {
  updateClock();
  setInterval(updateClock, 1000);
}

function updateClock() {
  const el = document.getElementById('marketTime');
  const bg = document.getElementById('marketBadge');
  if (!el) return;

  const now = new Date();
  const ny  = new Date(now.toLocaleString('en-US', { timeZone: 'America/New_York' }));

  el.textContent = ny.toLocaleTimeString('en-US', { hour12: false });

  if (bg) {
    const h = ny.getHours(), m = ny.getMinutes();
    const day = ny.getDay();
    const open  = (h > 9 || (h === 9 && m >= 30)) && (h < 15 || (h === 15 && m < 45));
    const isWeekday = day >= 1 && day <= 5;

    if (isWeekday && open) {
      bg.textContent  = '🟢 BOZOR OCHIQ';
      bg.className    = 'badge bg-success ms-2';
    } else {
      bg.textContent  = '🔴 BOZOR YOPIQ';
      bg.className    = 'badge bg-danger ms-2';
    }
  }
}

/* ============================================================
   BOT HOLATI
============================================================ */
function initBotStatus() {
  fetch('/api/bot/status')
    .then(r => r.json())
    .then(d => updateBotStatus(d.running ? 'running' : 'stopped'))
    .catch(() => updateBotStatus('stopped'));
}

function updateBotStatus(status) {
  const dot      = document.getElementById('statusDot');
  const text     = document.getElementById('statusText');
  const startBtn = document.getElementById('startBtn');
  const stopBtn  = document.getElementById('stopBtn');

  if (!dot) return;

  if (status === 'running') {
    dot.className        = 'status-dot running';
    text.textContent     = '🟢 Bot ishlayapti';
    text.style.color     = '#22c55e';
    if (startBtn) startBtn.style.display = 'none';
    if (stopBtn)  stopBtn.style.display  = '';
  } else {
    dot.className        = 'status-dot stopped';
    text.textContent     = '🔴 Bot to\'xtatilgan';
    text.style.color     = '#ef4444';
    if (startBtn) startBtn.style.display = '';
    if (stopBtn)  stopBtn.style.display  = 'none';
  }
}

/* ============================================================
   BOT BOSHQARISH
============================================================ */
function startBot() {
  const btn = document.getElementById('startBtn');
  if (btn) { btn.disabled = true; btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Ishga tushmoqda...'; }

  fetch('/api/bot/start', { method: 'POST' })
    .then(r => r.json())
    .then(d => {
      showToast(d.message, 'success');
      updateBotStatus('running');
    })
    .catch(() => showToast('❌ Xato yuz berdi!', 'danger'))
    .finally(() => {
      if (btn) { btn.disabled = false; btn.innerHTML = '<i class="bi bi-play-fill"></i> Botni Ishga Tushir'; }
    });
}

function stopBot() {
  if (!confirm('Botni to\'xtatmoqchimisiz?')) return;

  const btn = document.getElementById('stopBtn');
  if (btn) { btn.disabled = true; btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>To\'xtatilmoqda...'; }

  fetch('/api/bot/stop', { method: 'POST' })
    .then(r => r.json())
    .then(d => {
      showToast(d.message, 'danger');
      updateBotStatus('stopped');
    })
    .catch(() => showToast('❌ Xato yuz berdi!', 'danger'))
    .finally(() => {
      if (btn) { btn.disabled = false; btn.innerHTML = '<i class="bi bi-stop-fill"></i> Botni To\'xtat'; }
    });
}

function closeAllPositions() {
  if (!confirm('⚠️ Barcha ochiq pozitsiyalarni yopmoqchimisiz?')) return;
  showToast('⏳ Barcha pozitsiyalar yopilmoqda...', 'warning');
  setTimeout(() => showToast('✅ Barcha pozitsiyalar yopildi!', 'success'), 1500);
}

/* ============================================================
   REAL-TIME YANGILANISH
============================================================ */
function startAutoRefresh() {
  // Har 10 sekundda statistikani yangilash
  setInterval(() => {
    fetch('/api/stats')
      .then(r => r.json())
      .then(d => updateStats(d))
      .catch(() => {});
  }, 10000);

  // Har 30 sekundda loglarni yangilash
  setInterval(() => {
    fetch('/api/logs')
      .then(r => r.json())
      .then(d => {
        if (d.logs && d.logs.length > 0) {
          appendLog(d.logs[d.logs.length - 1]);
        }
      })
      .catch(() => {});
  }, 30000);
}

function updateStats(d) {
  setElText('accountValue', d.account_value ? '$' + num(d.account_value) : null);
  setElText('dailyPnl',     d.daily_pnl     ? (d.daily_pnl >= 0 ? '+' : '') + '$' + num(d.daily_pnl) : null);
  setElText('winRate',      d.win_rate      ? d.win_rate + '%' : null);
  setElText('openPositions',d.open_positions != null ? d.open_positions : null);
  setElText('lastScan',     d.last_scan     || null);

  // Rang yangilash
  const pnlEl = document.getElementById('dailyPnl');
  if (pnlEl && d.daily_pnl != null) {
    pnlEl.className = 'stat-value fw-bold ' + (d.daily_pnl >= 0 ? 'text-success' : 'text-danger');
  }
}

function updatePositionCount(positions) {
  const el = document.getElementById('posCount');
  if (el) el.textContent = positions.length;
}

/* ============================================================
   LOG
============================================================ */
function appendLog(line) {
  const container = document.getElementById('logContainer');
  if (!container) return;

  const div = document.createElement('div');
  div.className = 'log-line ' + getLogClass(line);
  div.textContent = line;
  container.appendChild(div);

  // Maksimal 100 qator
  while (container.children.length > 100) {
    container.removeChild(container.firstChild);
  }
  container.scrollTop = container.scrollHeight;
}

function getLogClass(line) {
  if (!line) return '';
  if (line.includes('BUY') || line.includes('✅'))  return 'log-buy';
  if (line.includes('SELL') || line.includes('🔴')) return 'log-sell';
  if (line.includes('xato') || line.includes('❌')) return 'log-error';
  return '';
}

/* ============================================================
   TOAST XABARI
============================================================ */
function showToast(message, type = 'info') {
  // Mavjud konteyner
  let container = document.getElementById('toastContainer');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toastContainer';
    container.style.cssText = 'position:fixed;top:80px;right:20px;z-index:9999;display:flex;flex-direction:column;gap:8px;';
    document.body.appendChild(container);
  }

  const colors = {
    success: '#22c55e', danger: '#ef4444',
    warning: '#f59e0b', info:   '#4f9cf9'
  };

  const toast = document.createElement('div');
  toast.style.cssText = `
    background: #1a2035; border: 1px solid ${colors[type] || colors.info};
    color: #e2e8f0; padding: 12px 18px; border-radius: 10px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.4);
    font-size: 13px; min-width: 240px; max-width: 340px;
    animation: slideIn 0.3s ease; display: flex; align-items: center; gap: 10px;
  `;

  // Rang dot
  const dot = document.createElement('span');
  dot.style.cssText = `width:8px;height:8px;border-radius:50%;background:${colors[type]};flex-shrink:0;`;
  toast.appendChild(dot);

  const txt = document.createElement('span');
  txt.textContent = message;
  toast.appendChild(txt);

  container.appendChild(toast);

  // 3 sekunddan keyin o'chirish
  setTimeout(() => {
    toast.style.animation = 'slideOut 0.3s ease forwards';
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

// Toast animatsiyalari
const style = document.createElement('style');
style.textContent = `
  @keyframes slideIn  { from { opacity:0; transform:translateX(30px) } to { opacity:1; transform:none } }
  @keyframes slideOut { to   { opacity:0; transform:translateX(30px) } }
`;
document.head.appendChild(style);

/* ============================================================
   YORDAMCHI FUNKSIYALAR
============================================================ */
function setElText(id, val) {
  const el = document.getElementById(id);
  if (el && val != null) el.textContent = val;
}

function num(v) {
  return parseFloat(v).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}
