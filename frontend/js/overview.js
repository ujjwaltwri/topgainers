class Overview {
  constructor() {
    this.period = '6M';
    this.init();
  }

  async init() {
    this.setupTheme();
    this.setupPeriodSelector();
    this.renderMarquee();
    await this.fetchAllData();
    
    // Resize listener for treemap and charts
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

        // Re-render canvases for theme changes
        this.renderSectorChart();
      });
    }
  }

async renderMarquee() {
    this.marqueeLoaded = true;
    const container = document.getElementById('global-marquee');
    const content = document.getElementById('marquee-content');
    if (!container || !content) return;
    
    // Show container and loading state
    container.style.display = 'block';
    content.innerHTML = '<span class="text-secondary">Fetching Global Markets...</span>';
    
    try {
      if (!window.SupabaseAPI || !window.SupabaseAPI.getMarqueeData) return;
      
      const data = await window.SupabaseAPI.getMarqueeData(this.period);
      if (!data || data.length === 0) {
        container.style.display = 'none';
        return;
      }
      
      let html = '';
      // We render two identical sets for seamless scrolling loop
      for(let j=0; j<2; j++) {
        for (const idx of data) {
          const isUp = idx.pct_change >= 0;
          const cls = isUp ? 'marquee-up' : 'marquee-down';
          const sign = isUp ? '+' : '';
          html += `
            <div class="marquee-item ${cls}">
              <span class="marquee-name">${idx.name}</span>
              <span class="marquee-value">${idx.value.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</span>
              <span class="marquee-change">${sign}${idx.pct_change.toFixed(2)}%</span>
            </div>
          `;
        }
      }
      content.innerHTML = html;
      
    } catch (e) {
      console.error(e);
      container.style.display = 'none';
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
    // Show loading states
    document.getElementById('treemap-badge').textContent = 'Loading...';
    document.getElementById('sector-badge').textContent = 'Loading...';
    document.getElementById('country-badge').textContent = 'Loading...';
    
    try {
      const [stats, breadth, sectors, countries, treemap] = await Promise.all([
        window.SupabaseAPI.getStats(),
        window.SupabaseAPI.getMarketBreadth(this.period),
        window.SupabaseAPI.getSectorPerformance(this.period),
        window.SupabaseAPI.getCountryPerformance(this.period),
        window.SupabaseAPI.getTreemap(this.period)
      ]);

      this.data = { stats, breadth, sectors, countries, treemap };
      this.renderAll();
    } catch (e) {
      console.error('Failed to fetch overview data:', e);
      document.getElementById('data-timestamp').textContent = '⚠ Data load failed';
    }
  }

  renderAll() {
    this.updateTimestamp();
    this.renderSummaryCards();
    this.renderTreemap();
    this.renderSectorChart();
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
    if (diff < 3600) return Math.floor(diff/60) + 'm ago';
    if (diff < 86400) return Math.floor(diff/3600) + 'h ago';
    return Math.floor(diff/86400) + 'd ago';
  }

  formatNumber(n, prefix='') {
    if (n === null || n === undefined) return '-';
    if (n >= 1e12) return prefix + (n / 1e12).toFixed(2) + 'T';
    if (n >= 1e9) return prefix + (n / 1e9).toFixed(2) + 'B';
    if (n >= 1e6) return prefix + (n / 1e6).toFixed(2) + 'M';
    if (n >= 1e3) return prefix + (n / 1e3).toFixed(2) + 'K';
    return prefix + n.toFixed(2);
  }

  renderSummaryCards() {
    // Total Stocks
    document.getElementById('card-total').textContent = this.data.stats.total_stocks.toLocaleString();
    
    // Breadth
    const breadth = this.data.breadth;
    document.getElementById('card-breadth').textContent = breadth.pct_positive.toFixed(1) + '%';
    const breadthSub = document.getElementById('card-breadth-sub');
    breadthSub.textContent = `${breadth.positive} up / ${breadth.negative} down`;
    if (breadth.pct_positive > 50) {
      document.getElementById('card-breadth').className = 'card-value text-gain';
    } else {
      document.getElementById('card-breadth').className = 'card-value text-loss';
    }

    // Best & Worst Sectors
    const secs = this.data.sectors.sectors;
    if (secs && secs.length > 0) {
      const best = secs[0];
      const worst = secs[secs.length - 1];
      
      document.getElementById('card-best-sector').textContent = best.sector;
      document.getElementById('card-best-sector-sub').textContent = 
        (best.avg_change > 0 ? '+' : '') + best.avg_change.toFixed(2) + '% avg';
        
      document.getElementById('card-worst-sector').textContent = worst.sector;
      document.getElementById('card-worst-sector-sub').textContent = 
        (worst.avg_change > 0 ? '+' : '') + worst.avg_change.toFixed(2) + '% avg';
    }
  }

  // ----------------------------------------------------------------------
  // TREEMAP
  // ----------------------------------------------------------------------
  renderTreemap() {
    const container = document.getElementById('treemap');
    if (!this.data.treemap || !this.data.treemap.stocks || this.data.treemap.stocks.length === 0) {
      container.innerHTML = '<div class="loading-overlay">No data available</div>';
      return;
    }
    
    document.getElementById('treemap-badge').textContent = this.data.treemap.stocks.length + ' stocks';
    
    // Filter out 0 or missing market caps and sort
    let stocks = this.data.treemap.stocks
      .filter(s => s.market_cap > 0 && s.pct_change !== null)
      .sort((a, b) => b.market_cap - a.market_cap);
      
    // Optionally limit to top N to avoid unreadable tiny boxes
    if (stocks.length > 100) stocks = stocks.slice(0, 100);

    const width = container.clientWidth;
    const height = container.clientHeight;
    
    if (width === 0 || height === 0) return; // Hidden or not sized yet

    container.innerHTML = '';
    
    // Normalize values
    const totalMcap = stocks.reduce((sum, s) => sum + s.market_cap, 0);
    const totalArea = width * height;
    
    // Assign areas
    stocks.forEach(s => {
      s._area = (s.market_cap / totalMcap) * totalArea;
    });

    // Simple slice-and-dice algorithm for treemap
    // We alternate splitting vertically and horizontally
    let rects = [];
    
    function divide(items, x, y, w, h, isVertical) {
      if (items.length === 0) return;
      if (items.length === 1) {
        rects.push({ stock: items[0], x, y, w, h });
        return;
      }
      
      // Find split point that roughly divides area in half
      const targetArea = items.reduce((s, it) => s + it._area, 0) / 2;
      let sum = 0;
      let splitIdx = 0;
      for (let i = 0; i < items.length; i++) {
        sum += items[i]._area;
        if (sum >= targetArea) {
          splitIdx = i;
          break;
        }
      }
      // Ensure at least one item on each side
      if (splitIdx === 0) splitIdx = 1;
      if (splitIdx === items.length) splitIdx = items.length - 1;
      
      const leftItems = items.slice(0, splitIdx);
      const rightItems = items.slice(splitIdx);
      
      const leftArea = leftItems.reduce((s, it) => s + it._area, 0);
      const rightArea = rightItems.reduce((s, it) => s + it._area, 0);
      const ratio = leftArea / (leftArea + rightArea);
      
      if (isVertical) {
        // Split left/right
        const leftW = w * ratio;
        divide(leftItems, x, y, leftW, h, false);
        divide(rightItems, x + leftW, y, w - leftW, h, false);
      } else {
        // Split top/bottom
        const topH = h * ratio;
        divide(leftItems, x, y, w, topH, true);
        divide(rightItems, x, y + topH, w, h - topH, true);
      }
    }
    
    // Start layout (true = start with vertical split)
    divide(stocks, 0, 0, width, height, width > height);
    
    // Render DOM elements
    const tooltip = document.getElementById('tm-tooltip');
    
    rects.forEach(r => {
      const el = document.createElement('div');
      el.className = 'treemap-rect';
      
      // Determine color based on pct_change
      const c = r.stock.pct_change;
      let bgColor = '';
      if (c >= 20) bgColor = 'rgba(0, 245, 160, 0.8)';
      else if (c >= 5) bgColor = 'rgba(0, 180, 120, 0.7)';
      else if (c > 0) bgColor = 'rgba(0, 120, 80, 0.6)';
      else if (c === 0) bgColor = 'rgba(100, 100, 100, 0.5)';
      else if (c > -5) bgColor = 'rgba(150, 40, 40, 0.6)';
      else if (c > -20) bgColor = 'rgba(200, 20, 40, 0.7)';
      else bgColor = 'rgba(245, 0, 79, 0.8)';
      
      el.style.left = r.x + 'px';
      el.style.top = r.y + 'px';
      el.style.width = Math.max(0, r.w) + 'px';
      el.style.height = Math.max(0, r.h) + 'px';
      el.style.backgroundColor = bgColor;
      
      // Only show text if box is large enough
      if (r.w > 40 && r.h > 30) {
        el.innerHTML = `
          <span class="tm-ticker">${r.stock.ticker}</span>
          <span class="tm-change">${c > 0 ? '+' : ''}${c.toFixed(1)}%</span>
        `;
      } else if (r.w > 30 && r.h > 15) {
        el.innerHTML = `<span class="tm-ticker" style="font-size: 0.6rem;">${r.stock.ticker}</span>`;
      }
      
      // Interactions
      el.addEventListener('mousemove', (e) => {
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
      
      el.addEventListener('mouseleave', () => {
        tooltip.classList.remove('visible');
      });
      
      el.addEventListener('click', () => {
        // Navigate to dashboard with this ticker
        window.location.href = `/?search=${r.stock.ticker}`;
      });
      
      container.appendChild(el);
    });
  }

  // ----------------------------------------------------------------------
  // SECTOR BAR CHART
  // ----------------------------------------------------------------------
  renderSectorChart() {
    const container = document.getElementById('sector-chart-container');
    const canvas = document.getElementById('sector-canvas');
    if (!canvas || !this.data.sectors || !this.data.sectors.sectors) return;
    
    const sectors = this.data.sectors.sectors;
    document.getElementById('sector-badge').textContent = sectors.length + ' sectors';
    
    // Adjust height based on rows
    const rowHeight = 40;
    const padding = { top: 30, right: 60, bottom: 20, left: 160 };
    canvas.height = (sectors.length * rowHeight) + padding.top + padding.bottom;
    canvas.width = container.clientWidth;
    
    const ctx = canvas.getContext('2d');
    const w = canvas.width;
    const h = canvas.height;
    
    ctx.clearRect(0, 0, w, h);
    
    // Find min/max for scale
    let maxAbs = 0;
    sectors.forEach(s => {
      maxAbs = Math.max(maxAbs, Math.abs(s.avg_change));
    });
    
    // Default scale if data is empty or zeros
    if (maxAbs === 0) maxAbs = 10;
    maxAbs *= 1.1; // 10% padding
    
    const chartW = w - padding.left - padding.right;
    const zeroX = padding.left + (chartW / 2);
    
    const toX = (val) => {
      return zeroX + (val / maxAbs) * (chartW / 2);
    };
    
    // Draw Center Line (Zero)
    ctx.strokeStyle = 'rgba(136, 136, 160, 0.3)';
    ctx.lineWidth = 1;
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    ctx.moveTo(zeroX, padding.top - 10);
    ctx.lineTo(zeroX, h - padding.bottom);
    ctx.stroke();
    ctx.setLineDash([]);
    
    // Get theme colors
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    const textColor = isDark ? '#e8e8f0' : '#1a1a2e';
    const textSecColor = isDark ? '#8888a0' : '#5a5a70';
    const gainColor = isDark ? '#00f5a0' : '#0a8f5a';
    const lossColor = isDark ? '#f5004f' : '#d4003a';
    
    // Draw rows
    ctx.font = '500 13px Inter, sans-serif';
    ctx.textBaseline = 'middle';
    
    sectors.forEach((s, i) => {
      const y = padding.top + (i * rowHeight) + (rowHeight / 2);
      
      // Label
      ctx.textAlign = 'right';
      ctx.fillStyle = textColor;
      ctx.fillText(s.sector.length > 20 ? s.sector.substring(0, 18) + '...' : s.sector, padding.left - 15, y);
      
      // Bar
      const barX = s.avg_change >= 0 ? zeroX : toX(s.avg_change);
      const barW = Math.abs(toX(s.avg_change) - zeroX);
      const barH = 16;
      
      ctx.fillStyle = s.avg_change >= 0 ? gainColor : lossColor;
      // Round corners
      ctx.beginPath();
      ctx.roundRect(barX, y - barH/2, Math.max(2, barW), barH, 4);
      ctx.fill();
      
      // Value Text
      ctx.textAlign = s.avg_change >= 0 ? 'left' : 'right';
      ctx.fillStyle = s.avg_change >= 0 ? gainColor : lossColor;
      ctx.font = '600 12px "JetBrains Mono", monospace';
      
      const textX = s.avg_change >= 0 ? barX + barW + 10 : barX - 10;
      ctx.fillText((s.avg_change > 0 ? '+' : '') + s.avg_change.toFixed(2) + '%', textX, y);
      
      // Stock count
      ctx.font = '400 11px Inter, sans-serif';
      ctx.fillStyle = textSecColor;
      ctx.textAlign = 'left';
      ctx.fillText(`(${s.stock_count})`, 10, y);
    });
  }

  // ----------------------------------------------------------------------
  // COUNTRY HEATMAP
  // ----------------------------------------------------------------------
  renderCountryHeatmap() {
    const container = document.getElementById('country-grid');
    if (!this.data.countries || !this.data.countries.countries) return;
    
    const countries = this.data.countries.countries;
    document.getElementById('country-badge').textContent = countries.length + ' countries';
    
    container.innerHTML = '';
    
    // Flag mapping
    const flags = {
      'United States': '🇺🇸', 'India': '🇮🇳', 'Japan': '🇯🇵', 
      'United Kingdom': '🇬🇧', 'Canada': '🇨🇦', 'Australia': '🇦🇺',
      'Brazil': '🇧🇷', 'South Korea': '🇰🇷', 'Germany': '🇩🇪',
      'China': '🇨🇳', 'Hong Kong': '🇭🇰', 'France': '🇫🇷',
      'Netherlands': '🇳🇱', 'Saudi Arabia': '🇸🇦'
    };
    
    countries.forEach((c, i) => {
      const card = document.createElement('div');
      card.className = 'country-card';
      card.style.animationDelay = (i * 0.05) + 's';
      
      // Background intensity
      const val = c.avg_change;
      let bg = '';
      if (val > 0) {
        const intensity = Math.min(0.2, val / 100);
        bg = `rgba(0, 245, 160, ${intensity})`;
      } else if (val < 0) {
        const intensity = Math.min(0.2, Math.abs(val) / 100);
        bg = `rgba(245, 0, 79, ${intensity})`;
      }
      if (bg) card.style.background = bg;
      
      const flag = flags[c.country] || '🌐';
      const pctPos = c.stock_count > 0 ? (c.positive / c.stock_count) * 100 : 0;
      
      const changeClass = val >= 0 ? 'text-gain' : 'text-loss';
      const changeStr = (val > 0 ? '+' : '') + val.toFixed(1) + '%';
      
      card.innerHTML = `
        <div class="cc-header">
          <span class="cc-flag">${flag}</span>
          <span class="cc-name" title="${c.country}">${c.country}</span>
        </div>
        <div class="cc-change ${changeClass}">${changeStr}</div>
        <div class="cc-meta">
          <span>${c.stock_count} stocks</span>
          <span style="color: ${pctPos > 50 ? 'var(--gain-primary)' : 'var(--loss-primary)'}">${pctPos.toFixed(0)}% up</span>
        </div>
        <div class="cc-breadth-bar">
          <div class="cc-breadth-fill" style="width: ${pctPos}%"></div>
        </div>
      `;
      
      container.appendChild(card);
    });
  }
}

document.addEventListener('DOMContentLoaded', () => {
  window.overview = new Overview();
});
