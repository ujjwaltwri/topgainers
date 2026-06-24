// Supabase API wrapper to replace local server.py
const SUPABASE_URL = 'https://xpmfwpqkykiqmswumoxu.supabase.co';
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InhwbWZ3cHFreWtpcW1zd3Vtb3h1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODIxNTEwNjYsImV4cCI6MjA5NzcyNzA2Nn0.TAFycwI-cScW88ynt9SZNkLUqskOxdO3e7PQh-zUZyk';

const supabaseClient = supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
window.supabaseClient = supabaseClient;

window.SupabaseAPI = {
  async getTopMovers(filters) {
    const period = filters.period || '6M';
    const limit = parseInt(filters.limit) || 25;
    const page = parseInt(filters.page) || 1;
    const offset = (page - 1) * limit;
    
    let query = supabaseClient.from('gains_with_stocks').select('*', { count: 'planned' });
    query = query.eq('period', period);
    
    // Apply filters
    if (filters.sector) query = query.eq('sector', filters.sector);
    if (filters.industry) query = query.eq('industry', filters.industry);
    if (filters.country) query = query.eq('country', filters.country);
    
    if (filters.region) {
      // server.py maps region to a list of countries
      const regionsMap = {
        "Americas": ["United States", "Canada", "Brazil", "Mexico", "Argentina", "Chile"],
        "Europe": ["United Kingdom", "Germany", "France", "Netherlands", "Switzerland", "Italy", "Spain", "Sweden", "Norway", "Denmark", "Finland", "Poland", "Austria", "Ireland", "Portugal", "Greece"],
        "Asia-Pacific": ["India", "Japan", "South Korea", "China", "Hong Kong", "Australia", "Taiwan", "Singapore", "Malaysia", "Indonesia", "Thailand", "Philippines", "New Zealand"],
        "Middle East / Africa": ["Saudi Arabia", "Israel", "Turkey", "Egypt", "Qatar", "United Arab Emirates", "South Africa"]
      };
      const countriesInRegion = regionsMap[filters.region];
      if (countriesInRegion && countriesInRegion.length > 0) {
        query = query.in('country', countriesInRegion);
      } else {
        query = query.eq('region', filters.region);
      }
    }
    
    if (filters.exchange) query = query.eq('exchange', filters.exchange);
    
    if (filters.mcap) {
      // Frontend sends "Mega,Large" but DB has "mega,large"
      const tiers = filters.mcap.split(',').map(t => t.toLowerCase());
      query = query.in('market_cap_tier', tiers);
    }
    
    if (filters.min_volume) query = query.gte('avg_volume', parseFloat(filters.min_volume));
    if (filters.min_price) query = query.gte('end_price', parseFloat(filters.min_price));
    if (filters.max_price) query = query.lte('end_price', parseFloat(filters.max_price));
    if (filters.min_pe) query = query.gte('pe_ratio', parseFloat(filters.min_pe));
    if (filters.max_pe) query = query.lte('pe_ratio', parseFloat(filters.max_pe));
    
    if (filters.at_52w_high === 'true') query = query.eq('at_52w_high', true);
    if (filters.at_52w_low === 'true') query = query.eq('at_52w_low', true);
    if (filters.volume_surge === 'true') query = query.gte('volume_ratio', 3.0);
    
    // Sorting
    const sortCol = filters.sort || 'pct_change';
    const direction = filters.direction || 'gainers';
    const ascending = direction === 'losers';
    
    query = query.not(sortCol, 'is', null).order(sortCol, { ascending, nullsFirst: false });
    query = query.range(offset, offset + limit - 1);
    
    const { data, error, count } = await query;
    if (error) {
        console.error('Supabase query error:', error);
        throw error;
    }
    
    return {
        results: data,
        total: count,
        page,
        pages: Math.ceil(count / limit),
        period,
        direction
    };
  },
  
  async getFilters() {
    const CACHE_KEY = 'tg_filters_v1';
    const CACHE_TTL = 60 * 60 * 1000; // 1 hour
    try {
      const cached = JSON.parse(localStorage.getItem(CACHE_KEY) || 'null');
      if (cached && (Date.now() - cached.ts) < CACHE_TTL) return cached.data;
    } catch {}

    const [{data: countries}, {data: sectors}, {data: industries}, {data: exchanges}] = await Promise.all([
        supabaseClient.rpc('get_distinct_countries'),
        supabaseClient.rpc('get_distinct_sectors'),
        supabaseClient.rpc('get_distinct_industries'),
        supabaseClient.rpc('get_distinct_exchanges')
    ]);

    const result = {
        sectors: sectors ? sectors.map(r => r.sector) : [],
        industries: industries ? industries.map(r => r.industry) : [],
        countries: countries ? countries.map(r => r.country) : [],
        exchanges: exchanges ? exchanges.map(r => r.exchange) : [],
        regions: {
          "Americas": ["United States", "Canada", "Brazil", "Mexico", "Argentina", "Chile"],
          "Europe": ["United Kingdom", "Germany", "France", "Netherlands", "Switzerland", "Italy", "Spain", "Sweden", "Norway", "Denmark", "Finland", "Poland", "Austria", "Ireland", "Portugal", "Greece"],
          "Asia-Pacific": ["India", "Japan", "South Korea", "China", "Hong Kong", "Australia", "Taiwan", "Singapore", "Malaysia", "Indonesia", "Thailand", "Philippines", "New Zealand"],
          "Middle East / Africa": ["Saudi Arabia", "Israel", "Turkey", "Egypt", "Qatar", "United Arab Emirates", "South Africa"]
        },
        periods: ["1D", "5D", "1M", "3M", "6M", "1Y", "2Y", "3Y", "5Y", "YTD", "MAX"],
        mcap_tiers: ["Mega", "Large", "Mid", "Small", "Micro", "Nano"],
        currencies: ["USD", "INR", "JPY", "CNY", "GBP", "EUR", "CAD", "AUD", "BRL", "KRW", "HKD", "SAR"]
    };
    try { localStorage.setItem(CACHE_KEY, JSON.stringify({ ts: Date.now(), data: result })); } catch {}
    return result;
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
    let allPrices = [];
    try {
      const { data, error } = await supabaseClient.functions.invoke('yfinance-proxy', {
        body: { ticker }
      });
      if (data && Array.isArray(data)) {
        allPrices = data;
      } else {
        console.error("Error from Edge Function:", data?.error || error);
      }
    } catch (err) {
      console.error("Failed to invoke Edge Function:", err);
    }

    const [{ data: stockData }, { data: gainsData }] = await Promise.all([
        supabaseClient.from('stocks').select('*').eq('ticker', ticker).single(),
        supabaseClient.from('gains').select('*').eq('ticker', ticker)
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
        price_history: allPrices || []
    };
  },
  
  async getMarqueeData(period) {
    const INDEX_LIST = [
      { name: 'S&P 500',    ticker: '^GSPC' },
      { name: 'NASDAQ',     ticker: '^IXIC' },
      { name: 'Nifty 50',   ticker: '^NSEI' },
      { name: 'SENSEX',     ticker: '^BSESN' },
      { name: 'KOSPI',      ticker: '^KS11' },
      { name: 'KOSDAQ',     ticker: '^KQ11' },
      { name: 'Nikkei 225', ticker: '^N225' },
      { name: 'Hang Seng',  ticker: '^HSI' },
      { name: 'FTSE 100',   ticker: '^FTSE' },
      { name: 'DAX',        ticker: '^GDAXI' },
      { name: 'CAC 40',     ticker: '^FCHI' },
      { name: 'ASX 200',    ticker: '^AXJO' },
      { name: 'TSX',        ticker: '^GSPTSE' },
      { name: 'BOVESPA',    ticker: '^BVSP' },
      { name: 'AEX',        ticker: '^AEX' },
      { name: 'SMI',        ticker: '^SSMI' },
      { name: 'IBEX 35',    ticker: '^IBEX' },
      { name: 'OMXS30',     ticker: '^OMX' },
      { name: 'TWSE',       ticker: '^TWII' },
      { name: 'STI',        ticker: '^STI' },
    ];
    try {
      const tickers = INDEX_LIST.map(i => i.ticker);
      const { data, error } = await supabaseClient.functions.invoke('live-quotes', {
        body: { tickers }
      });
      if (error || !data?.data) return [];
      return INDEX_LIST
        .map(idx => {
          const q = data.data[idx.ticker];
          if (!q) return null;
          return { name: idx.name, pct_change: q.pct_change };
        })
        .filter(Boolean);
    } catch (e) {
      console.error('Marquee error:', e);
      return [];
    }
  },
  
  async searchStocks(query, limit = 10) {
    const { data, error } = await supabaseClient
      .from('stocks')
      .select('ticker, name, sector, country, exchange, market_cap')
      .or(`ticker.ilike.%${query}%,name.ilike.%${query}%`)
      .limit(limit);
      
    if (error) {
      console.error(error);
      return { results: [] };
    }
    return { results: data };
  },

  // Realtime Subscription
  subscribeToUpdates(callback) {
    supabaseClient
      .channel('schema-db-changes')
      .on(
        'postgres_changes',
        { event: 'INSERT', schema: 'public', table: 'gains' },
        async (payload) => {
          const newGain = payload.new;
          // Fetch the stock data to complete the object
          const { data, error } = await supabaseClient
            .from('stocks')
            .select('*')
            .eq('ticker', newGain.ticker)
            .single();
            
          if (data && !error) {
            const fullRecord = { ...data, ...newGain };
            callback(fullRecord);
          }
        }
      )
      .subscribe();
  }
};

window.SupabaseAPI.getMarketBreadth = async function(period) {
    const { data, error } = await supabaseClient.rpc('get_market_breadth', { period_param: period });
    if (error || !data) return { total: 0, positive: 0, negative: 0, pct_positive: 0 };
    return data;
};

window.SupabaseAPI.getTreemap = async function(period) {
    const { data, error } = await supabaseClient
      .from('gains_with_stocks')
      .select('ticker, name, sector, market_cap, pct_change, volume_ratio')
      .eq('period', period)
      .not('market_cap', 'is', null)
      .gt('market_cap', 0)
      .order('market_cap', { ascending: false, nullsFirst: false })
      .limit(100);
      
    if (error) return { stocks: [] };
    
    return { stocks: data || [] };
};

window.SupabaseAPI.getSectorPerformance = async function(period) {
    const { data, error } = await supabaseClient.rpc('get_sector_performance', { period_param: period });
    if (error) { console.error('getSectorPerformance error:', error); return { sectors: [] }; }
    return { sectors: data || [] };
};

window.SupabaseAPI.getCountryPerformance = async function(period) {
    const { data, error } = await supabaseClient.rpc('get_country_performance', { period_param: period });
    if (error) { console.error('getCountryPerformance error:', error); return { countries: [] }; }
    return { countries: data || [] };
};

window.SupabaseAPI.getExchangePerformance = async function(period) {
    const { data, error } = await supabaseClient.rpc('get_exchange_performance', { period_param: period });
    if (error) { console.error('getExchangePerformance error:', error); return { exchanges: [] }; }
    return { exchanges: (data || []).map(r => ({ ...r, count: r.stock_count })) };
};
