// Supabase API wrapper to replace local server.py
const SUPABASE_URL = 'https://oqgwwidykukkqcgvvsnm.supabase.co';
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9xZ3d3aWR5a3Vra3FjZ3Z2c25tIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODIxMjc5NDEsImV4cCI6MjA5NzcwMzk0MX0.Yk8nSX_7NCvPqfv0_8I0kPmZCWhyoH7QRICaz2i_fjw';

const supabaseClient = supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

window.SupabaseAPI = {
  async getTopMovers(filters) {
    const period = filters.period || '6M';
    const limit = parseInt(filters.limit) || 25;
    const page = parseInt(filters.page) || 1;
    const offset = (page - 1) * limit;
    
    let query = supabaseClient.from('gains').select('*, stocks!inner(*)', { count: 'exact' });
    query = query.eq('period', period);
    
    // Apply filters
    if (filters.sector) query = query.eq('stocks.sector', filters.sector);
    if (filters.industry) query = query.eq('stocks.industry', filters.industry);
    if (filters.country) query = query.eq('stocks.country', filters.country);
    if (filters.region) query = query.eq('stocks.region', filters.region);
    if (filters.exchange) query = query.eq('stocks.exchange', filters.exchange);
    
    if (filters.mcap) {
      const tiers = filters.mcap.split(',');
      query = query.in('stocks.market_cap_tier', tiers);
    }
    
    if (filters.min_volume) query = query.gte('avg_volume', parseFloat(filters.min_volume));
    if (filters.min_price) query = query.gte('end_price', parseFloat(filters.min_price));
    if (filters.max_price) query = query.lte('end_price', parseFloat(filters.max_price));
    if (filters.min_pe) query = query.gte('stocks.pe_ratio', parseFloat(filters.min_pe));
    if (filters.max_pe) query = query.lte('stocks.pe_ratio', parseFloat(filters.max_pe));
    
    if (filters.at_52w_high === 'true') query = query.eq('at_52w_high', true);
    if (filters.at_52w_low === 'true') query = query.eq('at_52w_low', true);
    if (filters.volume_surge === 'true') query = query.gte('volume_ratio', 3.0);
    
    // Sorting
    const sortCol = filters.sort || 'pct_change';
    const direction = filters.direction || 'gainers';
    const ascending = direction === 'losers';
    
    let mappedSortCol = sortCol;
    if (sortCol === 'market_cap') {
        // Fallback for foreign key sort which might not work smoothly
        // If it fails, we ignore sort
        mappedSortCol = 'pct_change'; 
    }
    
    query = query.order(mappedSortCol, { ascending });
    query = query.range(offset, offset + limit - 1);
    
    const { data, error, count } = await query;
    if (error) {
        console.error('Supabase query error:', error);
        throw error;
    }
    
    // Flatten result
    const results = data.map(row => {
        const stockInfo = row.stocks;
        delete row.stocks;
        return { ...stockInfo, ...row };
    });
    
    if (sortCol === 'market_cap') {
        results.sort((a, b) => ascending ? a.market_cap - b.market_cap : b.market_cap - a.market_cap);
    }
    
    return {
        results,
        total: count,
        page,
        pages: Math.ceil(count / limit),
        period,
        direction
    };
  },
  
  async getFilters() {
    return {
        sectors: ["Technology", "Healthcare", "Financial Services", "Consumer Cyclical", "Industrials", "Communication Services", "Consumer Defensive", "Energy", "Basic Materials", "Real Estate", "Utilities"],
        industries: [],
        countries: ["United States", "India", "Japan", "China", "United Kingdom", "Germany", "France", "Canada", "Australia", "Brazil", "South Korea", "Hong Kong", "Saudi Arabia", "Netherlands", "Taiwan", "Switzerland"],
        exchanges: ["NYSE", "NASDAQ", "NSE", "BSE", "TSE", "SSE", "SZSE", "LSE", "XETRA", "TSX", "ASX", "B3", "KOSPI", "KOSDAQ", "HKEX", "Tadawul", "Euronext Paris", "Euronext Amsterdam"],
        regions: {"Americas": ["United States", "Canada", "Brazil"], "Europe": ["United Kingdom", "Germany", "France", "Netherlands", "Switzerland"], "Asia-Pacific": ["India", "Japan", "China", "South Korea", "Hong Kong", "Australia", "Taiwan"], "Middle East": ["Saudi Arabia"]},
        periods: ["1D", "5D", "1M", "3M", "6M", "1Y", "2Y", "3Y", "5Y", "YTD", "MAX"],
        mcap_tiers: ["Mega", "Large", "Mid", "Small", "Micro", "Nano"],
        currencies: ["USD", "INR", "JPY", "CNY", "GBP", "EUR", "CAD", "AUD", "BRL", "KRW", "HKD", "SAR"]
    };
  },
  
  async getStats() {
    const { data, error } = await supabaseClient.from('pipeline_meta').select('*');
    if (error) return {};
    
    const stats = {};
    for (const row of data) {
        stats[row.key] = row.value;
    }
    return {
        total_stocks: parseInt(stats.tickers_count) || 0,
        last_updated: stats.last_updated
    };
  },
  
  async getStockDetail(ticker) {
    const [{ data: stockData }, { data: gainsData }, { data: priceData }] = await Promise.all([
        supabaseClient.from('stocks').select('*').eq('ticker', ticker).single(),
        supabaseClient.from('gains').select('*').eq('ticker', ticker),
        supabaseClient.from('price_history').select('*').eq('ticker', ticker).order('date', { ascending: true })
    ]);
    
    const gainsObj = {};
    if (gainsData) {
        for (const g of gainsData) {
            gainsObj[g.period] = g;
        }
    }
    
    return {
        stock: stockData || {},
        gains: gainsObj,
        price_history: priceData || []
    };
  },
  
  async searchStocks(query) {
    const { data, error } = await supabase
        .from('stocks')
        .select('ticker, name, sector, country, exchange, market_cap')
        .or(`ticker.ilike.%${query}%,name.ilike.%${query}%`)
        .limit(10);
        
    return { results: data || [] };
  }
};

  window.SupabaseAPI.getMarketBreadth = async function(period) {
    const { data, count, error } = await supabaseClient.from('gains').select('pct_change', { count: 'exact' }).eq('period', period);
    if (error) return { total: 0, positive: 0, negative: 0, pct_positive: 0 };
    
    let positive = 0;
    let negative = 0;
    for (const row of data) {
      if (row.pct_change > 0) positive++;
      else if (row.pct_change < 0) negative++;
    }
    const total = positive + negative;
    return {
      total,
      positive,
      negative,
      pct_positive: total > 0 ? (positive / total) * 100 : 0
    };
  };

  window.SupabaseAPI.getTreemap = async function(period) {
    const { data, error } = await supabase
      .from('gains')
      .select('pct_change, stocks!inner(ticker, name, sector, market_cap)')
      .eq('period', period)
      .order('stocks(market_cap)', { ascending: false })
      .limit(100);
      
    if (error) return { stocks: [] };
    
    const stocks = data.map(row => ({
      ticker: row.stocks.ticker,
      name: row.stocks.name,
      sector: row.stocks.sector,
      market_cap: row.stocks.market_cap,
      pct_change: row.pct_change
    }));
    
    return { stocks };
  };
