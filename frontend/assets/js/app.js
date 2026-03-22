// Auth guard
(async () => {
  try {
    const r = await fetch('/auth/check');
    if (!r.ok) window.location.href = '/login';
  } catch {
    window.location.href = '/login';
  }
})();

// Navigation
const links = document.querySelectorAll('.nav-link');
const pages = document.querySelectorAll('.page');

function showPage(name) {
  links.forEach(l => l.classList.toggle('active', l.dataset.page === name));
  pages.forEach(p => p.classList.toggle('active', p.id === `page-${name}`));
  if (name === 'overview') { startLiveMetrics(); loadOverviewExtras(); }
  if (name === 'security') loadSecurity();
  if (name === 'history') loadHistory(24);
  if (name === 'reports') loadReports();
  if (name === 'events') loadAgentEvents();
}

links.forEach(l => l.addEventListener('click', e => {
  e.preventDefault();
  showPage(l.dataset.page);
}));

document.getElementById('logoutBtn').addEventListener('click', async () => {
  await fetch('/auth/logout', {method: 'POST'});
  window.location.href = '/login';
});

// ---- OVERVIEW ----
let liveInterval = null;

function fmtUptime(s) {
  const d = Math.floor(s / 86400), h = Math.floor((s % 86400) / 3600), m = Math.floor((s % 3600) / 60);
  return d > 0 ? `${d}d ${h}h` : h > 0 ? `${h}h ${m}m` : `${m}m`;
}

function setBar(cardId, pct) {
  const fill = document.querySelector(`#${cardId} .stat-bar-fill`);
  if (!fill) return;
  fill.style.width = pct + '%';
  fill.style.background = pct > 85 ? 'var(--red)' : pct > 65 ? 'var(--yellow)' : 'var(--accent)';
}

function updateLive(m) {
  const cpu = document.querySelector('#stat-cpu .stat-value');
  const ram = document.querySelector('#stat-ram .stat-value');
  const disk = document.querySelector('#stat-disk .stat-value');
  const temp = document.querySelector('#stat-temp .stat-value');
  const tempSub = document.querySelector('#stat-temp .stat-sub');
  const uptime = document.querySelector('#stat-uptime .stat-value');
  const load = document.querySelector('#stat-load .stat-value');
  const loadSub = document.querySelector('#stat-load .stat-sub');

  cpu.textContent = m.cpu_percent.toFixed(1) + '%';
  ram.textContent = m.ram_percent.toFixed(1) + '%';
  document.querySelector('#stat-ram .stat-sub') &&
    (document.querySelector('#stat-ram .stat-sub').textContent = `${m.ram_used_gb}/${m.ram_total_gb} GB`);
  disk.textContent = m.disk_percent.toFixed(1) + '%';
  document.querySelector('#stat-disk .stat-sub') &&
    (document.querySelector('#stat-disk .stat-sub').textContent = `${m.disk_used_gb}/${m.disk_total_gb} GB`);
  if (m.temp) {
    temp.textContent = m.temp + '°C';
    temp.style.color = m.temp > 75 ? 'var(--red)' : m.temp > 60 ? 'var(--yellow)' : 'var(--green)';
  }
  uptime.textContent = fmtUptime(m.uptime_seconds);
  load.textContent = m.load_1m;
  if (loadSub) loadSub.textContent = `5m: ${m.load_5m} · 15m: ${m.load_15m}`;

  setBar('stat-cpu', m.cpu_percent);
  setBar('stat-ram', m.ram_percent);
  setBar('stat-disk', m.disk_percent);
}

async function fetchLive() {
  try {
    const r = await fetch('/api/metrics/live');
    if (r.ok) updateLive(await r.json());
  } catch {}
}

function startLiveMetrics() {
  fetchLive();
  if (liveInterval) clearInterval(liveInterval);
  liveInterval = setInterval(fetchLive, 5000);
}

// ---- OVERVIEW EXTRAS ----
function extractActionItems(content) {
  return content.split('\n')
    .filter(l => l.includes('[ACTION NEEDED]'))
    .map(l => l.replace(/^[-*>\s]*/, '').trim());
}

async function loadOverviewExtras() {
  // Action items from latest report
  const rr = await fetch('/api/reports/');
  if (rr.ok) {
    const reports = await rr.json();
    const actionsEl = document.getElementById('overview-actions');
    if (reports.length) {
      const latest = await fetch(`/api/reports/${reports[0].id}`);
      const rep = await latest.json();
      const items = extractActionItems(rep.content);
      actionsEl.innerHTML = items.length
        ? items.map(i => `<div class="action-item">${marked.parseInline(i.replace('[ACTION NEEDED]', '').trim())}</div>`).join('')
        : '<p class="empty-msg">No open action items</p>';
    }
  }

  // Agent events
  const er = await fetch('/api/events/');
  if (er.ok) {
    const events = await er.json();
    const tbody = document.querySelector('#overview-events-table tbody');
    tbody.innerHTML = events.slice(0, 20).map(e =>
      `<tr><td>${new Date(e.timestamp).toLocaleString()}</td><td><strong>${e.action}</strong></td><td>${e.details || ''}</td></tr>`
    ).join('') || '<tr><td colspan="3" style="color:var(--text-dim)">No events yet</td></tr>';
  }
}

// ---- SECURITY ----
async function loadSecurity() {
  const r = await fetch('/api/security/summary');
  if (!r.ok) return;
  const d = await r.json();

  document.querySelector('#sec-attempts .stat-value').textContent = d.total_failed_attempts;
  document.querySelector('#sec-ips .stat-value').textContent = d.unique_ips;
  document.querySelector('#sec-bans .stat-value').textContent = d.fail2ban.available
    ? d.fail2ban.active_bans.length : 'N/A';
  document.querySelector('#sec-total-bans .stat-value').textContent = d.fail2ban.available
    ? d.fail2ban.total_banned : 'N/A';

  const atBody = document.querySelector('#attackers-table tbody');
  atBody.innerHTML = d.top_attacking_ips.map((ip, i) =>
    `<tr><td>${i+1}</td><td><code>${ip.ip}</code></td><td>${ip.count}</td></tr>`
  ).join('');

  const evBody = document.querySelector('#events-table tbody');
  evBody.innerHTML = [...d.recent_events].reverse().slice(0, 50).map(e =>
    `<tr><td>${new Date(e.timestamp).toLocaleString()}</td><td><code>${e.ip}</code></td><td>${e.line.substring(0, 80)}</td></tr>`
  ).join('');
}

// ---- HISTORY ----
let charts = {};

function mkChart(id, label, color) {
  const ctx = document.getElementById(id);
  if (charts[id]) charts[id].destroy();
  charts[id] = new Chart(ctx, {
    type: 'line',
    data: {labels: [], datasets: [{label, data: [], borderColor: color, backgroundColor: color + '20', fill: true, tension: 0.3, pointRadius: 0}]},
    options: {
      responsive: true,
      plugins: {legend: {labels: {color: '#94a3b8'}}},
      scales: {
        x: {ticks: {color: '#94a3b8', maxTicksLimit: 8}, grid: {color: '#2d3250'}},
        y: {ticks: {color: '#94a3b8'}, grid: {color: '#2d3250'}},
      },
    },
  });
  return charts[id];
}

async function loadHistory(hours) {
  document.querySelectorAll('.range-btn').forEach(b => {
    b.classList.toggle('active', parseInt(b.dataset.hours) === hours);
    b.onclick = () => loadHistory(parseInt(b.dataset.hours));
  });

  const r = await fetch(`/api/metrics/history?hours=${hours}`);
  if (!r.ok) return;
  const rows = await r.json();

  const labels = rows.map(r => new Date(r.timestamp).toLocaleString());

  const cpuChart = mkChart('chart-cpu', 'CPU %', '#6366f1');
  cpuChart.data.labels = labels;
  cpuChart.data.datasets[0].data = rows.map(r => r.cpu_percent);
  cpuChart.update();

  const ramChart = mkChart('chart-ram', 'RAM %', '#22c55e');
  ramChart.data.labels = labels;
  ramChart.data.datasets[0].data = rows.map(r => r.ram_percent);
  ramChart.update();

  const tempChart = mkChart('chart-temp', 'Temp °C', '#eab308');
  tempChart.data.labels = labels;
  tempChart.data.datasets[0].data = rows.map(r => r.temp);
  tempChart.update();
}

// ---- REPORTS ----
async function loadReports() {
  const r = await fetch('/api/reports/');
  if (!r.ok) return;
  const reports = await r.json();
  const list = document.getElementById('reports-list');
  list.innerHTML = reports.map(rep =>
    `<div class="report-item" data-id="${rep.id}">
      <div class="r-title">${rep.title}</div>
      <div class="r-date">${new Date(rep.timestamp).toLocaleDateString()}</div>
    </div>`
  ).join('') || '<p style="padding:16px;color:var(--text-dim)">No reports yet</p>';

  list.querySelectorAll('.report-item').forEach(item => {
    item.addEventListener('click', async () => {
      list.querySelectorAll('.report-item').forEach(i => i.classList.remove('active'));
      item.classList.add('active');
      const resp = await fetch(`/api/reports/${item.dataset.id}`);
      const rep = await resp.json();
      document.getElementById('report-body').innerHTML = marked.parse(rep.content);
      // Show action items panel
      const items = extractActionItems(rep.content);
      const actionsEl = document.getElementById('report-actions');
      const listEl = document.getElementById('report-actions-list');
      if (items.length) {
        listEl.innerHTML = items.map(i => `<div class="action-item">${marked.parseInline(i.replace('[ACTION NEEDED]', '').trim())}</div>`).join('');
        actionsEl.classList.remove('hidden');
      } else {
        actionsEl.classList.add('hidden');
      }
    });
  });
}

// ---- AGENT EVENTS ----
async function loadAgentEvents() {
  const r = await fetch('/api/events/');
  if (!r.ok) return;
  const events = await r.json();
  const tbody = document.querySelector('#agent-events-table tbody');
  tbody.innerHTML = events.map(e =>
    `<tr>
      <td>${new Date(e.timestamp).toLocaleString()}</td>
      <td><strong>${e.action}</strong></td>
      <td>${e.details || ''}</td>
    </tr>`
  ).join('') || '<tr><td colspan="3" style="color:var(--text-dim)">No events yet</td></tr>';
}

// Start on overview
showPage('overview');
