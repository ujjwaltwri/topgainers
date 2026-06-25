class Overview {
  constructor() {
    this.period = '6M';
    this.init();
  }

  async init() {
    this.setupTheme();
    this.setupPeriodSelector();
    this.renderMarquee();
    this.renderMarketClocks();
    setInterval(() => this.renderMarketClocks(), 60000);
    setInterval(() => this.renderMarquee(), 5000);
    await this.fetchAllData();
    window.addEventListener('resize', this.debounce(() => {
      this.renderTreemap();
      this.renderSectorChart();
    }, 250));
  }

  debounce(func, wait) {
    let timeout;
    return function(...args) {
      clearTimeout(timeout);
      timeout = setTimeout(() => func.apply(this, args), wait);
    };
  }

  // ── Market Clocks ──────────────────────────────
  renderMarketClocks() {
    const container = document.getElementById('market-clocks');
    if (!container) return;
    const now = new Date();
    const utcH = now.getUTCHours();
    const utcM = now.getUTCMinutes();
    const utcMins = utcH * 60 + utcM;
    const day = now.getUTCDay();
    const sessions = [
      { name: 'US',  open: 13 * 60 + 30, close: 20 * 60 },
      { name: 'EU',  open: 8  * 60,      close: 16 * 60 + 30 },
      { name: 'JP',  open: 0  * 60,      close: 6  * 60 },
      { name: 'IN',  open: 3  * 60 + 45, close: 10 * 60 },
    ];
    const weekend = day === 0 || day === 6;
    container.innerHTML = sessions.map(s => {
      const isOpen = !weekend && (
        s.open < s.close
          ? utcMins >= s.open && utcMins < s.close
          : utcMins >= s.open || utcMins < s.close
      );
      return `<div class="market-clock-item ${isOpen ? 'open' : 'closed'}"><span class="market-clock-dot"></span>${s.name}${isOpen ? ' OPEN' : ''}</div>`;
    }).join('');
  }

  // ── Theme ──────────────────────────────────────
  setupTheme() {
    const savedTheme = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-theme', savedTheme);
    const btn = document.getElementById('theme-toggle');
    if (!btn) return;
    const svg = btn.querySelector('svg');
    const setIcon = (theme) => {
      if (!svg) return;
      svg.innerHTML = theme === 'dark'
        ? '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>'
        : '<circle cx="12" cy="12" r="5"></circle><line x1="12" y1="1" x2="12" y2="3"></line><line x1="12" y1="21" x2="12" y2="23"></line><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line><line x1="1" y1="12" x2="3" y2="12"></line><line x1="21" y1="12" x2="23" y2="12"></line><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line>';
    };
    setIcon(savedTheme);
    btn.addEventListener('click', () => {
      const current = document.documentElement.getAttribute('data-theme');
      const next = current === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', next);
      localStorage.setItem('theme', next);
      setIcon(next);
      this.renderSectorChart();
    });
  }

  // ── Marquee ────────────────────────────────────
  async renderMarquee() {
    const container = document.getElementById('global-marquee');
    const content = document.getElementById('marquee-content');
    if (!container || !content) return;
    if (!this.marqueeLoaded) {
      container.style.display = 'block';
      content.innerHTML = '<span style="color:var(--ink-tertiary)">Fetching Global Markets...</span>';
    }
    try {
      if (!window.SupabaseAPI || !window.SupabaseAPI.getMarqueeData) return;
      const data = await window.SupabaseAPI.getMarqueeData(this.period);
      if (!data || data.length === 0) {
        if (!this.marqueeLoaded) container.style.display = 'none';
        return;
      }
      this.marqueeLoaded = true;
      container.style.display = 'block';
      let html = '';
      for (let j = 0; j < 2; j++) {
        for (const idx of data) {
          const isUp = idx.pct_change >= 0;
          const sign = isUp ? '+' : '';
          html += `<div class="marquee-item ${isUp ? 'marquee-up' : 'marquee-down'}"><span class="marquee-name">${idx.name}</span><span class="marquee-change">${sign}${idx.pct_change.toFixed(2)}%</span></div>`;
        }
      }
      content.innerHTML = html;
    } catch (e) {
      console.error(e);
      if (!this.marqueeLoaded) container.style.display = 'none';
    }
  }

  // ── Period selector ────────────────────────────
  setupPeriodSelector() {
    document.querySelectorAll('.period-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        document.querySelectorAll('.period-btn').forEach(b => b.classList.remove('active'));
        e.target.classList.add('active');
        this.period = e.target.dataset.period;
        this.fetchAllData();
      });
    });
  }

  // ── Movers tab toggle ──────────────────────────
  showMoversTab(tab) {
    document.getElementById('movers-gainers').style.display = tab === 'gainers' ? '' : 'none';
    document.getElementById('movers-losers').style.display  = tab === 'losers'  ? '' : 'none';
    document.getElementById('tab-gainers').classList.toggle('active', tab === 'gainers');
    document.getElementById('tab-losers').classList.toggle('active',  tab === 'losers');
  }

  // ── Fetch all data ─────────────────────────────
  async fetchAllData() {
    ['treemap-badge','sector-badge','country-badge','exchange-badge','movers-badge'].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.textContent = 'Loading…';
    });
    try {
      const [stats, breadth, sectors, countries, treemap, exchanges, topGainers, topLosers] = await Promise.all([
        window.SupabaseAPI.getStats(),
        window.SupabaseAPI.getMarketBreadth(this.period),
        window.SupabaseAPI.getSectorPerformance(this.period),
        window.SupabaseAPI.getCountryPerformance(this.period),
        window.SupabaseAPI.getTreemap(this.period),
        window.SupabaseAPI.getExchangePerformance(this.period),
        window.SupabaseAPI.getTopMovers({ period: this.period, direction: 'gainers', limit: 10, page: 1, sort: 'pct_change' }),
        window.SupabaseAPI.getTopMovers({ period: this.period, direction: 'losers',  limit: 10, page: 1, sort: 'pct_change' }),
      ]);
      this.data = { stats, breadth, sectors, countries, treemap, exchanges, topGainers, topLosers };
      this.renderAll();
    } catch (e) {
      console.error('Failed to fetch overview data:', e);
      const ts = document.getElementById('data-timestamp');
      if (ts) ts.textContent = '⚠ Data load failed — ' + e.message;
    }
  }

  renderAll() {
    this.updateTimestamp();
    this.renderSummaryCards();
    this.renderTopMovers();
    this.renderSectorChart();
    this.renderTreemap();
    this.renderExchangePerformance();
    this.renderCountryHeatmap();
  }

  // ── Timestamp ──────────────────────────────────
  updateTimestamp() {
    if (this.data.stats && this.data.stats.last_updated) {
      const date = new Date(this.data.stats.last_updated);
      const ts = document.getElementById('data-timestamp');
      if (ts) ts.textContent = 'As of ' + date.toLocaleString();
    }
  }

  timeAgo(d) {
    const diff = (new Date() - d) / 1000;
    if (diff < 60) return 'just now';
    if (diff < 3600) return Math.floor(diff / 60) + 'm ago';
    if (diff < 86400) return Math.floor(diff / 3600) + 'h ago';
    return Math.floor(diff / 86400) + 'd ago';
  }

  formatNumber(n, prefix = '') {
    if (n === null || n === undefined) return '—';
    if (n >= 1e12) return prefix + (n / 1e12).toFixed(2) + 'T';
    if (n >= 1e9)  return prefix + (n / 1e9).toFixed(2) + 'B';
    if (n >= 1e6)  return prefix + (n / 1e6).toFixed(2) + 'M';
    if (n >= 1e3)  return prefix + (n / 1e3).toFixed(2) + 'K';
    return prefix + n.toFixed(2);
  }

  animateCounter(el, targetStr) {
    const target = parseFloat(targetStr.replace(/[^0-9.-]/g, ''));
    const suffix = targetStr.replace(/[0-9.]/g, '').replace(/-/g, '');
    if (isNaN(target)) { el.textContent = targetStr; return; }
    const duration = 800;
    const start = performance.now();
    const step = (now) => {
      const p = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - p, 3);
      el.textContent = Math.round(target * eased).toLocaleString() + suffix;
      if (p < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }

  // ── Summary Cards ──────────────────────────────
  renderSummaryCards() {
    const totalEl = document.getElementById('card-total');
    if (totalEl && this.data.stats.total_stocks) {
      this.animateCounter(totalEl, this.data.stats.total_stocks.toString());
    }

    const breadth = this.data.breadth;
    const breadthEl = document.getElementById('card-breadth');
    const breadthBar = document.getElementById('card-breadth-bar');
    if (breadthEl) {
      const pct = Math.round(breadth.pct_positive || 0);
      breadthEl.textContent = pct + '%';
      breadthEl.className = 'card-value ' + (pct > 50 ? 'text-gain' : 'text-loss');
    }
    if (breadthBar) breadthBar.style.width = (breadth.pct_positive || 0) + '%';
    const breadthSub = document.getElementById('card-breadth-sub');
    if (breadthSub) breadthSub.textContent = `${(breadth.positive || 0).toLocaleString()} up / ${(breadth.negative || 0).toLocaleString()} down`;

    const secs = this.data.sectors.sectors || [];
    if (secs.length > 0) {
      const best = secs[0], worst = secs[secs.length - 1];
      const bs = document.getElementById('card-best-sector');
      if (bs) bs.textContent = best.sector;
      const bss = document.getElementById('card-best-sector-sub');
      if (bss) bss.textContent = (best.avg_change > 0 ? '+' : '') + best.avg_change.toFixed(2) + '% avg · ' + best.stock_count + ' stocks';
      const ws = document.getElementById('card-worst-sector');
      if (ws) ws.textContent = worst.sector;
      const wss = document.getElementById('card-worst-sector-sub');
      if (wss) wss.textContent = (worst.avg_change > 0 ? '+' : '') + worst.avg_change.toFixed(2) + '% avg · ' + worst.stock_count + ' stocks';
    }

    const ctrs = this.data.countries.countries || [];
    if (ctrs.length > 0) {
      const best = ctrs[0], worst = ctrs[ctrs.length - 1];
      const bc = document.getElementById('card-best-country');
      if (bc) bc.textContent = best.country;
      const bcs = document.getElementById('card-best-country-sub');
      if (bcs) bcs.textContent = (best.avg_change > 0 ? '+' : '') + best.avg_change.toFixed(2) + '% avg · ' + best.stock_count + ' stocks';
      const wc = document.getElementById('card-worst-country');
      if (wc) wc.textContent = worst.country;
      const wcs = document.getElementById('card-worst-country-sub');
      if (wcs) wcs.textContent = (worst.avg_change > 0 ? '+' : '') + worst.avg_change.toFixed(2) + '% avg · ' + worst.stock_count + ' stocks';
    }
  }

  // ── Top Movers ─────────────────────────────────
  renderTopMovers() {
    const badge = document.getElementById('movers-badge');
    const title = document.getElementById('movers-title');
    const gainers = this.data.topGainers?.results || [];
    const losers  = this.data.topLosers?.results  || [];

    if (badge) badge.textContent = (gainers.length + losers.length) + ' movers';
    if (title) title.textContent = `Top Movers — ${this.period}`;

    const renderList = (containerId, items, isGain) => {
      const el = document.getElementById(containerId);
      if (!el) return;
      if (!items.length) { el.innerHTML = '<div style="color:var(--text-tertiary);font-size:0.85rem;padding:8px 0">No data</div>'; return; }
      el.innerHTML = items.map((r, i) => {
        const pct = r.pct_change || 0;
        const pctStr = (pct > 0 ? '+' : '') + pct.toFixed(2) + '%';
        const color = isGain ? 'var(--gain-primary)' : 'var(--loss-primary)';
        return `
          <div class="mover-item" onclick="window.location.href='/?ticker=${r.ticker}'">
            <div class="mover-left">
              <span class="mover-rank">#${i + 1}</span>
              <div class="mover-info">
                <div class="mover-ticker">${r.ticker}</div>
                <div class="mover-name">${r.name || r.ticker}</div>
              </div>
            </div>
            <div class="mover-right">
              <div class="mover-pct" style="color:${color}">${pctStr}</div>
              <div class="mover-sector">${r.sector || ''}</div>
            </div>
          </div>`;
      }).join('');
    };

    renderList('movers-gainers', gainers, true);
    renderList('movers-losers', losers, false);
  }

  // ── Exchange Performance ───────────────────────
  renderExchangePerformance() {
    const container = document.getElementById('exchange-grid');
    const badge = document.getElementById('exchange-badge');
    if (!container) return;

    const exchanges = this.data.exchanges?.exchanges || [];
    if (badge) badge.textContent = exchanges.length + ' exchanges';

    if (!exchanges.length) {
      container.innerHTML = '<div class="loading-overlay">No exchange data</div>';
      return;
    }

    container.innerHTML = exchanges.map(ex => {
      const val = ex.avg_change;
      const isPos = val > 0;
      const color = isPos ? 'var(--gain-primary)' : (val < 0 ? 'var(--loss-primary)' : 'var(--text-secondary)');
      const intensity = Math.min(0.18, Math.abs(val) / 60);
      const bgColor = isPos ? `rgba(0,245,160,${intensity})` : val < 0 ? `rgba(245,0,79,${intensity})` : '';
      const pctStr = (val > 0 ? '+' : '') + val.toFixed(2) + '%';
      const total = (ex.count || ex.stock_count || 0);
      const posAdv = ex.positive && total ? Math.round((ex.positive / total) * 100) : null;
      const advColor = posAdv !== null ? (posAdv > 50 ? 'var(--gain-primary)' : 'var(--loss-primary)') : 'var(--text-tertiary)';
      const barW = posAdv !== null ? posAdv : 50;
      return `
        <div class="exchange-card" style="${bgColor ? `background:${bgColor};` : ''}">
          <div class="ex-name" title="${ex.name}">${ex.name}</div>
          <div class="ex-change" style="color:${color}">${pctStr}</div>
          <div class="ex-meta">
            <span class="ex-count">${total.toLocaleString()} stks</span>
            ${posAdv !== null ? `<span class="ex-adv" style="color:${advColor}">${posAdv}% adv</span>` : ''}
          </div>
          <div class="ex-bar"><div class="ex-bar-fill" style="width:${barW}%"></div></div>
        </div>`;
    }).join('');
  }

  // ── Treemap ────────────────────────────────────
  renderTreemap() {
    const container = document.getElementById('treemap');
    if (!container) return;
    if (!this.data.treemap || !this.data.treemap.stocks || !this.data.treemap.stocks.length) {
      container.innerHTML = '<div class="loading-overlay">No data available</div>';
      return;
    }

    document.getElementById('treemap-badge').textContent = this.data.treemap.stocks.length + ' stocks';

    let stocks = this.data.treemap.stocks
      .filter(s => s.market_cap > 0 && s.pct_change !== null)
      .sort((a, b) => b.market_cap - a.market_cap)
      .slice(0, 100);

    const width = container.clientWidth;
    const height = container.clientHeight;
    if (!width || !height) return;

    container.innerHTML = '';

    const totalMcap = stocks.reduce((sum, s) => sum + s.market_cap, 0);
    const totalArea = width * height;
    stocks.forEach(s => { s._area = (s.market_cap / totalMcap) * totalArea; });

    const rects = [];
    function divide(items, x, y, w, h, isVert) {
      if (!items.length) return;
      if (items.length === 1) { rects.push({ stock: items[0], x, y, w, h }); return; }
      const half = items.reduce((s, it) => s + it._area, 0) / 2;
      let sum = 0, splitIdx = 1;
      for (let i = 0; i < items.length; i++) {
        sum += items[i]._area;
        if (sum >= half) { splitIdx = i + 1; break; }
      }
      splitIdx = Math.max(1, Math.min(splitIdx, items.length - 1));
      const left = items.slice(0, splitIdx), right = items.slice(splitIdx);
      const lArea = left.reduce((s, it) => s + it._area, 0);
      const ratio = lArea / (lArea + right.reduce((s, it) => s + it._area, 0));
      if (isVert) {
        const lW = w * ratio;
        divide(left, x, y, lW, h, false);
        divide(right, x + lW, y, w - lW, h, false);
      } else {
        const tH = h * ratio;
        divide(left, x, y, w, tH, true);
        divide(right, x, y + tH, w, h - tH, true);
      }
    }
    divide(stocks, 0, 0, width, height, width > height);

    const tooltip = document.getElementById('tm-tooltip');
    rects.forEach(r => {
      const el = document.createElement('div');
      el.className = 'treemap-rect';
      const c = r.stock.pct_change;
      let bg = c >= 20 ? 'rgba(0,245,160,0.85)' : c >= 10 ? 'rgba(0,210,140,0.75)' : c >= 5 ? 'rgba(0,180,120,0.70)' : c > 0 ? 'rgba(0,140,90,0.60)' : c === 0 ? 'rgba(100,100,120,0.50)' : c > -5 ? 'rgba(180,40,50,0.60)' : c > -10 ? 'rgba(210,20,40,0.70)' : c > -20 ? 'rgba(230,10,30,0.75)' : 'rgba(245,0,79,0.85)';
      el.style.cssText = `left:${r.x}px;top:${r.y}px;width:${Math.max(0,r.w)}px;height:${Math.max(0,r.h)}px;background:${bg}`;
      if (r.w > 40 && r.h > 30) {
        el.innerHTML = `<span class="tm-ticker">${r.stock.ticker}</span><span class="tm-change">${c > 0 ? '+' : ''}${c.toFixed(1)}%</span>`;
      } else if (r.w > 30 && r.h > 15) {
        el.innerHTML = `<span class="tm-ticker" style="font-size:0.6rem">${r.stock.ticker}</span>`;
      }
      el.addEventListener('mousemove', (e) => {
        if (!tooltip) return;
        tooltip.classList.add('visible');
        tooltip.style.left = (e.clientX + 15) + 'px';
        tooltip.style.top = (e.clientY + 15) + 'px';
        document.getElementById('tt-name').textContent = r.stock.name;
        document.getElementById('tt-ticker').textContent = r.stock.ticker;
        const chEl = document.getElementById('tt-change');
        chEl.textContent = (c > 0 ? '+' : '') + c.toFixed(2) + '%';
        chEl.style.color = c > 0 ? 'var(--gain-primary)' : 'var(--loss-primary)';
        document.getElementById('tt-mcap').textContent = this.formatNumber(r.stock.market_cap, '$');
        document.getElementById('tt-sector').textContent = r.stock.sector || 'N/A';
        document.getElementById('tt-volume').textContent = r.stock.volume_ratio ? r.stock.volume_ratio.toFixed(1) + 'x' : 'N/A';
      });
      el.addEventListener('mouseleave', () => tooltip && tooltip.classList.remove('visible'));
      el.addEventListener('click', () => { window.location.href = `/?ticker=${r.stock.ticker}`; });
      container.appendChild(el);
    });
  }

  // ── Sector Bar Chart ───────────────────────────
  renderSectorChart() {
    const container = document.getElementById('sector-chart-container');
    const canvas = document.getElementById('sector-canvas');
    if (!canvas || !this.data?.sectors?.sectors) return;

    const sectors = this.data.sectors.sectors;
    document.getElementById('sector-badge').textContent = sectors.length + ' sectors';

    const rowHeight = 40;
    const pad = { top: 20, right: 70, bottom: 16, left: 170 };
    canvas.height = sectors.length * rowHeight + pad.top + pad.bottom;
    canvas.width = container.clientWidth;

    const ctx = canvas.getContext('2d');
    const w = canvas.width, h = canvas.height;
    ctx.clearRect(0, 0, w, h);

    let maxAbs = 0;
    sectors.forEach(s => { maxAbs = Math.max(maxAbs, Math.abs(s.avg_change)); });
    if (maxAbs === 0) maxAbs = 10;
    maxAbs *= 1.15;

    const chartW = w - pad.left - pad.right;
    const zeroX = pad.left + chartW / 2;
    const toX = (val) => zeroX + (val / maxAbs) * (chartW / 2);

    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    const textColor = isDark ? '#e8e8f0' : '#1a1a2e';
    const textSec = isDark ? '#8888a0' : '#5a5a70';
    const gainColor = isDark ? '#00f5a0' : '#0a8f5a';
    const lossColor = isDark ? '#f5004f' : '#d4003a';
    const gridColor = isDark ? 'rgba(136,136,160,0.2)' : 'rgba(100,100,120,0.15)';

    ctx.strokeStyle = gridColor;
    ctx.lineWidth = 1;
    ctx.setLineDash([4, 4]);
    ctx.beginPath(); ctx.moveTo(zeroX, pad.top - 5); ctx.lineTo(zeroX, h - pad.bottom); ctx.stroke();
    ctx.setLineDash([]);

    ctx.textBaseline = 'middle';
    sectors.forEach((s, i) => {
      const y = pad.top + i * rowHeight + rowHeight / 2;

      ctx.font = '500 13px Inter, sans-serif';
      ctx.textAlign = 'right'; ctx.fillStyle = textColor;
      ctx.fillText(s.sector.length > 20 ? s.sector.slice(0, 19) + '…' : s.sector, pad.left - 12, y);

      const barX = s.avg_change >= 0 ? zeroX : toX(s.avg_change);
      const barW = Math.max(2, Math.abs(toX(s.avg_change) - zeroX));
      ctx.fillStyle = s.avg_change >= 0 ? gainColor : lossColor;
      ctx.beginPath(); ctx.roundRect(barX, y - 8, barW, 16, 3); ctx.fill();

      ctx.font = '600 11px "JetBrains Mono", monospace';
      ctx.fillStyle = s.avg_change >= 0 ? gainColor : lossColor;
      ctx.textAlign = s.avg_change >= 0 ? 'left' : 'right';
      const textX = s.avg_change >= 0 ? barX + barW + 8 : barX - 8;
      ctx.fillText((s.avg_change > 0 ? '+' : '') + s.avg_change.toFixed(2) + '%', textX, y);

      ctx.font = '400 10px Inter, sans-serif';
      ctx.fillStyle = textSec; ctx.textAlign = 'left';
      ctx.fillText(s.stock_count, 4, y);
    });
  }

  // ── Country Heatmap ────────────────────────────
  renderCountryHeatmap() {
    const container = document.getElementById('country-grid');
    if (!container || !this.data?.countries?.countries) return;

    const countries = this.data.countries.countries;
    document.getElementById('country-badge').textContent = countries.length + ' countries';

    const codes = {
      'United States':'US','India':'IN','Japan':'JP','United Kingdom':'GB','Canada':'CA',
      'Australia':'AU','Brazil':'BR','South Korea':'KR','Germany':'DE','China':'CN',
      'Hong Kong':'HK','France':'FR','Netherlands':'NL','Saudi Arabia':'SA','Taiwan':'TW',
      'Singapore':'SG','Malaysia':'MY','Indonesia':'ID','Thailand':'TH','Philippines':'PH',
      'New Zealand':'NZ','Switzerland':'CH','Italy':'IT','Spain':'ES','Sweden':'SE',
      'Norway':'NO','Denmark':'DK','Finland':'FI','Poland':'PL','Austria':'AT',
      'Ireland':'IE','Portugal':'PT','Greece':'GR','Mexico':'MX','Argentina':'AR',
      'Chile':'CL','Israel':'IL','Turkey':'TR','Egypt':'EG','Qatar':'QA',
      'United Arab Emirates':'AE','South Africa':'ZA',
    };

    container.innerHTML = '';
    countries.forEach((c, i) => {
      const card = document.createElement('div');
      card.className = 'country-card';
      card.style.animationDelay = (i * 0.03) + 's';

      const val = c.avg_change;
      if (val > 0) { const t = Math.min(0.22, val / 80); card.style.background = `rgba(0,245,160,${t})`; }
      else if (val < 0) { const t = Math.min(0.22, Math.abs(val) / 80); card.style.background = `rgba(245,0,79,${t})`; }

      const code = codes[c.country] || c.country.slice(0, 2).toUpperCase();
      const pctPos = c.stock_count > 0 ? (c.positive / c.stock_count) * 100 : 0;
      const changeClass = val >= 0 ? 'text-gain' : 'text-loss';

      card.innerHTML = `
        <div class="cc-header">
          <span class="cc-code">${code}</span>
          <span class="cc-name" title="${c.country}">${c.country}</span>
        </div>
        <div class="cc-change ${changeClass}">${val > 0 ? '+' : ''}${val.toFixed(1)}%</div>
        <div class="cc-meta">
          <span>${c.stock_count} stocks</span>
          <span style="color:${pctPos > 50 ? 'var(--gain-primary)' : 'var(--loss-primary)'}">${pctPos.toFixed(0)}% adv</span>
        </div>
        <div class="cc-breadth-bar"><div class="cc-breadth-fill" style="width:${pctPos}%"></div></div>`;

      container.appendChild(card);
    });
  }
}

document.addEventListener('DOMContentLoaded', () => {
  window.overview = new Overview();
});
