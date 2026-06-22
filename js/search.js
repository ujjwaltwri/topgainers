class Search {
  static init(app) {
    this.app = app;
    this.input = document.getElementById('stock-search');
    this.resultsContainer = document.getElementById('search-results');
    
    if (!this.input || !this.resultsContainer) return;
    
    this.input.addEventListener('input', this.debounce((e) => this.search(e.target.value), 300));
    
    this.input.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') this.hideResults();
    });
    
    document.addEventListener('click', (e) => {
      if (!this.input.contains(e.target) && !this.resultsContainer.contains(e.target)) {
        this.hideResults();
      }
    });
  }

  static async search(query) {
    if (query.length < 2) {
      this.hideResults();
      return;
    }
    
    try {
      const data = await window.SupabaseAPI.searchStocks(query);
      if (data && data.results) {
        this.renderResults(data.results);
      }
    } catch (e) {
      console.error('Search error', e);
    }
  }

  static renderResults(results) {
    if (!results || results.length === 0) {
      this.resultsContainer.innerHTML = '<div class="search-result-item text-secondary">No results found</div>';
    } else {
      this.resultsContainer.innerHTML = '';
      results.forEach(r => {
        const div = document.createElement('div');
        div.className = 'search-result-item';
        div.innerHTML = `
          <div>
            <strong>${r.ticker}</strong> - ${r.name}
            <div class="text-small text-tertiary">${r.sector || ''}</div>
          </div>
          <div class="text-right">
            ${Table.getCountryFlag(r.country)}
          </div>
        `;
        div.addEventListener('click', () => {
          this.app.showStockDetail(r.ticker);
          this.hideResults();
          this.input.value = '';
        });
        this.resultsContainer.appendChild(div);
      });
    }
    this.resultsContainer.classList.remove('hidden');
  }

  static hideResults() {
    if (this.resultsContainer) {
      this.resultsContainer.classList.add('hidden');
    }
  }

  static debounce(fn, delay) {
    let timeoutId;
    return function (...args) {
      clearTimeout(timeoutId);
      timeoutId = setTimeout(() => fn.apply(this, args), delay);
    };
  }
}
window.Search = Search;
