/**
 * KNOW YOUR DATA — Financial Intelligence Dashboard
 * Frontend logic: upload, API calls, charts, table, filters, pagination
 */

// ─────────────────────────────────────────────
// State
// ─────────────────────────────────────────────
const State = {
  sessionId: null,
  exportId: null,
  transactions: [],
  filtered: [],
  sortKey: null,
  sortDir: 1,           // 1 = asc, -1 = desc
  page: 1,
  pageSize: 20,
  charts: {},           // chart instances
};

// ─────────────────────────────────────────────
// DOM Refs
// ─────────────────────────────────────────────
const $ = id => document.getElementById(id);
const dropZone      = $('dropZone');
const fileInput     = $('fileInput');
const uploadSection = $('uploadSection');
const dashboard     = $('dashboard');
const loadingOverlay = $('loadingOverlay');
const progressFill  = $('progressFill');
const uploadProgress = $('uploadProgress');

// ─────────────────────────────────────────────
// Utilities
// ─────────────────────────────────────────────
function showToast(msg, type = '') {
  const t = $('toast');
  t.textContent = msg;
  t.className = `toast show ${type}`;
  clearTimeout(t._timer);
  t._timer = setTimeout(() => t.classList.remove('show'), 3200);
}

function fmtNum(n) {
  if (n == null || isNaN(n)) return '—';
  if (Math.abs(n) >= 1_000_000) return (n / 1_000_000).toFixed(2) + 'M';
  if (Math.abs(n) >= 1_000)     return n.toLocaleString(undefined, { maximumFractionDigits: 0 });
  return n.toFixed(2);
}

function fmtCurrency(n, currency) {
  if (n == null || isNaN(n)) return '—';
  const sym = { INR: '₹', USD: '$', EUR: '€', GBP: '£', AED: 'د.إ', JPY: '¥' }[currency] || '';
  return sym + fmtNum(n);
}

function catClass(cat) {
  if (!cat) return 'cat-Misc';
  if (cat.includes('Cloud'))    return 'cat-Cloud';
  if (cat.includes('SaaS'))     return 'cat-SaaS';
  if (cat.includes('Travel'))   return 'cat-Travel';
  if (cat.includes('Meals'))    return 'cat-Meals';
  if (cat.includes('Finance'))  return 'cat-Finance';
  if (cat.includes('Hardware')) return 'cat-Hardware';
  if (cat.includes('Personal')) return 'cat-Personal';
  return 'cat-Misc';
}

// ─────────────────────────────────────────────
// Loading Steps Animation
// ─────────────────────────────────────────────
let _stepTimer = null;
function animateLoadingSteps() {
  const steps = ['ls1','ls2','ls3','ls4','ls5','ls6'];
  let i = 0;
  steps.forEach(id => { const el = $(id); if(el) { el.className = 'lstep'; } });

  function nextStep() {
    if (i > 0 && i <= steps.length) {
      const prev = $(steps[i - 1]);
      if (prev) prev.className = 'lstep done';
    }
    if (i < steps.length) {
      const el = $(steps[i]);
      if (el) el.className = 'lstep active';
      i++;
      _stepTimer = setTimeout(nextStep, 600);
    }
  }
  nextStep();
}

function stopLoadingSteps() {
  clearTimeout(_stepTimer);
  ['ls1','ls2','ls3','ls4','ls5','ls6'].forEach(id => {
    const el = $(id); if(el) el.className = 'lstep done';
  });
}

// ─────────────────────────────────────────────
// Upload Flow
// ─────────────────────────────────────────────
function handleFile(file) {
  if (!file) return;
  const ext = file.name.split('.').pop().toLowerCase();
  if (!['xlsx', 'csv'].includes(ext)) {
    showToast('Only .xlsx and .csv files are supported.', 'error');
    return;
  }

  // Show progress UI
  uploadProgress.style.display = 'block';
  simulateProgress();

  // Show loading overlay
  loadingOverlay.style.display = 'flex';
  animateLoadingSteps();

  const formData = new FormData();
  formData.append('file', file);

  fetch('/upload', { method: 'POST', body: formData })
    .then(r => r.json())
    .then(data => {
      if (data.error) throw new Error(data.error);
      State.sessionId = data.session_id;
      return fetchDashboard(data.session_id);
    })
    .catch(err => {
      stopLoadingSteps();
      loadingOverlay.style.display = 'none';
      uploadProgress.style.display = 'none';
      showToast('Error: ' + err.message, 'error');
    });
}

let _progTimer = null;
function simulateProgress() {
  let pct = 0;
  progressFill.style.width = '0%';
  clearInterval(_progTimer);
  _progTimer = setInterval(() => {
    pct = Math.min(pct + Math.random() * 8, 90);
    progressFill.style.width = pct + '%';
    if (pct >= 90) clearInterval(_progTimer);
  }, 200);
}

function completeProgress() {
  clearInterval(_progTimer);
  progressFill.style.width = '100%';
}

// ─────────────────────────────────────────────
// Dashboard Data Loading
// ─────────────────────────────────────────────
function fetchDashboard(sid) {
  return fetch(`/dashboard-data?session_id=${sid}`)
    .then(r => r.json())
    .then(data => {
      if (data.error) throw new Error(data.error);
      stopLoadingSteps();
      completeProgress();
      setTimeout(() => {
        loadingOverlay.style.display = 'none';
        renderDashboard(data);
      }, 500);
    });
}

// ─────────────────────────────────────────────
// Dashboard Rendering
// ─────────────────────────────────────────────
function renderDashboard(data) {
  State.exportId = data.export_id;
  State.transactions = data.transactions || [];

  // Switch views
  uploadSection.style.display = 'none';
  dashboard.style.display = 'block';
  window.scrollTo(0, 0);

  // Set header meta
  const kpis = data.kpis;
  $('dashMeta').textContent =
    `${kpis.total_transactions} transactions · ${kpis.currency} · Generated ${new Date().toLocaleString()}`;

  // Render sections
  renderKPIs(kpis);
  renderColDetect(kpis.detected_columns);
  renderInsights(data.insights);
  renderCharts(data.chart_data, kpis.currency);
  renderTable(State.transactions, kpis.currency);
  populateCategoryFilter(State.transactions);

  $('navStatus').textContent = `${kpis.total_transactions} rows loaded`;
  showToast(`✓ Dataset processed: ${kpis.total_transactions} transactions`, 'success');
}

// ── KPIs ──
function renderKPIs(kpis) {
  const currency = kpis.currency;
  const cards = [
    { label: 'Total Transactions', icon: '📊', value: kpis.total_transactions, cls: '', fmt: n => n.toLocaleString(), sub: `${kpis.original_count} rows ingested` },
    { label: 'Cleaned Records',    icon: '✓',  value: kpis.cleaned_records,    cls: 'info-card', fmt: n => n.toLocaleString(), valCls: 'info-text', sub: `${kpis.invalid_amounts} invalid amounts` },
    { label: 'Total Spend',        icon: '💰', value: kpis.total_spend,         cls: '', fmt: n => fmtCurrency(n, currency), valCls: 'accent-text', sub: currency },
    { label: 'Duplicate Exposure', icon: '⚠',  value: kpis.duplicate_exposure,  cls: kpis.duplicate_count > 0 ? 'critical' : '', fmt: n => fmtCurrency(n, currency), valCls: kpis.duplicate_count > 0 ? 'critical-text' : '', sub: `${kpis.duplicate_count} duplicate rows` },
    { label: 'Personal Expenses',  icon: '🚩', value: kpis.personal_exposure,   cls: kpis.personal_exposure > 0 ? 'warning' : '', fmt: n => fmtCurrency(n, currency), valCls: kpis.personal_exposure > 0 ? 'warning-text' : '', sub: 'Flagged for review' },
    { label: 'SaaS & Cloud Spend', icon: '☁',  value: kpis.saas_spend,          cls: '', fmt: n => fmtCurrency(n, currency), valCls: 'accent-text', sub: 'Technology spend' },
    { label: 'Critical Issues',    icon: '🔴', value: kpis.critical_count,      cls: kpis.critical_count > 0 ? 'critical' : '', fmt: n => n, valCls: kpis.critical_count > 0 ? 'critical-text' : '', sub: `${kpis.warning_count} warnings` },
    { label: 'Flagged Rows',       icon: '⚑',  value: kpis.flagged_rows,        cls: kpis.flagged_rows > 0 ? 'warning' : '', fmt: n => n, valCls: kpis.flagged_rows > 0 ? 'warning-text' : '', sub: `${kpis.missing_vendors} missing vendors` },
  ];

  const grid = $('kpiGrid');
  grid.innerHTML = cards.map(c => `
    <div class="kpi-card ${c.cls}">
      <p class="kpi-label"><span class="kpi-icon">${c.icon}</span> ${c.label}</p>
      <p class="kpi-value ${c.valCls || ''}">${c.fmt(c.value)}</p>
      <p class="kpi-sub">${c.sub}</p>
    </div>
  `).join('');
}

// ── Column Detection Banner ──
function renderColDetect(colMap) {
  const tags = $('colDetectTags');
  if (!colMap || !Object.keys(colMap).length) {
    $('colDetectBanner').style.display = 'none';
    return;
  }
  tags.innerHTML = Object.entries(colMap)
    .map(([field, col]) => `<span class="col-tag">${field} → <b>${col}</b></span>`)
    .join('');
}

// ── Insights ──
function renderInsights(insights) {
  const list = $('insightsList');
  if (!insights || !insights.length) {
    list.innerHTML = '<p class="empty-state">No insights generated.</p>';
    return;
  }
  list.innerHTML = insights.map((ins, i) => `
    <div class="insight-card ${ins.type}" style="animation-delay:${i * 60}ms">
      <div class="insight-dot"></div>
      <span class="insight-type">${ins.type}</span>
      <span class="insight-msg">${ins.message}</span>
    </div>
  `).join('');
}

// ─────────────────────────────────────────────
// Charts
// ─────────────────────────────────────────────
const CHART_COLORS = [
  '#3d9eff','#7ecfff','#a78bfa','#34d399','#fbbf24',
  '#f87171','#fb923c','#6b7280','#10b981','#60a5fa',
];

Chart.defaults.color = '#8899aa';
Chart.defaults.borderColor = '#1e2a38';
Chart.defaults.font.family = 'JetBrains Mono, monospace';
Chart.defaults.font.size = 11;

function destroyChart(key) {
  if (State.charts[key]) {
    State.charts[key].destroy();
    delete State.charts[key];
  }
}

function renderCharts(chartData, currency) {
  // Category distribution (horizontal bar)
  destroyChart('category');
  const catD = chartData.category_distribution || {};
  if (Object.keys(catD).length) {
    State.charts.category = new Chart($('chartCategory'), {
      type: 'bar',
      data: {
        labels: Object.keys(catD),
        datasets: [{
          data: Object.values(catD),
          backgroundColor: CHART_COLORS,
          borderRadius: 5,
          borderSkipped: false,
        }]
      },
      options: {
        indexAxis: 'y',
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false }, tooltip: { callbacks: {
          label: ctx => ` ${ctx.raw} transactions`
        }}},
        scales: {
          x: { grid: { color: '#1e2a38' }, ticks: { precision: 0 } },
          y: { grid: { display: false } }
        }
      }
    });
  }

  // Risk severity (doughnut)
  destroyChart('risk');
  const riskD = chartData.risk_severity || {};
  if (Object.keys(riskD).length) {
    const riskColors = { CRITICAL: '#ff4d4d', WARNING: '#ffb347', INFO: '#4ade80' };
    State.charts.risk = new Chart($('chartRisk'), {
      type: 'doughnut',
      data: {
        labels: Object.keys(riskD),
        datasets: [{
          data: Object.values(riskD),
          backgroundColor: Object.keys(riskD).map(k => riskColors[k] || '#6b7280'),
          borderColor: '#111820',
          borderWidth: 3,
        }]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        cutout: '65%',
        plugins: {
          legend: { position: 'bottom', labels: { padding: 16, usePointStyle: true, pointStyleWidth: 8 } }
        }
      }
    });
  }

  // Confidence distribution (bar)
  destroyChart('confidence');
  const confD = chartData.confidence_distribution || {};
  if (Object.keys(confD).length) {
    State.charts.confidence = new Chart($('chartConfidence'), {
      type: 'bar',
      data: {
        labels: Object.keys(confD),
        datasets: [{
          data: Object.values(confD),
          backgroundColor: ['#4ade80','#3d9eff','#ffb347','#ff4d4d'],
          borderRadius: 5,
        }]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { display: false } },
          y: { grid: { color: '#1e2a38' }, ticks: { precision: 0 } }
        }
      }
    });
  }

  // Vendor spend (horizontal bar)
  destroyChart('vendor');
  const vendorD = chartData.vendor_spend || {};
  if (Object.keys(vendorD).length) {
    State.charts.vendor = new Chart($('chartVendor'), {
      type: 'bar',
      data: {
        labels: Object.keys(vendorD).map(v => v.length > 22 ? v.substring(0, 22) + '…' : v),
        datasets: [{
          data: Object.values(vendorD),
          backgroundColor: CHART_COLORS,
          borderRadius: 4,
          borderSkipped: false,
        }]
      },
      options: {
        indexAxis: 'y',
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false }, tooltip: { callbacks: {
          label: ctx => ` ${currency === 'INR' ? '₹' : ''}${fmtNum(ctx.raw)}`
        }}},
        scales: {
          x: { grid: { color: '#1e2a38' } },
          y: { grid: { display: false } }
        }
      }
    });
  }

  // Department spend
  destroyChart('dept');
  const deptD = chartData.department_spend || {};
  const deptCard = $('chartDeptCard');
  if (Object.keys(deptD).length) {
    deptCard.style.display = 'block';
    State.charts.dept = new Chart($('chartDept'), {
      type: 'pie',
      data: {
        labels: Object.keys(deptD),
        datasets: [{
          data: Object.values(deptD),
          backgroundColor: CHART_COLORS,
          borderColor: '#111820',
          borderWidth: 2,
        }]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: {
          legend: { position: 'right', labels: { padding: 12, usePointStyle: true, pointStyleWidth: 8 } }
        }
      }
    });
  } else {
    deptCard.style.display = 'none';
  }

  // Duplicate analysis
  destroyChart('duplicate');
  const dupD = chartData.duplicate_analysis || {};
  const dupCard = $('chartDupCard');
  if (Object.keys(dupD).length) {
    dupCard.style.display = 'block';
    State.charts.duplicate = new Chart($('chartDuplicate'), {
      type: 'bar',
      data: {
        labels: Object.keys(dupD).map(v => v.length > 18 ? v.substring(0, 18) + '…' : v),
        datasets: [{
          label: 'Duplicate Exposure',
          data: Object.values(dupD),
          backgroundColor: 'rgba(255,77,77,0.6)',
          borderColor: '#ff4d4d',
          borderWidth: 1,
          borderRadius: 4,
        }]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false }, tooltip: { callbacks: {
          label: ctx => ` ${fmtCurrency(ctx.raw, currency)}`
        }}},
        scales: {
          x: { grid: { display: false } },
          y: { grid: { color: '#1e2a38' } }
        }
      }
    });
  } else {
    dupCard.style.display = 'none';
  }
}

// ─────────────────────────────────────────────
// Transaction Table
// ─────────────────────────────────────────────
function populateCategoryFilter(txns) {
  const cats = [...new Set(txns.map(t => t.category).filter(Boolean))].sort();
  const sel = $('filterCategory');
  sel.innerHTML = '<option value="">All Categories</option>' +
    cats.map(c => `<option value="${c}">${c}</option>`).join('');
}

function applyFilters() {
  const searchVal = $('searchInput').value.toLowerCase();
  const sevFilter = $('filterSeverity').value;
  const catFilter = $('filterCategory').value;

  State.filtered = State.transactions.filter(t => {
    const matchSearch = !searchVal ||
      (t.vendor || '').toLowerCase().includes(searchVal) ||
      (t.category || '').toLowerCase().includes(searchVal) ||
      (t.flags || '').toLowerCase().includes(searchVal) ||
      (t.description || '').toLowerCase().includes(searchVal);
    const matchSev = !sevFilter || t.severity === sevFilter;
    const matchCat = !catFilter || t.category === catFilter;
    return matchSearch && matchSev && matchCat;
  });

  // Apply sort
  if (State.sortKey) {
    State.filtered.sort((a, b) => {
      let av = a[State.sortKey], bv = b[State.sortKey];
      if (typeof av === 'number' && typeof bv === 'number') return (av - bv) * State.sortDir;
      return String(av || '').localeCompare(String(bv || '')) * State.sortDir;
    });
  }

  State.page = 1;
  renderTablePage();
}

function renderTable(txns, currency) {
  State.filtered = [...txns];
  State.page = 1;
  renderTablePage(currency);
  setupTableSort();
}

function renderTablePage(currency) {
  // Determine currency from KPI if not passed
  const cur = currency || document.getElementById('dashMeta')?.textContent?.match(/\b(INR|USD|EUR|GBP|AED)\b/)?.[0] || '';
  const sym = { INR: '₹', USD: '$', EUR: '€', GBP: '£', AED: 'د.إ' }[cur] || '';

  const total = State.filtered.length;
  const pages = Math.max(1, Math.ceil(total / State.pageSize));
  State.page = Math.min(State.page, pages);

  const start = (State.page - 1) * State.pageSize;
  const slice = State.filtered.slice(start, start + State.pageSize);

  const tbody = $('tableBody');
  if (!slice.length) {
    tbody.innerHTML = `<tr><td colspan="8" class="empty-state">No transactions match the current filters.</td></tr>`;
  } else {
    tbody.innerHTML = slice.map(t => {
      const amtStr = t.amount != null ? `${sym}${fmtNum(t.amount)}` : (t.amount_raw || '—');
      const confPct = Math.round((t.confidence || 0) * 100);
      const confColor = confPct >= 80 ? '#4ade80' : confPct >= 60 ? '#3d9eff' : confPct >= 40 ? '#ffb347' : '#ff4d4d';
      const flags = (t.flags || '').split(';').map(f => f.trim()).filter(Boolean);
      const flagHtml = flags.map(f => {
        const cls = f.toLowerCase().includes('duplicate') ? 'dup' :
                    f.toLowerCase().includes('missing') || f.toLowerCase().includes('invalid') ? 'warn' : '';
        return `<span class="flag-chip ${cls}">${f}</span>`;
      }).join('');

      return `
        <tr class="${t.is_duplicate ? 'dup-row' : ''}">
          <td class="vendor-cell" title="${t.vendor}">${t.vendor || '—'}</td>
          <td><span class="cat-badge ${catClass(t.category)}">${t.category}</span></td>
          <td class="amount-cell">${amtStr}</td>
          <td>${t.department || '—'}</td>
          <td style="font-family:var(--font-mono);font-size:11px">${t.date || '—'}</td>
          <td>
            <div class="conf-bar-wrap">
              <div class="conf-bar"><div class="conf-bar-fill" style="width:${confPct}%;background:${confColor}"></div></div>
              <span class="conf-val">${confPct}%</span>
            </div>
          </td>
          <td><span class="badge badge-${t.severity}">${t.severity}</span></td>
          <td><div class="flag-list">${flagHtml || '—'}</div></td>
        </tr>`;
    }).join('');
  }

  // Pagination controls
  $('pgInfo').textContent = `Page ${State.page} of ${pages} · ${total} rows`;
  $('pgPrev').disabled = State.page <= 1;
  $('pgNext').disabled = State.page >= pages;
}

function setupTableSort() {
  document.querySelectorAll('.data-table thead th[data-sort]').forEach(th => {
    th.addEventListener('click', () => {
      const key = th.dataset.sort;
      if (State.sortKey === key) {
        State.sortDir *= -1;
      } else {
        State.sortKey = key;
        State.sortDir = 1;
      }
      // Update sort icons
      document.querySelectorAll('.sort-icon').forEach(i => i.textContent = '↕');
      th.querySelector('.sort-icon').textContent = State.sortDir === 1 ? '↑' : '↓';
      applyFilters();
    });
  });
}

// ─────────────────────────────────────────────
// Event Listeners
// ─────────────────────────────────────────────

// Drag & Drop
dropZone.addEventListener('dragover', e => {
  e.preventDefault();
  dropZone.classList.add('dragover');
});
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
dropZone.addEventListener('drop', e => {
  e.preventDefault();
  dropZone.classList.remove('dragover');
  const file = e.dataTransfer.files[0];
  if (file) handleFile(file);
});
dropZone.addEventListener('click', () => fileInput.click());

// File input change
fileInput.addEventListener('change', () => {
  if (fileInput.files[0]) handleFile(fileInput.files[0]);
});

// Filters & search
$('searchInput').addEventListener('input', applyFilters);
$('filterSeverity').addEventListener('change', applyFilters);
$('filterCategory').addEventListener('change', applyFilters);

// Pagination
$('pgPrev').addEventListener('click', () => { State.page--; renderTablePage(); });
$('pgNext').addEventListener('click', () => { State.page++; renderTablePage(); });

// Export buttons
$('btnExportCSV').addEventListener('click', () => {
  if (!State.exportId) return showToast('No data to export', 'error');
  window.location = `/download-cleaned?export_id=${State.exportId}&format=csv`;
});
$('btnExportXLSX').addEventListener('click', () => {
  if (!State.exportId) return showToast('No data to export', 'error');
  window.location = `/download-cleaned?export_id=${State.exportId}&format=xlsx`;
});
$('btnExportJSON').addEventListener('click', () => {
  if (!State.exportId) return showToast('No report to export', 'error');
  window.location = `/download-report?export_id=${State.exportId}&format=json`;
});

// New Upload button
$('btnNewUpload').addEventListener('click', () => {
  uploadSection.style.display = 'flex';
  dashboard.style.display = 'none';
  uploadProgress.style.display = 'none';
  progressFill.style.width = '0%';
  $('navStatus').textContent = 'Ready';
  fileInput.value = '';
  State.sessionId = null;
  State.exportId = null;
  State.transactions = [];
  State.filtered = [];
  // Destroy charts
  Object.values(State.charts).forEach(c => c.destroy());
  State.charts = {};
});

// Prevent default form submit on file input inside label
document.querySelector('label.upload-btn')?.addEventListener('click', e => {
  e.stopPropagation(); // Don't trigger dropZone click
});
