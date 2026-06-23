class App {
  constructor() {
    this.filters = {
      direction: 'gainers',
      period: '6M',
      sort: 'pct_change',
      limit: 25,
      page: 1
    };
    this.currentData = null;
    this.tvChart = null;
    this.tvSeries = null;
    this.tvVolume = null;
    this.init();
  }

  async init() {
    this.setupTheme();
    
    // Make sure other modules exist
    if (window.Filters) Filters.init(this);
    if (window.Search) Search.init(this);
    if (window.Table) Table.init(this);

    this.readURL();
    
    try {
      await Promise.all([
        this.fetchFiltersData(),
        this.fetchStatsData(),
        this.fetchData()
      ]);
    } catch (e) {
      console.error("Init error", e);
      this.showError('Failed to initialize. Please refresh the page.');
    }
    
    this.setupShortcuts();
    this.setupModal();
    this.setupKeyboardNav();
    
    document.getElementById('export-csv')?.addEventListener('click', () => this.exportCSV());
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
      btn.addEventListener('click', () => this.toggleTheme());
    }
  }

  toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme');
    const next = current === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('theme', next);
    const svg = document.getElementById('theme-toggle')?.querySelector('svg');
    if (svg) {
      svg.innerHTML = next === 'dark' 
        ? '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>'
        : '<circle cx="12" cy="12" r="5"></circle><line x1="12" y1="1" x2="12" y2="3"></line><line x1="12" y1="21" x2="12" y2="23"></line><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line><line x1="1" y1="12" x2="3" y2="12"></line><line x1="21" y1="12" x2="23" y2="12"></line><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line>';
    }
    this.syncTVChartTheme();
  }

  readURL() {
    const params = new URLSearchParams(window.location.search);
    for (const [key, value] of params.entries()) {
      if (value) this.filters[key] = value;
    }
    // Update UI to match filters
    if (window.Filters) Filters.syncUI(this.filters);
  }

  updateURL() {
    const params = new URLSearchParams();
    for (const key in this.filters) {
      if (this.filters[key] && this.filters[key] !== '' && this.filters[key] !== false) {
        if (key === 'limit' && this.filters[key] === 25) continue;
        if (key === 'page' && this.filters[key] === 1) continue;
        if (key === 'direction' && this.filters[key] === 'gainers') continue;
        params.set(key, this.filters[key]);
      }
    }
    const newUrl = window.location.pathname + '?' + params.toString();
    window.history.pushState({path: newUrl}, '', newUrl);
  }

  updateFilters(newFilters) {
    this.filters = { ...this.filters, ...newFilters, page: 1 }; // reset page on filter change
    this.updateURL();
    if (window.Filters) Filters.renderActivePills(this.filters);
    
    // Debounce fetch
    clearTimeout(this.fetchTimeout);
    this.fetchTimeout = setTimeout(() => this.fetchData(), 300);
  }
  
  changePage(newPage) {
    this.filters.page = newPage;
    this.updateURL();
    this.fetchData();
    // Scroll results area to top
    document.querySelector('.results-area')?.scrollTo({ top: 0, behavior: 'smooth' });
  }

  async fetchFiltersData() {
    try {
      const data = await window.SupabaseAPI.getFilters();
      if (window.Filters) Filters.populateAll(data);
    } catch (e) {
      console.error(e);
    }
  }

  async fetchStatsData() {
    try {
      const data = await window.SupabaseAPI.getStats();
      const el = document.getElementById('last-updated-time');
      if (el && data.last_updated) {
        el.textContent = 'Updated ' + this.timeAgo(data.last_updated);
      }
    } catch (e) {
      console.error(e);
    }
  }

  async fetchData() {
    if (window.Table) Table.showSkeleton();
    
    const params = new URLSearchParams();
    for (const key in this.filters) {
      if (this.filters[key] !== null && this.filters[key] !== undefined && this.filters[key] !== '') {
        params.set(key, this.filters[key]);
      }
    }
    
    try {
      if (!window.SupabaseAPI) {
        throw new Error("Supabase API is not loaded. Please check your connection.");
      }
      
      const data = await window.SupabaseAPI.getTopMovers(this.filters);
      this.currentData = data;
      const countEl = document.getElementById('results-count');
      if (countEl) {
        const total = data.total || 0;
        countEl.textContent = `${total.toLocaleString()} result${total !== 1 ? 's' : ''}`;
      }
      if (window.Table) Table.render(data);
    } catch (e) {
      console.error("FetchData Error:", e);
      this.showError(`Error: ${e.message || e.toString()}`);
      if (window.Table) Table.render({results: [], total: 0, page: 1, pages: 1});
    }
  }

  showError(message) {
    const countEl = document.getElementById('results-count');
    if (countEl) {
      countEl.textContent = 'Error: ' + message;
      countEl.style.color = 'var(--loss-primary)';
      console.error("UI Error Display:", message);
      setTimeout(() => { 
        countEl.style.color = ''; 
        if (countEl.textContent.startsWith('Error:')) countEl.textContent = '0 results';
      }, 5000);
    }
  }

  setupShortcuts() {
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        this.hideStockDetail();
        if (window.Search) Search.hideResults();
      }
      if (e.key === '/' && document.activeElement.tagName !== 'INPUT') {
        e.preventDefault();
        document.getElementById('stock-search')?.focus();
      }
    });
  }

  setupKeyboardNav() {
    document.addEventListener('keydown', (e) => {
      // Don't interfere with input fields
      if (document.activeElement.tagName === 'INPUT' || document.activeElement.tagName === 'SELECT') return;
      
      if (!window.Table) return;
      const rowCount = Table.getRowCount();
      if (rowCount === 0) return;

      if (e.key === 'ArrowDown' || e.key === 'j') {
        e.preventDefault();
        const next = Math.min(Table.activeRowIndex + 1, rowCount - 1);
        Table.highlightRow(next);
      } else if (e.key === 'ArrowUp' || e.key === 'k') {
        e.preventDefault();
        const prev = Math.max(Table.activeRowIndex - 1, 0);
        Table.highlightRow(prev);
      } else if (e.key === 'Enter') {
        const ticker = Table.getActiveRowTicker();
        if (ticker) {
          e.preventDefault();
          this.showStockDetail(ticker);
        }
      }
    });
  }

  setupModal() {
    const overlay = document.getElementById('stock-modal-overlay');
    const closeBtn = document.getElementById('close-modal');
    const aiBtn = document.getElementById('modal-btn-ai');
    
    if (overlay) overlay.addEventListener('click', () => this.hideStockDetail());
    if (closeBtn) closeBtn.addEventListener('click', () => this.hideStockDetail());
    if (aiBtn) aiBtn.addEventListener('click', () => this.fetchAIInsight());
  }

  async fetchAIInsight() {
    const ticker = document.getElementById('modal-ticker').textContent;
    const container = document.getElementById('modal-ai-insight');
    const content = document.getElementById('ai-insight-content');
    const btn = document.getElementById('modal-btn-ai');
    
    if (!ticker || !container || !content) return;
    
    // Show loading state
    container.classList.remove('hidden');
    content.innerHTML = '<div class="ai-loading"><div class="ai-loading-spinner"></div> Analyzing market data...</div>';
    btn.disabled = true;
    
    try {
      content.innerHTML = '<p class="text-secondary">AI Insight is currently offline in Serverless mode. Please integrate a cloud function.</p>';
    } catch (e) {
      console.error('AI Insight Error:', e);
      content.innerHTML = '<p class="text-loss">Network error while reaching AI service.</p>';
    } finally {
      btn.disabled = false;
    }
  }

  async showStockDetail(ticker) {
    const modal = document.getElementById('stock-modal');
    const overlay = document.getElementById('stock-modal-overlay');
    
    // Fetch detail
    try {
      const data = await window.SupabaseAPI.getStockDetail(ticker);
      if (data && data.stock) {
        // Unhide modal first so DOM elements have dimensions
        modal.classList.remove('hidden');
        overlay.classList.remove('hidden');
        
        this.populateModal(data);
        // brief timeout to allow display before transform animation
        requestAnimationFrame(() => {
          modal.classList.add('visible');
          overlay.classList.add('visible');
          
          setTimeout(() => {
             if (this.tvChart) {
                const container = document.getElementById('tv-chart-container');
                this.tvChart.resize(container.clientWidth, container.clientHeight);
                this.tvChart.timeScale().fitContent();
             }
          }, 300); // Wait for transition
        });
      } else {
        this.showError(`Could not load details for ${ticker}`);
      }
    } catch(e) {
      console.error(e);
      this.showError('Failed to load stock details');
    }
  }

  populateModal(data) {
    const s = data.stock;
    const g = data.gains[this.filters.period] || Object.values(data.gains)[0] || {};
    
    // Reset AI Insight
    document.getElementById('modal-ai-insight').classList.add('hidden');
    document.getElementById('ai-insight-content').innerHTML = '';
    
    document.getElementById('modal-name').textContent = s.name || s.ticker;
    document.getElementById('modal-ticker').textContent = s.ticker;
    document.getElementById('modal-sector').textContent = s.sector || '—';
    document.getElementById('modal-country').textContent = s.country || '—';
    document.getElementById('modal-exchange').textContent = s.exchange || '—';
    
    document.getElementById('modal-price').textContent = this.formatPrice(g.end_price, s.currency);
    document.getElementById('modal-mcap').textContent = this.formatNumber(s.market_cap, '$');
    document.getElementById('modal-pe').textContent = s.pe_ratio ? s.pe_ratio.toFixed(2) : '—';
    document.getElementById('modal-rsi').textContent = g.rsi_14 ? g.rsi_14.toFixed(1) : '—';
    
    // Colorize RSI
    const rsiEl = document.getElementById('modal-rsi');
    if (g.rsi_14) {
      rsiEl.className = 'stat-value font-mono';
      if (g.rsi_14 > 70) rsiEl.classList.add('text-loss');
      else if (g.rsi_14 < 30) rsiEl.classList.add('text-gain');
    }
    
    const vsSecEl = document.getElementById('modal-vs-sector');
    vsSecEl.textContent = g.vs_sector !== null && g.vs_sector !== undefined ? this.formatPercent(g.vs_sector) : '—';
    vsSecEl.className = 'stat-value font-mono ' + (g.vs_sector > 0 ? 'text-gain' : (g.vs_sector < 0 ? 'text-loss' : '')) + (g.vs_sector ? '' : ' dimmed');

    const vsCtyEl = document.getElementById('modal-vs-country');
    vsCtyEl.textContent = g.vs_country !== null && g.vs_country !== undefined ? this.formatPercent(g.vs_country) : '—';
    vsCtyEl.className = 'stat-value font-mono ' + (g.vs_country > 0 ? 'text-gain' : (g.vs_country < 0 ? 'text-loss' : '')) + (g.vs_country ? '' : ' dimmed');

    // New stats
    const volatilityEl = document.getElementById('modal-volatility');
    if (volatilityEl) volatilityEl.textContent = g.volatility ? (g.volatility * 100).toFixed(1) + '%' : '—';
    
    const drawdownEl = document.getElementById('modal-drawdown');
    if (drawdownEl) {
      drawdownEl.textContent = g.max_drawdown ? (g.max_drawdown * 100).toFixed(1) + '%' : '—';
      if (g.max_drawdown) drawdownEl.classList.add('text-loss');
    }
    
    const streakEl = document.getElementById('modal-gain-streak');
    if (streakEl) {
      const streak = g.gain_streak || s.gain_streak || 0;
      streakEl.textContent = streak > 0 ? streak + ' days' : '—';
      if (streak >= 5) streakEl.classList.add('text-gain');
    }
    
    const ma50El = document.getElementById('modal-ma50');
    if (ma50El) ma50El.textContent = g.ma_50 ? this.formatPrice(g.ma_50, '') : '—';
    
    const ma200El = document.getElementById('modal-ma200');
    if (ma200El) ma200El.textContent = g.ma_200 ? this.formatPrice(g.ma_200, '') : '—';
    
    const volEl = document.getElementById('modal-volume');
    if (volEl) volEl.textContent = g.volume ? this.formatNumber(g.volume) : (s.avg_volume ? this.formatNumber(s.avg_volume) : '—');

    // 52-week range
    const high52 = g.high_52w || 1;
    const low52 = g.low_52w || 0;
    const curr = g.end_price || 0;
    
    document.getElementById('modal-low52').textContent = this.formatPrice(low52, '');
    document.getElementById('modal-high52').textContent = this.formatPrice(high52, '');
    
    const ind = document.getElementById('modal-range-indicator');
    if (high52 > low52) {
      let pct = ((curr - low52) / (high52 - low52)) * 100;
      pct = Math.max(0, Math.min(100, pct));
      ind.style.left = `calc(${pct}% - 3px)`;
    }

    // Draw chart
    this.updateTVChart(data);
  }

  setupTVChart() {
    const container = document.getElementById('tv-chart-container');
    if (!container || typeof LightweightCharts === 'undefined') return;

    this.tvChart = LightweightCharts.createChart(container, {
      layout: {
        background: { type: 'solid', color: 'transparent' },
        textColor: 'rgba(136, 136, 160, 0.8)',
      },
      grid: {
        vertLines: { color: 'rgba(136, 136, 160, 0.1)' },
        horzLines: { color: 'rgba(136, 136, 160, 0.1)' },
      },
      crosshair: {
        mode: LightweightCharts.CrosshairMode.Normal,
      },
      rightPriceScale: {
        borderColor: 'rgba(136, 136, 160, 0.2)',
      },
      timeScale: {
        borderColor: 'rgba(136, 136, 160, 0.2)',
        timeVisible: true,
      },
    });

    this.tvSeries = this.tvChart.addCandlestickSeries({
      upColor: '#00f5a0',
      downColor: '#f5004f',
      borderVisible: false,
      wickUpColor: '#00f5a0',
      wickDownColor: '#f5004f',
    });

    this.tvVolume = this.tvChart.addHistogramSeries({
      priceFormat: {
        type: 'volume',
      },
      priceScaleId: '', // set as an overlay
    });

    this.tvChart.priceScale('').applyOptions({
      scaleMargins: {
        top: 0.8,
        bottom: 0,
      },
    });

    this.syncTVChartTheme();

    new ResizeObserver(entries => {
      if (entries.length === 0 || entries[0].target !== container) { return; }
      const newRect = entries[0].contentRect;
      this.tvChart.applyOptions({ height: newRect.height, width: newRect.width });
    }).observe(container);
  }

  syncTVChartTheme() {
    if (!this.tvChart) return;
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    this.tvChart.applyOptions({
      layout: {
        textColor: isDark ? 'rgba(255, 255, 255, 0.7)' : 'rgba(0, 0, 0, 0.7)',
      },
      grid: {
        vertLines: { color: isDark ? 'rgba(255, 255, 255, 0.05)' : 'rgba(0, 0, 0, 0.05)' },
        horzLines: { color: isDark ? 'rgba(255, 255, 255, 0.05)' : 'rgba(0, 0, 0, 0.05)' },
      }
    });
  }

  updateTVChart(data) {
    const container = document.getElementById('tv-chart-container');
    try {
      if (typeof LightweightCharts === 'undefined') {
          container.innerHTML = "<div style='color:red; padding:20px;'>ERROR: LightweightCharts library failed to load! Check your internet connection or adblocker.</div>";
          return;
      }
      if (!this.tvChart) {
          container.innerHTML = ''; // clear any old error messages
          this.setupTVChart();
      }
      if (!this.tvSeries || !this.tvVolume) {
          container.innerHTML = "<div style='color:red; padding:20px;'>ERROR: tvSeries or tvVolume were not created successfully!</div>";
          return;
      }

      let history = data.price_history || [];
      
      if (!history.length) {
        container.innerHTML = `<div class='empty-state' style='height:100%; justify-content:center; padding: 20px;'><div class='empty-icon'><svg viewBox='0 0 24 24' width='48' height='48' fill='none' stroke='currentColor' stroke-width='1.5'><path d='M3 3v18h18'></path><path d='M18 9l-5-5-4 4-5-5'></path></svg></div><div class='empty-text'>No Chart Data Available</div><div class='empty-sub'>Price history for ${data.stock?.ticker || 'this stock'} was not found in the database.</div></div>`;
        this.tvSeries.setData([]);
        this.tvVolume.setData([]);
        return;
      }

      // Sort ascending by date
      history = [...history].sort((a, b) => new Date(a.date) - new Date(b.date));

      const candleData = [];
      const volumeData = [];

      for (let i = 0; i < history.length; i++) {
        const row = history[i];
        const time = row.date.split('T')[0];
        
        // Ensure no NaN values which crash the chart
        const open = Number(row.open) || 0;
        const high = Number(row.high) || open;
        const low = Number(row.low) || open;
        const close = Number(row.close) || open;
        
        candleData.push({
          time: time,
          open: open,
          high: Math.max(high, open, close),
          low: Math.min(low, open, close),
          close: close
        });

        const isUp = close >= open;
        volumeData.push({
          time: time,
          value: Number(row.volume) || 0,
          color: isUp ? 'rgba(0, 245, 160, 0.5)' : 'rgba(245, 0, 79, 0.5)'
        });
      }

      console.log("[CHART DEBUG] First row:", candleData[0]);
      console.log("[CHART DEBUG] Last row:", candleData[candleData.length - 1]);

      // If there are exact duplicate dates, the chart will crash.
      // Deduplicate by time:
      const uniqueCandles = [];
      const uniqueVolumes = [];
      const seenTimes = new Set();
      for (let i = 0; i < candleData.length; i++) {
          if (!seenTimes.has(candleData[i].time)) {
              seenTimes.add(candleData[i].time);
              uniqueCandles.push(candleData[i]);
              uniqueVolumes.push(volumeData[i]);
          }
      }

      this.tvSeries.setData(uniqueCandles);
      this.tvVolume.setData(uniqueVolumes);
      
      // ensure we clear any error message
      const errDiv = document.getElementById('chart-error-msg');
      if (errDiv) errDiv.remove();

    } catch (e) {
      console.error("[CHART ERROR]", e);
      // Display the error physically on the UI
      if (container) {
          let errDiv = document.getElementById('chart-error-msg');
          if (!errDiv) {
              errDiv = document.createElement('div');
              errDiv.id = 'chart-error-msg';
              errDiv.style.color = '#f5004f';
              errDiv.style.padding = '20px';
              errDiv.style.position = 'absolute';
              errDiv.style.zIndex = '999';
              container.appendChild(errDiv);
          }
          errDiv.innerHTML = `<strong>Chart Rendering Error:</strong><br/>${e.message}`;
      }
    }
    // Only fit content if chart was actually created
    if (this.tvChart) {
        this.tvChart.timeScale().fitContent();
    }
  }

  hideStockDetail() {
    const modal = document.getElementById('stock-modal');
    const overlay = document.getElementById('stock-modal-overlay');
    if (modal) {
      modal.classList.remove('visible');
      overlay?.classList.remove('visible');
      setTimeout(() => {
        modal.classList.add('hidden');
        if (overlay) overlay.classList.add('hidden');
        document.getElementById('modal-ai-insight')?.classList.add('hidden');
      }, 300);
    }
  }

  exportCSV() {
    if (!this.currentData || !this.currentData.results.length) return;
    
    const cols = ['ticker', 'name', 'sector', 'country', 'pct_change', 'end_price', 'market_cap'];
    let csv = cols.join(',') + '\n';
    
    this.currentData.results.forEach(r => {
      const row = cols.map(c => `"${r[c] || ''}"`);
      csv += row.join(',') + '\n';
    });
    
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `topgainers_${this.filters.period}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
  }

  formatNumber(n, prefix='') {
    if (!n) return '-';
    if (n >= 1e12) return prefix + (n / 1e12).toFixed(2) + 'T';
    if (n >= 1e9) return prefix + (n / 1e9).toFixed(2) + 'B';
    if (n >= 1e6) return prefix + (n / 1e6).toFixed(2) + 'M';
    if (n >= 1e3) return prefix + (n / 1e3).toFixed(2) + 'K';
    return prefix + n.toFixed(2);
  }

  formatPercent(n) {
    if (n === null || n === undefined) return '-';
    const sign = n > 0 ? '+' : '';
    return sign + n.toFixed(2) + '%';
  }

  formatPrice(n, currency) {
    if (n === null || n === undefined) return '-';
    const currStr = currency ? currency + ' ' : '';
    try {
      return currStr + Number(n).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    } catch {
      return currStr + n.toFixed(2);
    }
  }

  timeAgo(dateString) {
    const d = new Date(dateString);
    const now = new Date();
    const diff = (now - d) / 1000;
    if (diff < 60) return 'just now';
    if (diff < 3600) return Math.floor(diff/60) + 'm ago';
    if (diff < 86400) return Math.floor(diff/3600) + 'h ago';
    return Math.floor(diff/86400) + 'd ago';
  }
}

document.addEventListener('DOMContentLoaded', () => {
  window.app = new App();
});
