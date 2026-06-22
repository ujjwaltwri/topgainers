class Table {
  static init(app) {
    this.app = app;
    this.tbody = document.getElementById('table-body');
    this.pagination = document.getElementById('pagination');
    this.activeRowIndex = -1;
  }

  static render(data) {
    if (!this.tbody) return;
    this.tbody.innerHTML = '';
    this.activeRowIndex = -1;
    
    if (!data.results || data.results.length === 0) {
      this.tbody.innerHTML = `
        <tr>
          <td colspan="10">
            <div class="empty-state">
              <div class="empty-icon"><svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg></div>
              <div class="empty-text">No stocks match your filters</div>
              <div class="empty-sub">Try adjusting your criteria or reset filters</div>
            </div>
          </td>
        </tr>`;
      this.renderPagination(1, 1);
      return;
    }
    
    const isGain = this.app.filters.direction === 'gainers';
    const offset = (data.page - 1) * this.app.filters.limit;
    
    data.results.forEach((r, i) => {
      const tr = document.createElement('tr');
      tr.style.animation = `rowFadeIn 0.35s ease forwards ${i * 0.025}s`;
      tr.style.opacity = '0';
      tr.dataset.index = i;
      
      const pctAbs = Math.abs(r.pct_change || 0);
      const pctColor = r.pct_change > 0 ? 'badge-gain' : (r.pct_change < 0 ? 'badge-loss' : 'text-neutral');
      let intensity = '';
      if (pctAbs > 20) intensity = ' intensity-extreme';
      else if (pctAbs > 8) intensity = ' intensity-high';
      
      const vsColor = r.vs_sector > 0 ? 'text-gain' : (r.vs_sector < 0 ? 'text-loss' : 'text-neutral');
      
      let signals = '';
      if (r.at_52w_high) signals += '<span class="badge" title="At 52W High">52W HI</span> ';
      if (r.at_52w_low) signals += '<span class="badge" title="At 52W Low">52W LO</span> ';
      if (r.volume_ratio >= 3.0) signals += '<span class="badge" title="Volume Surge">SURGE</span> ';
      if (r.gain_streak >= 10) signals += '<span class="badge" title="Gain Streak">STREAK</span> ';
      
      const watchlistIcon = localStorage.getItem('wl_' + r.ticker) ? '<svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon></svg>' : '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon></svg>';
      const wlClass = localStorage.getItem('wl_' + r.ticker) ? 'active' : '';

      tr.innerHTML = `
        <td class="text-tertiary">${offset + i + 1}</td>
        <td>
          <div class="stock-cell-title font-bold">${r.name || r.ticker}</div>
          <div class="stock-cell-ticker">${r.ticker} ${signals}</div>
        </td>
        <td class="text-secondary">${r.sector || '-'}</td>
        <td><span class="text-small text-secondary">${r.country || '-'}</span></td>
        <td class="text-right"><span class="${pctColor}${intensity} font-mono">${this.app.formatPercent(r.pct_change)}</span></td>
        <td class="text-right"><span class="${vsColor} font-mono">${this.app.formatPercent(r.vs_sector)}</span></td>
        <td class="text-right font-mono">${this.formatWithCommas(r.end_price, r.currency)}</td>
        <td class="text-right font-mono">${this.app.formatNumber(r.market_cap, '$')}</td>
        <td class="text-center"><canvas width="120" height="30" class="sparkline trend-canvas" data-ticker="${r.ticker}" data-pct="${r.pct_change || 0}"></canvas></td>
        <td class="text-center watchlist-star ${wlClass}" data-ticker="${r.ticker}">${watchlistIcon}</td>
      `;
      
      tr.addEventListener('click', (e) => {
        if (!e.target.classList.contains('watchlist-star')) {
          this.app.showStockDetail(r.ticker);
        }
      });
      
      this.tbody.appendChild(tr);
    });
    
    // Setup Watchlist clicks
    this.tbody.querySelectorAll('.watchlist-star').forEach(star => {
      star.addEventListener('click', (e) => {
        e.stopPropagation();
        const t = e.currentTarget.dataset.ticker;
        if (localStorage.getItem('wl_' + t)) {
          localStorage.removeItem('wl_' + t);
          e.currentTarget.innerHTML = '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon></svg>';
          e.currentTarget.classList.remove('active');
        } else {
          localStorage.setItem('wl_' + t, '1');
          e.currentTarget.innerHTML = '<svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon></svg>';
          e.currentTarget.classList.add('active');
        }
      });
    });

    this.renderPagination(data.pages, data.page);
    this.drawSparklines();
  }

  static formatWithCommas(num, currency) {
    if (num === null || num === undefined) return '-';
    const currStr = currency ? currency + ' ' : '';
    try {
      return currStr + Number(num).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    } catch {
      return currStr + Number(num).toFixed(2);
    }
  }

  static renderPagination(pages, currentPage) {
    if (!this.pagination) return;
    this.pagination.innerHTML = '';
    
    if (pages <= 1) return;
    
    const prev = document.createElement('button');
    prev.className = 'page-btn';
    prev.innerHTML = '◀ Prev';
    prev.disabled = currentPage <= 1;
    prev.addEventListener('click', () => this.app.changePage(currentPage - 1));
    this.pagination.appendChild(prev);
    
    const info = document.createElement('span');
    info.className = 'text-secondary font-mono';
    info.style.alignSelf = 'center';
    info.style.fontSize = '0.85rem';
    info.textContent = `${currentPage} / ${pages}`;
    this.pagination.appendChild(info);
    
    const next = document.createElement('button');
    next.className = 'page-btn';
    next.innerHTML = 'Next ▶';
    next.disabled = currentPage >= pages;
    next.addEventListener('click', () => this.app.changePage(currentPage + 1));
    this.pagination.appendChild(next);
  }

  static showSkeleton() {
    if (!this.tbody) return;
    this.tbody.innerHTML = '';
    for (let i = 0; i < 12; i++) {
      const tr = document.createElement('tr');
      tr.style.animation = `fadeIn 0.3s ease forwards ${i * 0.03}s`;
      tr.style.opacity = '0';
      tr.innerHTML = `
        <td><div class="skeleton" style="width:20px;height:14px"></div></td>
        <td>
          <div class="skeleton" style="width:${100 + Math.random() * 40}px;height:14px;margin-bottom:6px"></div>
          <div class="skeleton" style="width:${50 + Math.random() * 30}px;height:11px"></div>
        </td>
        <td><div class="skeleton" style="width:${70 + Math.random() * 30}px;height:14px"></div></td>
        <td><div class="skeleton" style="width:${80 + Math.random() * 30}px;height:14px"></div></td>
        <td class="text-right"><div class="skeleton" style="width:60px;height:22px;display:inline-block;border-radius:4px"></div></td>
        <td class="text-right"><div class="skeleton" style="width:50px;height:14px;display:inline-block"></div></td>
        <td class="text-right"><div class="skeleton" style="width:65px;height:14px;display:inline-block"></div></td>
        <td class="text-right"><div class="skeleton" style="width:55px;height:14px;display:inline-block"></div></td>
        <td class="text-center"><div class="skeleton" style="width:120px;height:36px;display:inline-block;border-radius:4px"></div></td>
        <td></td>
      `;
      this.tbody.appendChild(tr);
    }
  }

  static getCountryFlag(country) {
    return ''; // Flags removed in favor of Cortexa text-only layout
  }
  
  // --- Premium Sparklines with gradient fill and random-walk data ---
  static drawSparklines() {
    document.querySelectorAll('canvas.sparkline').forEach(canvas => {
      const ctx = canvas.getContext('2d');
      const w = canvas.width;
      const h = canvas.height;
      const pct = parseFloat(canvas.dataset.pct) || 0;
      const isGain = pct >= 0;
      
      ctx.clearRect(0, 0, w, h);
      
      // Generate realistic random-walk data
      const pts = 30;
      const points = [];
      let value = isGain ? h * 0.7 : h * 0.3;
      const trend = isGain ? -0.15 : 0.15; // negative Y = upward on canvas
      const volatility = h * 0.08;
      
      for (let i = 0; i <= pts; i++) {
        const noise = (Math.random() - 0.5) * volatility * 2;
        // Mean-reverting random walk with trend
        const drift = trend * (1 + Math.abs(pct) * 0.02);
        value += noise + drift;
        value = Math.max(4, Math.min(h - 4, value));
        points.push({ x: (w / pts) * i, y: value });
      }
      
      // Smooth the curve using cardinal spline
      const smoothed = this.cardinalSpline(points, 0.4, 6);
      
      // Draw gradient fill
      ctx.beginPath();
      ctx.moveTo(smoothed[0].x, smoothed[0].y);
      for (let i = 1; i < smoothed.length; i++) {
        ctx.lineTo(smoothed[i].x, smoothed[i].y);
      }
      // Close the fill
      ctx.lineTo(w, h);
      ctx.lineTo(0, h);
      ctx.closePath();
      
      const fillGrad = ctx.createLinearGradient(0, 0, 0, h);
      if (isGain) {
        fillGrad.addColorStop(0, 'rgba(0, 245, 160, 0.25)');
        fillGrad.addColorStop(1, 'rgba(0, 245, 160, 0.02)');
      } else {
        fillGrad.addColorStop(0, 'rgba(245, 0, 79, 0.25)');
        fillGrad.addColorStop(1, 'rgba(245, 0, 79, 0.02)');
      }
      ctx.fillStyle = fillGrad;
      ctx.fill();
      
      // Draw line
      ctx.beginPath();
      ctx.moveTo(smoothed[0].x, smoothed[0].y);
      for (let i = 1; i < smoothed.length; i++) {
        ctx.lineTo(smoothed[i].x, smoothed[i].y);
      }
      
      const lineGrad = ctx.createLinearGradient(0, 0, w, 0);
      if (isGain) {
        lineGrad.addColorStop(0, 'rgba(0, 245, 160, 0.5)');
        lineGrad.addColorStop(1, '#00f5a0');
      } else {
        lineGrad.addColorStop(0, 'rgba(245, 0, 79, 0.5)');
        lineGrad.addColorStop(1, '#f5004f');
      }
      ctx.strokeStyle = lineGrad;
      ctx.lineWidth = 1.5;
      ctx.lineJoin = 'round';
      ctx.stroke();
      
      // Draw end dot
      const last = smoothed[smoothed.length - 1];
      ctx.beginPath();
      ctx.arc(last.x, last.y, 2, 0, Math.PI * 2);
      ctx.fillStyle = isGain ? '#00f5a0' : '#f5004f';
      ctx.fill();
    });
  }
  
  // Cardinal spline interpolation for smooth curves
  static cardinalSpline(points, tension, segments) {
    const result = [];
    const t = tension || 0.5;
    const segs = segments || 6;
    
    for (let i = 0; i < points.length - 1; i++) {
      const p0 = points[Math.max(0, i - 1)];
      const p1 = points[i];
      const p2 = points[Math.min(points.length - 1, i + 1)];
      const p3 = points[Math.min(points.length - 1, i + 2)];
      
      for (let s = 0; s < segs; s++) {
        const st = s / segs;
        const st2 = st * st;
        const st3 = st2 * st;
        
        const x = 0.5 * (
          (2 * p1.x) +
          (-p0.x + p2.x) * st +
          (2 * p0.x - 5 * p1.x + 4 * p2.x - p3.x) * st2 +
          (-p0.x + 3 * p1.x - 3 * p2.x + p3.x) * st3
        );
        const y = 0.5 * (
          (2 * p1.y) +
          (-p0.y + p2.y) * st +
          (2 * p0.y - 5 * p1.y + 4 * p2.y - p3.y) * st2 +
          (-p0.y + 3 * p1.y - 3 * p2.y + p3.y) * st3
        );
        
        result.push({ x, y });
      }
    }
    // Add the last point
    result.push(points[points.length - 1]);
    return result;
  }

  // Keyboard navigation support
  static highlightRow(index) {
    const rows = this.tbody.querySelectorAll('tr');
    rows.forEach(r => r.classList.remove('keyboard-active'));
    if (index >= 0 && index < rows.length) {
      this.activeRowIndex = index;
      rows[index].classList.add('keyboard-active');
      rows[index].scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    }
  }

  static getActiveRowTicker() {
    const rows = this.tbody.querySelectorAll('tr');
    if (this.activeRowIndex >= 0 && this.activeRowIndex < rows.length) {
      const star = rows[this.activeRowIndex].querySelector('.watchlist-star');
      return star ? star.dataset.ticker : null;
    }
    return null;
  }

  static getRowCount() {
    return this.tbody ? this.tbody.querySelectorAll('tr').length : 0;
  }
}
window.Table = Table;
