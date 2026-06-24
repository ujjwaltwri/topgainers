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

  // ── Market Clock ──────────────────────────────────
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
      const cls = isOpen ? 'open' : 'closed';
      return `<div class="market-clock-item ${cls}"><span class="market-clock-dot"></span>${s.name} ${isOpen ? 'OPEN' : 'CLOSED'}</div>`;
    }).join('');
  }

  setupTheme() {
    const savedTheme = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-theme', savedTheme);
    const btn = document.getElementById('theme-toggle');
    if (btn) {
      const svg = btn.querySelector('svg');
      if (svg) {
        svg.innerHTML = savedTheme === 'dark'
          ? '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>'
          : '<circle cx="12" cy="12" r="5"></circle><line x1="12" y1="1" x2="12" y2="3"></line><line x1="12" y1="21" x2="12" y2="23"></line><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line><line x1="1" y1="12" x2="3" y2="12"></line><line x1="21" y1="12" x2="23" y2="12"></line><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line>';
      }
      btn.addEventListener('click', () => {
        const current = document.documentElement.getAttribute('data-theme');
        const next = current === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', next);
        localStorage.setItem('theme', next);
        if (svg) {
          svg.innerHTML = next === 'dark'
            ? '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>'
            : '<circle cx="12" cy="12" r="5"></circle><line x1="12" y1="1" x2="12" y2="3"></line><line x1="12" y1="21" x2="12" y2="23"></line><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line><line x1="1" y1="12" x2="3" y2="12"></line><line x1="21" y1="12" x2="23" y2="12"></line><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line>';
        }
        this.renderSectorChart();
      });
    }
  }

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
          const cls = isUp ? 'marquee-up' : 'marquee-down';
          const sign = isUp ? '+' : '';
          html += `
            <div class="marquee-item ${cls}">
              <span class="marquee-name">${idx.name}</span>
              <span class="marquee-change">${sign}${idx.pct_change.toFixed(2)}%</span>
            </div>
          `;
        }
      }
      content.innerHTML = html;
    } catch (e) {
      console.error(e);
      if (!this.marqueeLoaded) container.style.display = 'none';
    }
  }

  setupPeriodSelector() {
    const buttons = document.querySelectorAll('.period-btn');
    buttons.forEach(btn => {
      btn.addEventListener('click', (e) => {
        buttons.forEach(b => b.classList.remove('active'));
        e.target.classList.add('active');
        this.period = e.target.dataset.period;
        this.fetchAllData();
      });
    });
  }

  async fetchAllData() {
    document.getElementById('treemap-badge').textContent = 'Loading...';
    document.getElementById('sector-badge').textContent = 'Loading...';
    document.getElementById('country-badge').textContent = 'Loading...';
    document.getElementById('exchange-badge').textContent = 'Loading...';
    document.getElementById('movers-badge').textContent = 'Loading...';

    try {
      const [stats, breadth, sectors, countries, treemap, exchanges, topGainers, topLosers] = await Promise.all([
        window.SupabaseAPI.getStats(),
        window.SupabaseAPI.getMarketBreadth(this.period),
        window.SupabaseAPI.getSectorPerformance(this.period),
        window.SupabaseAPI.getCountryPerformance(this.period),
        window.SupabaseAPI.getTreemap(this.period),
        window.SupabaseAPI.getExchangePerformance(this.period),
        window.SupabaseAPI.getTopMovers({ period: this.period, direction: 'gainers', limit: 5, page: 1, sort: 'pct_change' }),
        window.SupabaseAPI.getTopMovers({ period: this.period, direction: 'losers', limit: 5, page: 1, sort: 'pct_change' }),
      ]);

      this.data = { stats, breadth, sectors, countries, treemap, exchanges, topGainers, topLosers };
      this.renderAll();
    } catch (e) {
      console.error('Failed to fetch overview data:', e);
      document.getElementById('data-timestamp').textContent = '⚠ Data load failed';
    }
  }

  renderAll() {
    this.updateTimestamp();
    this.renderSummaryCards();
    this.renderTopMovers();
    this.renderTreemap();
    this.renderSectorChart();
    this.renderExchangePerformance();
    this.renderCountryHeatmap();
  }

  updateTimestamp() {
    if (this.data.stats && this.data.stats.last_updated) {
      const date = new Date(this.data.stats.last_updated);
      document.getElementById('last-updated-time').textContent = 'Updated ' + this.timeAgo(date);
      document.getElementById('data-timestamp').textContent = 'As of ' + date.toLocaleString();
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
    if (n === null || n === undefined) return '-';
    if (n >= 1e12) return prefix + (n / 1e12).toFixed(2) + 'T';
    if (n >= 1e9) return prefix + (n / 1e9).toFixed(2) + 'B';
    if (n >= 1e6) return prefix + (n / 1e6).toFixed(2) + 'M';
    if (n >= 1e3) return prefix + (n / 1e3).toFixed(2) + 'K';
    return prefix + n.toFixed(2);
  }

  // Animated counter helper
  animateCounter(el, targetStr) {
    const target = parseFloat(targetStr.replace(/[^0-9.-]/g, ''));
    const suffix = targetStr.replace(/[0-9.-]/g, '');
    if (isNaN(target)) { el.textContent = targetStr; return; }
    const duration = 800;
    const start = performance.now();
    const step = (now) => {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      const current = Math.round(target * eased);
      el.textContent = current.toLocaleString() + suffix;
      if (progress < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
    el.classList.add('count-animated');
  }

  renderSummaryCards() {
    const totalEl = document.getElementById('card-total');
    if (totalEl && this.data.stats.total_stocks) {
      this.animateCounter(totalEl, this.data.stats.total_stocks.toString());
    }

    const breadth = this.data.breadth;
    const breadthEl = document.getElementById('card-breadth');
    if (breadthEl) {
      this.animateCounter(breadthEl, Math.round(breadth.pct_positive) + '%');
    }
    const breadthSub = document.getElementById('card-breadth-sub');
    if (breadthSub) breadthSub.textContent = `${(breadth.positive || 0).toLocaleString()} up / ${(breadth.negative || 0).toLocaleString()} down`;
    if (breadthEl) {
      breadthEl.className = 'card-value ' + (breadth.pct_positive > 50 ? 'text-gain' : 'text-loss');
    }

    const secs = this.data.sectors.sectors;
    if (secs && secs.length > 0) {
      const best = secs[0];
      const worst = secs[secs.length - 1];
      document.getElementById('card-best-sector').textContent = best.sector;
      document.getElementById('card-best-sector-sub').textContent = (best.avg_change > 0 ? '+' : '') + best.avg_change.toFixed(2) + '% avg';
      document.getElementById('card-worst-sector').textContent = worst.sector;
      document.getElementById('card-worst-sector-sub').textContent = (worst.avg_change > 0 ? '+' : '') + worst.avg_change.toFixed(2) + '% avg';
    }
  }

  // ── Top Movers ──────────────────────────────────
  renderTopMovers() {
    const gainersEl = document.getElementById('movers-gainers');
    const losersEl = document.getElementById('movers-losers');
    const badge = document.getElementById('movers-badge');

    const gainers = this.data.topGainers?.results || [];
    const losers = this.data.topLosers?.results || [];

    if (badge) badge.textContent = `${gainers.length + losers.length} movers`;

    const renderList = (container, items, isGain) => {
      if (!container) return;
      container.innerHTML = items.map(r => {
        const pctStr = (r.pct_change > 0 ? '+' : '') + (r.pct_change || 0).toFixed(2) + '%';
        const color = isGain ? 'var(--gain-primary)' : 'var(--loss-primary)';
        return `
          <div class="mover-item" onclick="window.location.href='/?ticker=${r.ticker}'">
            <div>
              <div class="mover-ticker">${r.ticker}</div>
              <div class="mover-name">${r.name || r.ticker}</div>
            </div>
            <div class="mover-pct" style="color:${color}">${pctStr}</div>
          </div>
        `;
      }).join('');
    };

    renderList(gainersEl, gainers, true);
    renderList(losersEl, losers, false);
  }

  // ── Exchange Performance ──────────────────────────────────
  renderExchangePerformance() {
    const container = document.getElementById('exchange-grid');
    const badge = document.getElementById('exchange-badge');
    if (!container) return;

    const exchanges = this.data.exchanges?.exchanges || [];
    if (badge) badge.textContent = exchanges.length + ' exchanges';

    if (!exchanges.length) {
      container.innerHTML = '<div class="loading-overlay">No exchange data available</div>';
      return;
    }

    container.innerHTML = exchanges.map(ex => {
      const val = ex.avg_change;
      const isPos = val > 0;
      const color = isPos ? 'var(--gain-primary)' : (val < 0 ? 'var(--loss-primary)' : 'var(--text-secondary)');
      const intensity = Math.min(0.18, Math.abs(val) / 60);
      const bgColor = val > 0
        ? `rgba(0,245,160,${intensity})`
        : val < 0
        ? `rgba(245,0,79,${intensity})`
        : '';
      const pctStr = (val > 0 ? '+' : '') + val.toFixed(2) + '%';
      return `
        <div class="exchange-card" style="${bgColor ? `background:${bgColor};` : ''}">
          <div class="ex-name">${ex.exchange}</div>
          <div class="ex-change" style="color:${color}">${pctStr}</div>
          <div class="ex-count">${(ex.count || ex.stock_count || 0).toLocaleString()} stocks</div>
        </div>
      `;
    }).join('');
  }

  // ── Treemap ──────────────────────────────────
  renderTreemap() {
    const container = document.getElementById('treemap');
    if (!this.data.treemap || !this.data.treemap.stocks || this.data.treemap.stocks.length === 0) {
      container.innerHTML = '<div class="loading-overlay">No data available</div>';
      return;
    }

    document.getElementById('treemap-badge').textContent = this.data.treemap.stocks.length + ' stocks';

    let stocks = this.data.treemap.stocks
      .filter(s => s.market_cap > 0 && s.pct_change !== null)
      .sort((a, b) => b.market_cap - a.market_cap);

    if (stocks.length > 100) stocks = stocks.slice(0, 100);

    const width = container.clientWidth;
    const height = container.clientHeight;

    if (width === 0 || height === 0) return;

    container.innerHTML = '';

    if (stocks.length === 0) {
      container.innerHTML = '<div class="loading-overlay">No data to display</div>';
      return;
    }

    const totalMcap = stocks.reduce((sum, s) => sum + s.market_cap, 0);
    const totalArea = width * height;
    stocks.forEach(s => { s._area = (s.market_cap / totalMcap) * totalArea; });

    let rects = [];

    function divide(items, x, y, w, h, isVertical) {
      if (items.length === 0) return;
      if (items.length === 1) { rects.push({ stock: items[0], x, y, w, h }); return; }
      const targetArea = items.reduce((s, it) => s + it._area, 0) / 2;
      let sum = 0, splitIdx = 0;
      for (let i = 0; i < items.length; i++) {
        sum += items[i]._area;
        if (sum >= targetArea) { splitIdx = i; break; }
      }
      if (splitIdx === 0) splitIdx = 1;
      if (splitIdx === items.length) splitIdx = items.length - 1;
      const leftItems = items.slice(0, splitIdx);
      const rightItems = items.slice(splitIdx);
      const leftArea = leftItems.reduce((s, it) => s + it._area, 0);
      const rightArea = rightItems.reduce((s, it) => s + it._area, 0);
      const ratio = leftArea / (leftArea + rightArea);
      if (isVertical) {
        const leftW = w * ratio;
        divide(leftItems, x, y, leftW, h, false);
        divide(rightItems, x + leftW, y, w - leftW, h, false);
      } else {
        const topH = h * ratio;
        divide(leftItems, x, y, w, topH, true);
        divide(rightItems, x, y + topH, w, h - topH, true);
      }
    }

    divide(stocks, 0, 0, width, height, width > height);

    if (rects.length === 0) {
      container.innerHTML = '<div class="loading-overlay">Layout error</div>';
      return;
    }

    const tooltip = document.getElementById('tm-tooltip');

    rects.forEach(r => {
      const el = document.createElement('div');
      el.className = 'treemap-rect';
      const c = r.stock.pct_change;
      let bgColor = '';
      if (c >= 20) bgColor = 'rgba(0, 245, 160, 0.85)';
      else if (c >= 10) bgColor = 'rgba(0, 210, 140, 0.75)';
      else if (c >= 5) bgColor = 'rgba(0, 180, 120, 0.70)';
      else if (c > 0) bgColor = 'rgba(0, 140, 90, 0.60)';
      else if (c === 0) bgColor = 'rgba(100, 100, 120, 0.50)';
      else if (c > -5) bgColor = 'rgba(180, 40, 50, 0.60)';
      else if (c > -10) bgColor = 'rgba(210, 20, 40, 0.70)';
      else if (c > -20) bgColor = 'rgba(230, 10, 30, 0.75)';
      else bgColor = 'rgba(245, 0, 79, 0.85)';

      el.style.left = r.x + 'px';
      el.style.top = r.y + 'px';
      el.style.width = Math.max(0, r.w) + 'px';
      el.style.height = Math.max(0, r.h) + 'px';
      el.style.backgroundColor = bgColor;

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
        const changeEl = document.getElementById('tt-change');
        changeEl.textContent = (c > 0 ? '+' : '') + c.toFixed(2) + '%';
        changeEl.style.color = c > 0 ? 'var(--gain-primary)' : 'var(--loss-primary)';
        document.getElementById('tt-mcap').textContent = this.formatNumber(r.stock.market_cap, '$');
        document.getElementById('tt-sector').textContent = r.stock.sector || 'N/A';
        document.getElementById('tt-volume').textContent = r.stock.volume_ratio ? r.stock.volume_ratio.toFixed(1) + 'x' : 'N/A';
      });

      el.addEventListener('mouseleave', () => { if (tooltip) tooltip.classList.remove('visible'); });
      el.addEventListener('click', () => { window.location.href = `/?ticker=${r.stock.ticker}`; });
      container.appendChild(el);
    });
  }

  // ── Sector Bar Chart ──────────────────────────────────
  renderSectorChart() {
    const container = document.getElementById('sector-chart-container');
    const canvas = document.getElementById('sector-canvas');
    if (!canvas || !this.data.sectors || !this.data.sectors.sectors) return;

    const sectors = this.data.sectors.sectors;
    document.getElementById('sector-badge').textContent = sectors.length + ' sectors';

    const rowHeight = 40;
    const padding = { top: 30, right: 60, bottom: 20, left: 170 };
    canvas.height = (sectors.length * rowHeight) + padding.top + padding.bottom;
    canvas.width = container.clientWidth;

    const ctx = canvas.getContext('2d');
    const w = canvas.width;
    const h = canvas.height;
    ctx.clearRect(0, 0, w, h);

    let maxAbs = 0;
    sectors.forEach(s => { maxAbs = Math.max(maxAbs, Math.abs(s.avg_change)); });
    if (maxAbs === 0) maxAbs = 10;
    maxAbs *= 1.1;

    const chartW = w - padding.left - padding.right;
    const zeroX = padding.left + (chartW / 2);
    const toX = (val) => zeroX + (val / maxAbs) * (chartW / 2);

    ctx.strokeStyle = 'rgba(136, 136, 160, 0.3)';
    ctx.lineWidth = 1;
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    ctx.moveTo(zeroX, padding.top - 10);
    ctx.lineTo(zeroX, h - padding.bottom);
    ctx.stroke();
    ctx.setLineDash([]);

    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    const textColor = isDark ? '#e8e8f0' : '#1a1a2e';
    const textSecColor = isDark ? '#8888a0' : '#5a5a70';
    const gainColor = isDark ? '#00f5a0' : '#0a8f5a';
    const lossColor = isDark ? '#f5004f' : '#d4003a';

    ctx.textBaseline = 'middle';
    sectors.forEach((s, i) => {
      const y = padding.top + (i * rowHeight) + (rowHeight / 2);
      ctx.font = '500 13px Inter, sans-serif';
      ctx.textAlign = 'right';
      ctx.fillStyle = textColor;
      ctx.fillText(s.sector.length > 22 ? s.sector.substring(0, 20) + '…' : s.sector, padding.left - 15, y);

      const barX = s.avg_change >= 0 ? zeroX : toX(s.avg_change);
      const barW = Math.abs(toX(s.avg_change) - zeroX);
      const barH = 16;

      ctx.fillStyle = s.avg_change >= 0 ? gainColor : lossColor;
      ctx.beginPath();
      ctx.roundRect(barX, y - barH / 2, Math.max(2, barW), barH, 4);
      ctx.fill();

      ctx.textAlign = s.avg_change >= 0 ? 'left' : 'right';
      ctx.fillStyle = s.avg_change >= 0 ? gainColor : lossColor;
      ctx.font = '600 12px "JetBrains Mono", monospace';
      const textX = s.avg_change >= 0 ? barX + barW + 10 : barX - 10;
      ctx.fillText((s.avg_change > 0 ? '+' : '') + s.avg_change.toFixed(2) + '%', textX, y);

      ctx.font = '400 11px Inter, sans-serif';
      ctx.fillStyle = textSecColor;
      ctx.textAlign = 'left';
      ctx.fillText(`(${s.stock_count})`, 10, y);
    });
  }

  // ── Country Heatmap ──────────────────────────────────
  renderCountryHeatmap() {
    const container = document.getElementById('country-grid');
    if (!this.data.countries || !this.data.countries.countries) return;

    const countries = this.data.countries.countries;
    document.getElementById('country-badge').textContent = countries.length + ' countries';

    container.innerHTML = '';

    // ISO 2-letter codes for compact display — no emojis
    const codes = {
      'United States': 'US', 'India': 'IN', 'Japan': 'JP',
      'United Kingdom': 'GB', 'Canada': 'CA', 'Australia': 'AU',
      'Brazil': 'BR', 'South Korea': 'KR', 'Germany': 'DE',
      'China': 'CN', 'Hong Kong': 'HK', 'France': 'FR',
      'Netherlands': 'NL', 'Saudi Arabia': 'SA', 'Taiwan': 'TW',
      'Singapore': 'SG', 'Malaysia': 'MY', 'Indonesia': 'ID',
      'Thailand': 'TH', 'Philippines': 'PH', 'New Zealand': 'NZ',
      'Switzerland': 'CH', 'Italy': 'IT', 'Spain': 'ES',
      'Sweden': 'SE', 'Norway': 'NO', 'Denmark': 'DK',
      'Finland': 'FI', 'Poland': 'PL', 'Austria': 'AT',
      'Ireland': 'IE', 'Portugal': 'PT', 'Greece': 'GR',
      'Mexico': 'MX', 'Argentina': 'AR', 'Chile': 'CL',
      'Israel': 'IL', 'Turkey': 'TR', 'Egypt': 'EG',
      'Qatar': 'QA', 'United Arab Emirates': 'AE', 'South Africa': 'ZA',
    };

    countries.forEach((c, i) => {
      const card = document.createElement('div');
      card.className = 'country-card';
      card.style.animationDelay = (i * 0.04) + 's';

      const val = c.avg_change;
      let bg = '';
      if (val > 0) { const intensity = Math.min(0.22, val / 80); bg = `rgba(0, 245, 160, ${intensity})`; }
      else if (val < 0) { const intensity = Math.min(0.22, Math.abs(val) / 80); bg = `rgba(245, 0, 79, ${intensity})`; }
      if (bg) card.style.background = bg;

      const code = codes[c.country] || c.country.substring(0, 2).toUpperCase();
      const pctPos = c.stock_count > 0 ? (c.positive / c.stock_count) * 100 : 0;
      const changeClass = val >= 0 ? 'text-gain' : 'text-loss';
      const changeStr = (val > 0 ? '+' : '') + val.toFixed(1) + '%';

      card.innerHTML = `
        <div class="cc-header">
          <span class="cc-code">${code}</span>
          <span class="cc-name" title="${c.country}">${c.country}</span>
        </div>
        <div class="cc-change ${changeClass}">${changeStr}</div>
        <div class="cc-meta">
          <span>${c.stock_count} stocks</span>
          <span style="color:${pctPos > 50 ? 'var(--gain-primary)' : 'var(--loss-primary)'}">${pctPos.toFixed(0)}% adv</span>
        </div>
        <div class="cc-breadth-bar">
          <div class="cc-breadth-fill" style="width:${pctPos}%"></div>
        </div>
      `;

      container.appendChild(card);
    });
  }
}

document.addEventListener('DOMContentLoaded', () => {
  window.overview = new Overview();
});
