class Filters {
  static init(app) {
    this.app = app;
    this.setupRegionCountryExchange();
    this.setupSectorIndustry();
    this.setupMcapChips();
    this.setupDirectionToggle();
    this.setupQuickFilters();
    this.setupVolumeFilter();
    this.setupPriceRange();
    this.setupPERatioRange();
    
    document.getElementById('reset-filters')?.addEventListener('click', () => this.resetAll());
    document.getElementById('sort-by')?.addEventListener('change', (e) => this.app.updateFilters({sort: e.target.value}));
  }

  static populateAll(data) {
    this.filtersData = data;
    
    this.populateDropdown('filter-region', Object.keys(data.regions || {}), '-- All Regions --');
    this.populateDropdown('filter-sector', data.sectors || [], '-- All Sectors --');
    this.populateDropdown('filter-country', data.countries || [], '-- All Countries --');
    this.populateDropdown('filter-exchange', data.exchanges || [], '-- All Exchanges --');
    this.populateDropdown('filter-industry', data.industries || [], '-- All Industries --');
    
    this.renderPeriodButtons(data.periods || ['1D', '5D', '1M', '3M', '6M', '1Y', 'YTD', 'MAX']);
    
    this.syncUI(this.app.filters);
  }

  static populateDropdown(elementId, options, defaultLabel) {
    const el = document.getElementById(elementId);
    if (!el) return;
    el.innerHTML = `<option value="">${defaultLabel}</option>`;
    options.forEach(opt => {
      const option = document.createElement('option');
      option.value = opt;
      option.textContent = opt;
      el.appendChild(option);
    });
  }

  static setupRegionCountryExchange() {
    const reg = document.getElementById('filter-region');
    const cty = document.getElementById('filter-country');
    const exc = document.getElementById('filter-exchange');
    
    if (reg) reg.addEventListener('change', (e) => {
      const val = e.target.value;
      if (val && this.filtersData && this.filtersData.regions) {
        this.populateDropdown('filter-country', this.filtersData.regions[val], '-- All Countries --');
        cty.disabled = false;
      } else {
        this.populateDropdown('filter-country', this.filtersData?.countries || [], '-- All Countries --');
        cty.disabled = false;
      }
      this.app.updateFilters({region: val, country: '', exchange: ''});
    });

    if (cty) cty.addEventListener('change', (e) => {
      exc.disabled = false;
      this.app.updateFilters({country: e.target.value, exchange: ''});
    });

    if (exc) exc.addEventListener('change', (e) => {
      this.app.updateFilters({exchange: e.target.value});
    });
  }

  static setupSectorIndustry() {
    const sec = document.getElementById('filter-sector');
    const ind = document.getElementById('filter-industry');
    
    if (sec) sec.addEventListener('change', (e) => {
      ind.disabled = !e.target.value;
      this.app.updateFilters({sector: e.target.value, industry: ''});
    });
    
    if (ind) ind.addEventListener('change', (e) => {
      this.app.updateFilters({industry: e.target.value});
    });
  }

  static renderPeriodButtons(periods) {
    const container = document.getElementById('period-buttons');
    if (!container) return;
    container.innerHTML = '';
    
    periods.forEach(p => {
      if (p === 'CUSTOM') return;
      const btn = document.createElement('button');
      btn.textContent = p;
      btn.dataset.val = p;
      if (p === this.app.filters.period) btn.classList.add('active');
      
      btn.addEventListener('click', () => {
        container.querySelectorAll('button').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        this.app.updateFilters({period: p});
      });
      container.appendChild(btn);
    });
  }

  static setupMcapChips() {
    const container = document.getElementById('mcap-chips');
    if (!container) return;
    
    container.addEventListener('click', (e) => {
      if (e.target.classList.contains('chip')) {
        const val = e.target.dataset.val;
        
        if (val === '') {
          container.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
          e.target.classList.add('active');
          this.app.updateFilters({mcap: ''});
        } else {
          container.querySelector('.chip[data-val=""]').classList.remove('active');
          e.target.classList.toggle('active');
          
          const activeVals = Array.from(container.querySelectorAll('.chip.active')).map(c => c.dataset.val).filter(v => v);
          if (activeVals.length === 0) {
            container.querySelector('.chip[data-val=""]').classList.add('active');
            this.app.updateFilters({mcap: ''});
          } else {
            this.app.updateFilters({mcap: activeVals.join(',')});
          }
        }
      }
    });
  }

  static setupDirectionToggle() {
    const container = document.getElementById('direction-toggle');
    if (!container) return;
    
    container.addEventListener('click', (e) => {
      if (e.target.tagName === 'BUTTON') {
        container.querySelectorAll('button').forEach(b => b.classList.remove('active'));
        e.target.classList.add('active');
        
        // Animate the sliding indicator
        if (e.target.dataset.dir === 'losers') {
          container.classList.add('losers-active');
        } else {
          container.classList.remove('losers-active');
        }
        
        this.app.updateFilters({direction: e.target.dataset.dir});
      }
    });
  }

  static setupQuickFilters() {
    ['52w-high', '52w-low', 'vol-surge'].forEach(id => {
      const el = document.getElementById(`filter-${id}`);
      if (el) {
        el.addEventListener('change', (e) => {
          let key = id;
          if (id === '52w-high') key = 'at_52w_high';
          if (id === '52w-low') key = 'at_52w_low';
          if (id === 'vol-surge') key = 'volume_surge';
          
          this.app.updateFilters({[key]: e.target.checked ? 'true' : ''});
        });
      }
    });
  }

  static setupVolumeFilter() {
    const el = document.getElementById('filter-volume');
    if (el) {
      el.addEventListener('change', (e) => {
        this.app.updateFilters({min_volume: e.target.value});
      });
    }
  }

  static setupPriceRange() {
    const minEl = document.getElementById('filter-price-min');
    const maxEl = document.getElementById('filter-price-max');
    
    const handler = this.debounce(() => {
      const updates = {};
      updates.min_price = minEl ? minEl.value : '';
      updates.max_price = maxEl ? maxEl.value : '';
      this.app.updateFilters(updates);
    }, 600);
    
    if (minEl) minEl.addEventListener('input', handler);
    if (maxEl) maxEl.addEventListener('input', handler);
  }

  static setupPERatioRange() {
    const minEl = document.getElementById('filter-pe-min');
    const maxEl = document.getElementById('filter-pe-max');
    
    const handler = this.debounce(() => {
      const updates = {};
      updates.min_pe = minEl ? minEl.value : '';
      updates.max_pe = maxEl ? maxEl.value : '';
      this.app.updateFilters(updates);
    }, 600);
    
    if (minEl) minEl.addEventListener('input', handler);
    if (maxEl) maxEl.addEventListener('input', handler);
  }

  static debounce(fn, delay) {
    let timeoutId;
    return (...args) => {
      clearTimeout(timeoutId);
      timeoutId = setTimeout(() => fn(...args), delay);
    };
  }

  static syncUI(filters) {
    // Dropdowns
    ['region', 'country', 'exchange', 'sector', 'industry'].forEach(key => {
      const el = document.getElementById(`filter-${key}`);
      if (el) {
        el.value = filters[key] || '';
        if (filters[key]) el.disabled = false;
      }
    });
    
    // Volume
    const vol = document.getElementById('filter-volume');
    if (vol) vol.value = filters.min_volume || '';
    
    // Price range
    const priceMin = document.getElementById('filter-price-min');
    const priceMax = document.getElementById('filter-price-max');
    if (priceMin) priceMin.value = filters.min_price || '';
    if (priceMax) priceMax.value = filters.max_price || '';
    
    // PE range
    const peMin = document.getElementById('filter-pe-min');
    const peMax = document.getElementById('filter-pe-max');
    if (peMin) peMin.value = filters.min_pe || '';
    if (peMax) peMax.value = filters.max_pe || '';
    
    // Sort
    const sort = document.getElementById('sort-by');
    if (sort) sort.value = filters.sort || 'pct_change';

    // Direction
    const dirContainer = document.getElementById('direction-toggle');
    if (dirContainer) {
      dirContainer.querySelectorAll('button').forEach(b => {
        b.classList.toggle('active', b.dataset.dir === (filters.direction || 'gainers'));
      });
      if (filters.direction === 'losers') {
        dirContainer.classList.add('losers-active');
      } else {
        dirContainer.classList.remove('losers-active');
      }
    }

    // Period
    const perContainer = document.getElementById('period-buttons');
    if (perContainer) {
      perContainer.querySelectorAll('button').forEach(b => {
        b.classList.toggle('active', b.dataset.val === filters.period);
      });
    }
    
    // Checkboxes
    const c_high = document.getElementById('filter-52w-high');
    if (c_high) c_high.checked = !!filters.at_52w_high;
    const c_low = document.getElementById('filter-52w-low');
    if (c_low) c_low.checked = !!filters.at_52w_low;
    const c_surge = document.getElementById('filter-vol-surge');
    if (c_surge) c_surge.checked = !!filters.volume_surge;
  }

  static renderActivePills(filters) {
    const container = document.getElementById('active-filters-container');
    if (!container) return;
    container.innerHTML = '';
    
    const skip = ['direction', 'period', 'sort', 'limit', 'page'];
    
    // Human-readable labels for filter keys
    const labels = {
      region: 'Region',
      country: 'Country',
      exchange: 'Exchange',
      sector: 'Sector',
      industry: 'Industry',
      mcap: 'Market Cap',
      min_volume: 'Min Volume',
      min_price: 'Min Price',
      max_price: 'Max Price',
      min_pe: 'Min P/E',
      max_pe: 'Max P/E',
      '52w_high': '52W High',
      at_52w_high: '52W High',
      '52w_low': '52W Low',
      at_52w_low: '52W Low',
      vol_surge: 'Vol Surge',
    };
    
    for (const key in filters) {
      if (skip.includes(key)) continue;
      const val = filters[key];
      if (val !== '' && val !== null && val !== undefined && val !== false) {
        const pill = document.createElement('div');
        pill.className = 'filter-pill';
        const label = labels[key] || key.replace(/_/g, ' ');
        let displayVal = val;
        if (val === true) displayVal = '✓';
        else if (key === 'min_volume') {
          const n = Number(val);
          if (n >= 1e6) displayVal = (n / 1e6) + 'M+';
          else if (n >= 1e3) displayVal = (n / 1e3) + 'K+';
        }
        pill.innerHTML = `
          <span class="pill-label">${label}:</span>
          <span>${displayVal}</span>
          <span class="pill-close" data-key="${key}">✕</span>
        `;
        container.appendChild(pill);
      }
    }
    
    // Event delegation for pill removal
    container.onclick = (e) => {
      if (e.target.classList.contains('pill-close') && e.target.dataset.key) {
        const key = e.target.dataset.key;
        this.app.updateFilters({[key]: ''});
        
        // Also reset the UI element
        this.syncUI(this.app.filters);
      }
    };
  }

  static resetAll() {
    const defaultFilters = {
      direction: 'gainers',
      period: '6M',
      sort: 'pct_change',
      limit: 25,
      page: 1
    };
    
    // Animate the reset button
    const btn = document.getElementById('reset-filters');
    if (btn) {
      btn.style.transform = 'scale(0.9)';
      btn.style.transition = 'transform 0.15s ease';
      setTimeout(() => { btn.style.transform = ''; }, 150);
    }
    
    // Reset inputs
    document.querySelectorAll('select').forEach(s => s.value = '');
    document.querySelectorAll('input[type="checkbox"]').forEach(c => c.checked = false);
    document.querySelectorAll('input[type="number"]').forEach(n => n.value = '');
    
    // Reset Mcap
    const mcapContainer = document.getElementById('mcap-chips');
    if (mcapContainer) {
      mcapContainer.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
      mcapContainer.querySelector('.chip[data-val=""]')?.classList.add('active');
    }
    
    // Reset direction indicator
    const dirContainer = document.getElementById('direction-toggle');
    if (dirContainer) dirContainer.classList.remove('losers-active');
    
    this.app.filters = {};
    this.app.updateFilters(defaultFilters);
    this.syncUI(defaultFilters);
  }
}
window.Filters = Filters;
