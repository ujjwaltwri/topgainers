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
    this.fxRates = {};
    this.loadFxRates(); // fire-and-forget, table re-renders when ready

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

      if (window.SupabaseAPI && window.SupabaseAPI.subscribeToUpdates) {
        window.SupabaseAPI.subscribeToUpdates((newRecord) => this.handleRealtimeUpdate(newRecord));
      }

      this.renderMarquee();
    } catch (e) {
      console.error("Init error", e);
      this.showError('Failed to initialize. Please refresh the page.');
    }

    this.setupShortcuts();
    this.setupModal();
    this.setupModalTabs();
    this.setupAlerts();
    this.setupCompareAI();
    this.setupKeyboardNav();
    this.startLiveRefresh();
    this.renderMarketClocks();
    setInterval(() => this.renderMarketClocks(), 60000);

    document.getElementById('export-csv')?.addEventListener('click', () => this.exportCSV());

    // Deep-link: open modal if ?ticker=XXXX
    const urlParams = new URLSearchParams(window.location.search);
    const tickerParam = urlParams.get('ticker');
    if (tickerParam) {
      setTimeout(() => this.showStockDetail(tickerParam.toUpperCase()), 800);
    }
  }

  // ── Market Clock ──────────────────────────────────
  renderMarketClocks() {
    const container = document.getElementById('market-clocks');
    if (!container) return;

    const now = new Date();
    const utcH = now.getUTCHours();
    const utcM = now.getUTCMinutes();
    const utcMins = utcH * 60 + utcM;
    const day = now.getUTCDay(); // 0=Sun, 6=Sat

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
      // Open markets: show prominently. Closed: just a dim label, no "CLOSED" noise.
      return `<div class="market-clock-item ${isOpen ? 'open' : 'closed'}"><span class="market-clock-dot"></span>${s.name}${isOpen ? ' OPEN' : ''}</div>`;
    }).join('');
  }

  handleRealtimeUpdate(newRecord) {
    if (!this.currentData || !this.currentData.results) return;
    if (newRecord.period !== this.filters.period) return;

    const isGainer = this.filters.direction === 'gainers';
    if ((isGainer && newRecord.pct_change <= 0) || (!isGainer && newRecord.pct_change >= 0)) return;
    if (this.filters.sector && newRecord.sector !== this.filters.sector) return;
    if (this.filters.country && newRecord.country !== this.filters.country) return;

    const existsIndex = this.currentData.results.findIndex(r => r.ticker === newRecord.ticker);
    if (existsIndex >= 0) {
      this.currentData.results[existsIndex] = newRecord;
    } else {
      this.currentData.results.push(newRecord);
    }

    const sortField = this.filters.sort || 'pct_change';
    this.currentData.results.sort((a, b) => {
      let valA = a[sortField];
      let valB = b[sortField];
      if (typeof valA === 'string') valA = parseFloat(valA.replace(/[^0-9.-]+/g, "")) || 0;
      if (typeof valB === 'string') valB = parseFloat(valB.replace(/[^0-9.-]+/g, "")) || 0;
      return isGainer ? valB - valA : valA - valB;
    });

    this.currentData.results = this.currentData.results.slice(0, this.filters.limit || 25);

    if (this.filters.page === 1) {
      if (window.Table) Table.render(this.currentData);

      setTimeout(() => {
        const tr = document.querySelector(`tr[data-ticker="${newRecord.ticker}"]`);
        if (tr) {
          tr.classList.add('flash-row');
          setTimeout(() => tr.classList.remove('flash-row'), 1500);
        }
      }, 50);
    }
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
      if (key !== 'ticker' && value) this.filters[key] = value;
    }
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
    const newUrl = window.location.pathname + (params.toString() ? '?' + params.toString() : '');
    window.history.replaceState({path: newUrl}, '', newUrl);
  }

  updateFilters(newFilters) {
    const periodChanged = newFilters.period && newFilters.period !== this.filters.period;
    this.filters = { ...this.filters, ...newFilters, page: 1 };
    this.updateURL();
    if (window.Filters) Filters.renderActivePills(this.filters);

    clearTimeout(this.fetchTimeout);
    this.fetchTimeout = setTimeout(() => {
      this.fetchData();
      if (periodChanged || !this.marqueeLoaded) {
        this.renderMarquee();
      }
    }, 300);
  }

  async renderMarquee() {
    const container = document.getElementById('global-marquee');
    const content = document.getElementById('marquee-content');
    if (!container || !content) return;

    // Only show loading placeholder on very first render
    if (!this.marqueeLoaded) {
      container.style.display = 'block';
      content.innerHTML = '<span class="text-secondary">Fetching Global Markets...</span>';
    }

    try {
      if (!window.SupabaseAPI || !window.SupabaseAPI.getMarqueeData) return;

      const data = await window.SupabaseAPI.getMarqueeData(this.filters.period);
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

  changePage(newPage) {
    this.filters.page = newPage;
    this.updateURL();
    this.fetchData();
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

  async fetchData() {
    if (window.Table) Table.showSkeleton();

    try {
      if (!window.SupabaseAPI) throw new Error("Supabase API is not loaded.");

      const data = await window.SupabaseAPI.getTopMovers(this.filters);
      this.currentData = data;
      const countEl = document.getElementById('results-count');
      if (countEl) {
        const shown = data.results ? data.results.length : 0;
        countEl.textContent = shown > 0 ? `Showing ${shown}` : 'No results';
      }

      // Show session label for 1D
      const asOfEl = document.getElementById('data-as-of');
      if (asOfEl && data.results && data.results.length > 0) {
        const sample = data.results.find(r => r.end_date);
        if (sample && this.filters.period === '1D') {
          const d = new Date(sample.end_date);
          asOfEl.textContent = `Session: ${d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}`;
          asOfEl.style.display = 'inline';
        } else {
          asOfEl.style.display = 'none';
        }
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
      setTimeout(() => {
        countEl.style.color = '';
        if (countEl.textContent.startsWith('Error:')) countEl.textContent = '0 results';
      }, 5000);
    }
  }

  setupShortcuts() {
    const overlay = document.getElementById('shortcuts-overlay');

    document.addEventListener('keydown', (e) => {
      const inInput = document.activeElement.tagName === 'INPUT' || document.activeElement.tagName === 'SELECT';

      // Show shortcut panel
      if (e.key === '?' && !inInput) {
        e.preventDefault();
        if (overlay) overlay.classList.toggle('visible');
        return;
      }

      if (e.key === 'Escape') {
        this.hideStockDetail();
        if (window.Search) Search.hideResults();
        if (overlay) overlay.classList.remove('visible');
        return;
      }

      if (e.key === '/' && !inInput) {
        e.preventDefault();
        document.getElementById('stock-search')?.focus();
        return;
      }

      if ((e.ctrlKey || e.metaKey) && e.key === 'e') {
        e.preventDefault();
        this.exportCSV();
        return;
      }

      if (!inInput) {
        if (e.key === 'g' || e.key === 'G') {
          e.preventDefault();
          const btn = document.querySelector('[data-dir="gainers"]');
          btn?.click();
        } else if (e.key === 'l' || e.key === 'L') {
          e.preventDefault();
          const btn = document.querySelector('[data-dir="losers"]');
          btn?.click();
        }
      }
    });

    // Close shortcuts panel on outside click
    if (overlay) {
      overlay.addEventListener('click', (e) => {
        if (e.target === overlay) overlay.classList.remove('visible');
      });
    }
  }

  setupKeyboardNav() {
    document.addEventListener('keydown', (e) => {
      if (document.activeElement.tagName === 'INPUT' || document.activeElement.tagName === 'SELECT') return;
      if (!window.Table) return;
      const rowCount = Table.getRowCount();
      if (rowCount === 0) return;

      if (e.key === 'ArrowDown' || e.key === 'j') {
        e.preventDefault();
        Table.highlightRow(Math.min(Table.activeRowIndex + 1, rowCount - 1));
      } else if (e.key === 'ArrowUp' || e.key === 'k') {
        e.preventDefault();
        Table.highlightRow(Math.max(Table.activeRowIndex - 1, 0));
      } else if (e.key === 'Enter') {
        const ticker = Table.getActiveRowTicker();
        if (ticker) { e.preventDefault(); this.showStockDetail(ticker); }
      }
    });
  }

  setupCompareAI() {
    const btn = document.getElementById('compare-ai-btn');
    const countSpan = document.getElementById('compare-count');
    const modal = document.getElementById('compare-modal');
    const overlay = document.getElementById('compare-modal-overlay');
    const closeBtn = document.getElementById('close-compare-modal');
    const content = document.getElementById('compare-insight-content');

    if (closeBtn) closeBtn.addEventListener('click', () => { modal.classList.add('hidden'); overlay.classList.add('hidden'); });
    if (overlay) overlay.addEventListener('click', () => { modal.classList.add('hidden'); overlay.classList.add('hidden'); });

    document.getElementById('table-body')?.addEventListener('change', (e) => {
      if (e.target.classList.contains('row-checkbox')) {
        const checked = document.querySelectorAll('.row-checkbox:checked');
        if (checked.length >= 2) {
          btn.style.display = 'inline-flex';
          countSpan.textContent = checked.length;
        } else {
          btn.style.display = 'none';
        }
      }
    });

    if (btn) btn.addEventListener('click', async () => {
      const checkedBoxes = Array.from(document.querySelectorAll('.row-checkbox:checked'));
      const stocksData = checkedBoxes.map(cb => ({
        ticker: cb.value,
        name: cb.dataset.name,
        sector: cb.dataset.sector,
        pct_change: cb.dataset.pct,
        market_cap: cb.dataset.mcap,
        pe_ratio: cb.dataset.pe,
        volume_ratio: cb.dataset.vol
      }));

      modal.classList.remove('hidden');
      overlay.classList.remove('hidden');
      content.innerHTML = '<div class="ai-loading"><div class="ai-loading-spinner"></div> Analyzing selected stocks...</div>';

      try {
        const { data, error } = await window.supabaseClient.functions.invoke('ai-compare', {
          body: { stocks: stocksData }
        });
        if (error) throw error;

        let htmlText = (data.result || 'No insight available.')
          .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
          .replace(/\n/g, '<br/>');

        let refHtml = `<div class="ai-references" style="margin-top: 20px; border-top: 1px solid rgba(255,255,255,0.1); padding-top: 16px; font-size: 13px; color: var(--text-secondary);">
          <div style="margin-bottom: 8px; font-weight: 500; color: var(--text-primary);">Data Points Accounted For:</div>
          <ul style="padding-left: 20px; margin-bottom: 12px; margin-top: 0; opacity: 0.85;">`;
        stocksData.forEach(s => {
          refHtml += `<li><strong>${s.name || s.ticker}</strong>: ${s.sector} | Gain: ${s.pct_change}% | Cap: ${s.market_cap || 'N/A'} | P/E: ${s.pe_ratio || 'N/A'}</li>`;
        });
        refHtml += `</ul>`;
        if (data.news && data.news.length > 0) {
          refHtml += `<div style="margin-bottom: 4px; font-weight: 500; color: var(--text-primary);">Google Search References:</div>
          <ul style="padding-left: 20px; margin-top: 0; opacity: 0.85;">
            ${data.news.map(n => `<li><a href="${n.link}" target="_blank" style="color: var(--accent-primary); text-decoration: none;">${n.title}</a> <span style="opacity:0.7">(${n.publisher})</span></li>`).join('')}
          </ul>`;
        }
        refHtml += `</div>`;
        content.innerHTML = `<p>${htmlText}</p>${refHtml}`;
      } catch (err) {
        console.error('Compare AI error:', err);
        content.innerHTML = '<p class="text-loss">Failed to generate AI comparison.</p>';
      }
    });
  }

  setupModal() {
    const overlay = document.getElementById('stock-modal-overlay');
    const closeBtn = document.getElementById('close-modal');
    const aiBtn = document.getElementById('modal-btn-ai');
    const shareBtn = document.getElementById('modal-share-btn');

    if (overlay) overlay.addEventListener('click', () => this.hideStockDetail());
    if (closeBtn) closeBtn.addEventListener('click', () => this.hideStockDetail());
    if (aiBtn) aiBtn.addEventListener('click', () => this.fetchAIInsight());
    if (shareBtn) shareBtn.addEventListener('click', () => {
      const ticker = document.getElementById('modal-ticker')?.textContent;
      if (ticker) {
        const url = window.location.origin + window.location.pathname + '?ticker=' + encodeURIComponent(ticker);
        navigator.clipboard.writeText(url).then(() => {
          shareBtn.style.color = 'var(--gain-primary)';
          setTimeout(() => shareBtn.style.color = '', 1500);
        }).catch(() => {
          prompt('Copy this link:', url);
        });
      }
    });
  }

  setupModalTabs() {
    document.querySelectorAll('.modal-tab').forEach(tab => {
      tab.addEventListener('click', () => this.switchModalTab(tab.dataset.tab));
    });
  }

  async fetchAIInsight() {
    const ticker = document.getElementById('modal-ticker').textContent;
    const name = document.getElementById('modal-name').textContent;
    const stock = window.app.currentData?.results?.find(r => r.ticker === ticker) || {};
    const pct_change = stock.pct_change || 0;

    const container = document.getElementById('modal-ai-insight');
    const content = document.getElementById('ai-insight-content');
    const btn = document.getElementById('modal-btn-ai');

    if (!ticker || !container || !content) return;

    container.classList.remove('hidden');
    content.innerHTML = '<div class="ai-loading"><div class="ai-loading-spinner"></div> Analyzing market data...</div>';
    btn.disabled = true;

    try {
      const { data, error } = await window.supabaseClient.functions.invoke('ai-summary', {
        body: {
          ticker, name, pct_change,
          sector: stock.sector,
          industry: stock.industry,
          market_cap: stock.market_cap,
          pe_ratio: stock.pe_ratio,
          at_52w_high: stock.at_52w_high,
          at_52w_low: stock.at_52w_low,
          volume_ratio: stock.volume_ratio
        }
      });
      if (error) throw error;

      let htmlText = (data.result || 'No insight available.')
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\n/g, '<br/>');

      let refHtml = `<div class="ai-references" style="margin-top: 20px; border-top: 1px solid rgba(255,255,255,0.1); padding-top: 16px; font-size: 13px; color: var(--text-secondary);">
        <div style="margin-bottom: 8px; font-weight: 500; color: var(--text-primary);">Data Points & Context Analyzed:</div>
        <ul style="padding-left: 20px; margin-bottom: 12px; margin-top: 0; opacity: 0.85;">
          <li><strong>Fundamentals:</strong> ${stock.sector || 'N/A'} / ${stock.industry || 'N/A'} | Cap: ${stock.market_cap || 'N/A'} | P/E: ${stock.pe_ratio || 'N/A'}</li>
          <li><strong>Technicals:</strong> Volume Surge: ${stock.volume_ratio}x ${stock.at_52w_high ? '| 52W High' : ''} ${stock.at_52w_low ? '| 52W Low' : ''}</li>
        </ul>`;
      if (data.news && data.news.length > 0) {
        refHtml += `<div style="margin-bottom: 4px; font-weight: 500; color: var(--text-primary);">News Articles Referenced:</div>
        <ul style="padding-left: 20px; margin-top: 0; opacity: 0.85;">
          ${data.news.map(n => `<li><a href="${n.link}" target="_blank" style="color: var(--accent-primary); text-decoration: none;">${n.title}</a> <span style="opacity:0.7">(${n.publisher})</span></li>`).join('')}
        </ul>`;
      } else {
        refHtml += `<div style="opacity: 0.7; font-style: italic;">No specific news articles referenced. Analysis based strictly on technical/fundamental data.</div>`;
      }
      refHtml += `</div>`;
      content.innerHTML = `<p>${htmlText}</p>${refHtml}`;
    } catch (e) {
      console.error('AI Insight Error:', e);
      content.innerHTML = '<p class="text-loss">Failed to reach AI service or generate insight.</p>';
    } finally {
      btn.disabled = false;
    }
  }

  async showStockDetail(ticker) {
    const modal = document.getElementById('stock-modal');
    const overlay = document.getElementById('stock-modal-overlay');

    try {
      const data = await window.SupabaseAPI.getStockDetail(ticker);
      if (data && data.stock) {
        modal.classList.remove('hidden');
        overlay.classList.remove('hidden');

        this.populateModal(data);
        requestAnimationFrame(() => {
          modal.classList.add('visible');
          overlay.classList.add('visible');

          setTimeout(() => {
            if (this.tvChart) {
              const container = document.getElementById('tv-chart-container');
              this.tvChart.resize(container.clientWidth, container.clientHeight);
              this.tvChart.timeScale().fitContent();
            }
          }, 300);
        });
      } else {
        this.showError(`Could not load details for ${ticker}`);
      }
    } catch (e) {
      console.error(e);
      this.showError('Failed to load stock details');
    }
  }

  populateModal(data) {
    const s = data.stock;
    const g = data.gains[this.filters.period] || Object.values(data.gains)[0] || {};

    document.getElementById('modal-ai-insight').classList.add('hidden');
    document.getElementById('ai-insight-content').innerHTML = '';

    document.getElementById('modal-name').textContent = s.name || s.ticker;
    document.getElementById('modal-ticker').textContent = s.ticker;
    document.getElementById('modal-sector').textContent = s.sector || '—';
    document.getElementById('modal-country').textContent = s.country || '—';
    document.getElementById('modal-exchange').textContent = s.exchange || '—';

    document.getElementById('modal-price').textContent = this.formatPrice(g.end_price, s.currency);
    document.getElementById('modal-mcap').textContent = this.formatMarketCap(s.market_cap, s.currency);
    document.getElementById('modal-pe').textContent = s.pe_ratio ? s.pe_ratio.toFixed(2) : '—';
    document.getElementById('modal-rsi').textContent = g.rsi_14 ? g.rsi_14.toFixed(1) : '—';

    const rsiEl = document.getElementById('modal-rsi');
    if (g.rsi_14) {
      rsiEl.className = 'stat-value font-mono';
      if (g.rsi_14 > 70) rsiEl.classList.add('text-loss');
      else if (g.rsi_14 < 30) rsiEl.classList.add('text-gain');
    }

    const vsSecEl = document.getElementById('modal-vs-sector');
    vsSecEl.textContent = g.vs_sector !== null && g.vs_sector !== undefined ? this.formatPercent(g.vs_sector) : '—';
    vsSecEl.className = 'stat-value font-mono ' + (g.vs_sector > 0 ? 'text-gain' : (g.vs_sector < 0 ? 'text-loss' : ''));

    const vsCtyEl = document.getElementById('modal-vs-country');
    vsCtyEl.textContent = g.vs_country !== null && g.vs_country !== undefined ? this.formatPercent(g.vs_country) : '—';
    vsCtyEl.className = 'stat-value font-mono ' + (g.vs_country > 0 ? 'text-gain' : (g.vs_country < 0 ? 'text-loss' : ''));

    const volatilityEl = document.getElementById('modal-volatility');
    if (volatilityEl) volatilityEl.textContent = g.volatility_30d ? (g.volatility_30d * 100).toFixed(1) + '%' : '—';

    const drawdownEl = document.getElementById('modal-drawdown');
    if (drawdownEl) {
      drawdownEl.textContent = g.max_drawdown ? (g.max_drawdown * 100).toFixed(1) + '%' : '—';
      if (g.max_drawdown) drawdownEl.classList.add('text-loss');
    }

    const streakEl = document.getElementById('modal-gain-streak');
    if (streakEl) {
      const streak = g.gain_streak || s.gain_streak || 0;
      streakEl.textContent = streak > 0 ? `${streak} days${streak >= 10 ? ' HOT' : ''}` : '—';
      if (streak >= 5) streakEl.classList.add('text-gain');
    }

    const ma50El = document.getElementById('modal-ma50');
    if (ma50El) ma50El.textContent = g.ma_50 ? this.formatPrice(g.ma_50, '') : '—';

    const ma200El = document.getElementById('modal-ma200');
    if (ma200El) ma200El.textContent = g.ma_200 ? this.formatPrice(g.ma_200, '') : '—';

    const volEl = document.getElementById('modal-volume');
    if (volEl) volEl.textContent = g.volume ? this.formatNumber(g.volume) : (s.avg_volume ? this.formatNumber(s.avg_volume) : '—');

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

    this.updateTVChart(data);

    // Populate fundamentals tab
    this.populateFundamentals(s);

    // Reset tabs to Overview
    this.switchModalTab('overview');

    // Fetch news async (don't await — let it populate in background)
    this.fetchStockNews(s.ticker);

    // Load saved alert for this ticker
    this.loadAlertForTicker(s.ticker);
  }

  switchModalTab(tabName) {
    document.querySelectorAll('.modal-tab').forEach(t => t.classList.toggle('active', t.dataset.tab === tabName));
    document.querySelectorAll('.modal-tab-content').forEach(c => {
      const id = c.id.replace('modal-tab-', '');
      c.classList.toggle('hidden', id !== tabName);
    });
  }

  async fetchStockNews(ticker) {
    const listEl = document.getElementById('modal-news-list');
    if (!listEl) return;
    listEl.innerHTML = '<div class="news-loading">Loading news...</div>';

    try {
      const { data, error } = await window.supabaseClient.functions.invoke('stock-news', { body: { ticker } });
      if (error) throw error;
      const items = data?.news || [];
      this.renderNews(items);
      this.renderSentimentBadge(items);
    } catch (e) {
      listEl.innerHTML = '<div class="news-empty">Could not load news.</div>';
    }
  }

  renderNews(items) {
    const listEl = document.getElementById('modal-news-list');
    if (!listEl) return;
    if (!items.length) {
      listEl.innerHTML = '<div class="news-empty">No recent news found.</div>';
      return;
    }
    listEl.innerHTML = items.map(n => {
      const ts = n.providerPublishTime ? new Date(n.providerPublishTime * 1000) : null;
      const ago = ts ? this.timeAgo(ts.toISOString()) : '';
      const safeTitle = n.title.replace(/</g, '&lt;').replace(/>/g, '&gt;');
      const safePublisher = (n.publisher || '').replace(/</g, '&lt;');
      return `<a class="news-item" href="${n.link}" target="_blank" rel="noopener noreferrer">
        <div class="news-title">${safeTitle}</div>
        <div class="news-meta">${safePublisher}${ago ? ' · ' + ago : ''}</div>
      </a>`;
    }).join('');
  }

  renderSentimentBadge(items) {
    const badge = document.getElementById('modal-sentiment-badge');
    if (!badge) return;
    if (!items.length) { badge.classList.add('hidden'); return; }

    const POSITIVE = ['surge', 'rally', 'gain', 'beat', 'record', 'growth', 'profit', 'upgrade', 'buy', 'rise', 'jump', 'soar', 'boost', 'strong'];
    const NEGATIVE = ['drop', 'fall', 'miss', 'loss', 'downgrade', 'sell', 'crash', 'cut', 'decline', 'weak', 'sink', 'plunge', 'concern', 'warn'];

    let score = 0;
    items.forEach(n => {
      const text = (n.title || '').toLowerCase();
      POSITIVE.forEach(w => { if (text.includes(w)) score++; });
      NEGATIVE.forEach(w => { if (text.includes(w)) score--; });
    });

    badge.classList.remove('hidden', 'bullish', 'bearish', 'neutral');
    if (score > 0) { badge.classList.add('bullish'); badge.textContent = 'BULLISH'; }
    else if (score < 0) { badge.classList.add('bearish'); badge.textContent = 'BEARISH'; }
    else { badge.classList.add('neutral'); badge.textContent = 'NEUTRAL'; }
  }

  populateFundamentals(s) {
    const fmt = (v, suffix = '') => (v !== null && v !== undefined) ? (typeof v === 'number' ? v.toFixed(2) + suffix : v) : '—';
    const fmtPct = v => (v !== null && v !== undefined) ? (v * 100).toFixed(1) + '%' : '—';
    const fmtB = v => (v !== null && v !== undefined) ? this.formatMarketCap(v, s.currency) : '—';

    const set = (id, val, cls = '') => {
      const el = document.getElementById(id);
      if (!el) return;
      el.textContent = val;
      if (cls) el.className = 'fund-value font-mono ' + cls;
    };

    set('modal-eps', fmt(s.trailing_eps));
    set('modal-rev-growth', fmtPct(s.revenue_growth), s.revenue_growth > 0 ? 'text-gain' : (s.revenue_growth < 0 ? 'text-loss' : ''));
    set('modal-earn-growth', fmtPct(s.earnings_growth), s.earnings_growth > 0 ? 'text-gain' : (s.earnings_growth < 0 ? 'text-loss' : ''));
    set('modal-de', fmt(s.debt_to_equity));
    set('modal-fcf', fmtB(s.free_cashflow));
    set('modal-margin', fmtPct(s.profit_margin), s.profit_margin > 0 ? 'text-gain' : '');
    set('modal-roe', fmtPct(s.return_on_equity), s.return_on_equity > 0 ? 'text-gain' : (s.return_on_equity < 0 ? 'text-loss' : ''));
    set('modal-div-yield', s.dividend_yield ? fmtPct(s.dividend_yield) : '—');
    set('modal-rec', s.recommendation ? s.recommendation.toUpperCase() : '—');

    const earnEl = document.getElementById('modal-earn-date');
    if (earnEl) {
      if (s.earnings_date) {
        const d = new Date(typeof s.earnings_date === 'number' ? s.earnings_date * 1000 : s.earnings_date);
        earnEl.textContent = isNaN(d) ? '—' : d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
      } else {
        earnEl.textContent = '—';
      }
    }
  }

  loadAlertForTicker(ticker) {
    const input = document.getElementById('alert-price-input');
    const statusEl = document.getElementById('alert-status');
    if (!input || !statusEl) return;

    const alerts = JSON.parse(localStorage.getItem('price_alerts') || '[]');
    const existing = alerts.find(a => a.ticker === ticker);
    if (existing) {
      input.value = existing.price;
      statusEl.textContent = 'Alert set at ' + existing.price;
    } else {
      input.value = '';
      statusEl.textContent = '';
    }
  }

  setupAlerts() {
    const btn = document.getElementById('alert-set-btn');
    const input = document.getElementById('alert-price-input');
    const statusEl = document.getElementById('alert-status');
    if (!btn || !input) return;

    btn.addEventListener('click', async () => {
      const ticker = document.getElementById('modal-ticker')?.textContent?.trim();
      const price = parseFloat(input.value);
      if (!ticker || isNaN(price) || price <= 0) {
        if (statusEl) { statusEl.textContent = 'Enter a valid price.'; statusEl.style.color = 'var(--loss-primary)'; }
        return;
      }

      if (Notification.permission === 'default') {
        await Notification.requestPermission();
      }

      const alerts = JSON.parse(localStorage.getItem('price_alerts') || '[]');
      const filtered = alerts.filter(a => a.ticker !== ticker);
      const currentPrice = parseFloat(document.getElementById('modal-price')?.textContent?.replace(/[^0-9.]/g, '') || '0');
      const direction = price > currentPrice ? 'above' : 'below';
      filtered.push({ ticker, price, direction });
      localStorage.setItem('price_alerts', JSON.stringify(filtered));

      if (statusEl) {
        statusEl.textContent = `Alert set: notify when ${ticker} goes ${direction} ${price}`;
        statusEl.style.color = 'var(--gain-primary)';
      }
    });
  }

  checkPriceAlerts(quotes) {
    const alerts = JSON.parse(localStorage.getItem('price_alerts') || '[]');
    if (!alerts.length) return;
    const remaining = [];
    let changed = false;

    alerts.forEach(alert => {
      const quote = quotes[alert.ticker];
      if (!quote) { remaining.push(alert); return; }
      const currentPrice = quote.price;
      const triggered = (alert.direction === 'above' && currentPrice >= alert.price) ||
                        (alert.direction === 'below' && currentPrice <= alert.price);
      if (triggered) {
        changed = true;
        if (Notification.permission === 'granted') {
          new Notification(`TopGainers Alert: ${alert.ticker}`, {
            body: `Price ${alert.direction === 'above' ? 'reached' : 'dropped to'} ${currentPrice.toFixed(2)} (target: ${alert.price})`,
          });
        }
      } else {
        remaining.push(alert);
      }
    });

    if (changed) localStorage.setItem('price_alerts', JSON.stringify(remaining));
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
      crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
      rightPriceScale: { borderColor: 'rgba(136, 136, 160, 0.2)' },
      timeScale: { borderColor: 'rgba(136, 136, 160, 0.2)', timeVisible: true },
    });

    this.tvSeries = this.tvChart.addCandlestickSeries({
      upColor: '#00f5a0',
      downColor: '#f5004f',
      borderVisible: false,
      wickUpColor: '#00f5a0',
      wickDownColor: '#f5004f',
    });

    this.tvVolume = this.tvChart.addHistogramSeries({
      priceFormat: { type: 'volume' },
      priceScaleId: '',
    });

    this.tvChart.priceScale('').applyOptions({ scaleMargins: { top: 0.8, bottom: 0 } });
    this.syncTVChartTheme();

    new ResizeObserver(entries => {
      if (entries.length === 0 || entries[0].target !== container) return;
      const newRect = entries[0].contentRect;
      this.tvChart.applyOptions({ height: newRect.height, width: newRect.width });
    }).observe(container);
  }

  syncTVChartTheme() {
    if (!this.tvChart) return;
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    this.tvChart.applyOptions({
      layout: { textColor: isDark ? 'rgba(255,255,255,0.7)' : 'rgba(0,0,0,0.7)' },
      grid: {
        vertLines: { color: isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.05)' },
        horzLines: { color: isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.05)' },
      }
    });
  }

  updateTVChart(data) {
    const container = document.getElementById('tv-chart-container');
    try {
      if (typeof LightweightCharts === 'undefined') {
        container.innerHTML = "<div style='color:red; padding:20px;'>ERROR: LightweightCharts library failed to load!</div>";
        return;
      }
      if (this.tvChart && (container.innerHTML.includes('empty-state') || container.innerHTML.includes('ERROR:'))) {
        try { this.tvChart.remove(); } catch (e) {}
        this.tvChart = null;
      }

      if (!this.tvChart) {
        container.innerHTML = '';
        this.setupTVChart();
      }
      if (!this.tvSeries || !this.tvVolume) {
        container.innerHTML = "<div style='color:red; padding:20px;'>ERROR: chart series not created.</div>";
        return;
      }

      let history = data.price_history || [];

      if (!history.length) {
        if (this.tvChart) { try { this.tvChart.remove(); } catch (e) {} this.tvChart = null; }
        container.innerHTML = `<div class='empty-state' style='height:100%; justify-content:center; padding: 20px;'><div class='empty-icon'><svg viewBox='0 0 24 24' width='48' height='48' fill='none' stroke='currentColor' stroke-width='1.5'><path d='M3 3v18h18'></path><path d='M18 9l-5-5-4 4-5-5'></path></svg></div><div class='empty-text'>No Chart Data Available</div><div class='empty-sub'>Price history for ${data.stock?.ticker || 'this stock'} was not found in the database.</div></div>`;
        return;
      }

      history = [...history].sort((a, b) => new Date(a.date) - new Date(b.date));

      const candleData = [];
      const volumeData = [];

      for (let i = 0; i < history.length; i++) {
        const row = history[i];
        const time = row.date.split('T')[0];
        const open = Number(row.open) || 0;
        const high = Number(row.high) || open;
        const low = Number(row.low) || open;
        const close = Number(row.close) || open;
        candleData.push({ time, open, high: Math.max(high, open, close), low: Math.min(low, open, close), close });
        const isUp = close >= open;
        volumeData.push({ time, value: Number(row.volume) || 0, color: isUp ? 'rgba(0,245,160,0.5)' : 'rgba(245,0,79,0.5)' });
      }

      const seenTimes = new Set();
      const uniqueCandles = [];
      const uniqueVolumes = [];
      for (let i = 0; i < candleData.length; i++) {
        if (!seenTimes.has(candleData[i].time)) {
          seenTimes.add(candleData[i].time);
          uniqueCandles.push(candleData[i]);
          uniqueVolumes.push(volumeData[i]);
        }
      }

      this.tvSeries.setData(uniqueCandles);
      this.tvVolume.setData(uniqueVolumes);
    } catch (e) {
      console.error("[CHART ERROR]", e);
      if (container) {
        let errDiv = document.getElementById('chart-error-msg');
        if (!errDiv) {
          errDiv = document.createElement('div');
          errDiv.id = 'chart-error-msg';
          errDiv.style.cssText = 'color:#f5004f; padding:20px; position:absolute; z-index:999;';
          container.appendChild(errDiv);
        }
        errDiv.innerHTML = `<strong>Chart Error:</strong><br/>${e.message}`;
      }
    }
    if (this.tvChart) this.tvChart.timeScale().fitContent();
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
    if (!this.currentData || !this.currentData.results || !this.currentData.results.length) return;

    const cols = ['ticker', 'name', 'sector', 'industry', 'country', 'exchange', 'pct_change', 'vs_sector', 'vs_country', 'end_price', 'market_cap', 'market_cap_tier', 'pe_ratio', 'rsi_14', 'volume_ratio', 'gain_streak', 'at_52w_high', 'at_52w_low', 'pct_from_52w_high', 'volatility_30d', 'max_drawdown', 'currency'];
    let csv = cols.join(',') + '\n';

    this.currentData.results.forEach(r => {
      const row = cols.map(c => {
        const val = r[c];
        if (val === null || val === undefined) return '';
        return `"${val}"`;
      });
      csv += row.join(',') + '\n';
    });

    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `topgainers_${this.filters.period}_${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
  }

  async loadFxRates() {
    const CACHE_KEY = 'tg_fx_v1';
    const CACHE_TTL = 24 * 60 * 60 * 1000;
    try {
      const cached = JSON.parse(localStorage.getItem(CACHE_KEY) || 'null');
      if (cached && (Date.now() - cached.ts) < CACHE_TTL) {
        this.fxRates = cached.rates;
        return;
      }
      const res = await fetch('https://open.er-api.com/v6/latest/USD');
      const json = await res.json();
      if (json.rates) {
        this.fxRates = json.rates;
        localStorage.setItem(CACHE_KEY, JSON.stringify({ ts: Date.now(), rates: json.rates }));
        // Re-render table so market caps show converted values
        if (this.currentData && window.Table) Table.render(this.currentData);
      }
    } catch (e) {
      console.warn('FX rates fetch failed, showing local currency for market cap', e);
    }
  }

  toUSD(amount, currency) {
    if (!amount) return null;
    if (!currency || currency === 'USD') return amount;
    const rate = this.fxRates[currency];
    if (!rate) return amount; // unknown currency — show as-is
    return amount / rate;
  }

  formatMarketCap(n, currency) {
    const usd = this.toUSD(n, currency);
    if (!usd) return '—';
    const prefix = '$';
    if (usd >= 1e12) return prefix + (usd / 1e12).toFixed(2) + 'T';
    if (usd >= 1e9)  return prefix + (usd / 1e9).toFixed(2) + 'B';
    if (usd >= 1e6)  return prefix + (usd / 1e6).toFixed(2) + 'M';
    if (usd >= 1e3)  return prefix + (usd / 1e3).toFixed(2) + 'K';
    return prefix + usd.toFixed(2);
  }

  formatNumber(n, prefix = '') {
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
    if (diff < 3600) return Math.floor(diff / 60) + 'm ago';
    // For anything older than 1h, show the actual date/time so it's not vague
    const today = now.toDateString() === d.toDateString();
    if (today) return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    return d.toLocaleDateString([], { month: 'short', day: 'numeric' }) + ' ' + d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }

  startLiveRefresh() {
    this._stalenessInterval = setInterval(() => {
      const el = document.getElementById('last-updated-time');
      if (el && this._lastUpdatedAt) {
        el.textContent = 'Data: ' + this.timeAgo(this._lastUpdatedAt);
      }
    }, 60000);

    this._liveQuoteInterval = setInterval(() => {
      if (!this.currentData || !this.currentData.results) return;
      const tickers = this.currentData.results.map(r => r.ticker);
      const currencyMap = {};
      this.currentData.results.forEach(r => currencyMap[r.ticker] = r.currency);
      if (window.Table) Table.hydrateLiveQuotes(tickers, currencyMap, this.filters.period);
    }, 5000);

    this._fullRefreshInterval = setInterval(() => {
      if (this.filters.period === '1D') this.fetchData();
    }, 300000);

    this._marqueeInterval = setInterval(() => {
      this.renderMarquee();
    }, 5000);
  }

  async fetchStatsData() {
    try {
      const data = await window.SupabaseAPI.getStats();
      const el = document.getElementById('last-updated-time');
      if (el && data.last_updated) {
        this._lastUpdatedAt = data.last_updated;
        el.textContent = 'Data: ' + this.timeAgo(data.last_updated);
      }
    } catch (e) {
      console.error(e);
    }
  }
}

document.addEventListener('DOMContentLoaded', () => {
  window.app = new App();

  const mobileFilterBtn = document.getElementById('mobile-filter-btn');
  const closeSidebarBtn = document.getElementById('close-sidebar');
  const sidebar = document.getElementById('sidebar');
  const sidebarOverlay = document.getElementById('sidebar-overlay');

  if (mobileFilterBtn && sidebar && sidebarOverlay) {
    mobileFilterBtn.addEventListener('click', () => {
      sidebar.classList.add('open');
      sidebarOverlay.classList.remove('hidden');
    });

    const closeSidebar = () => {
      sidebar.classList.remove('open');
      sidebarOverlay.classList.add('hidden');
    };

    if (closeSidebarBtn) closeSidebarBtn.addEventListener('click', closeSidebar);
    sidebarOverlay.addEventListener('click', closeSidebar);
  }
});
