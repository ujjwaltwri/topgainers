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
    
    let query = supabaseClient.from('gains_with_stocks').select('*', { count: 'exact' });
    query = query.eq('period', period);
    
    // Apply filters
    if (filters.sector) query = query.eq('sector', filters.sector);
    if (filters.industry) query = query.eq('industry', filters.industry);
    if (filters.country) query = query.eq('country', filters.country);
    
    if (filters.region) {
      // server.py maps region to a list of countries
      const regionsMap = {"Americas": ["United States", "Canada", "Brazil"], "Europe": ["United Kingdom", "Germany", "France", "Netherlands", "Switzerland"], "Asia-Pacific": ["India", "Japan", "China", "South Korea", "Hong Kong", "Australia", "Taiwan"], "Middle East": ["Saudi Arabia"]};
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
    
    query = query.order(sortCol, { ascending });
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
    const [{data: countries}, {data: sectors}, {data: industries}, {data: exchanges}] = await Promise.all([
        supabaseClient.rpc('get_distinct_countries'),
        supabaseClient.rpc('get_distinct_sectors'),
        supabaseClient.rpc('get_distinct_industries'),
        supabaseClient.rpc('get_distinct_exchanges')
    ]);

    return {
        sectors: sectors ? sectors.map(r => r.sector) : [],
        industries: industries ? industries.map(r => r.industry) : [],
        countries: countries ? countries.map(r => r.country) : [],
        exchanges: exchanges ? exchanges.map(r => r.exchange) : [],
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
    let allPrices = [];
    let offset = 0;
    while(true) {
        const { data } = await supabaseClient.from('price_history').select('*').eq('ticker', ticker).order('date', { ascending: true }).range(offset, offset + 999);
        if (!data || data.length === 0) break;
        allPrices = allPrices.concat(data);
        if (data.length < 1000) break;
        offset += 1000;
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
  
  async searchStocks(query) {
    const { data, error } = await supabaseClient
        .from('stocks')
        .select('ticker, name, sector, country, exchange, market_cap')
        .or(`ticker.ilike.%${query}%,name.ilike.%${query}%`)
        .limit(10);
        
    return { results: data || [] };
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
      .select('ticker, name, sector, market_cap, pct_change')
      .eq('period', period)
      .order('market_cap', { ascending: false })
      .limit(100);
      
    if (error) return { stocks: [] };
    
    return { stocks: data || [] };
};

window.SupabaseAPI.getSectorPerformance = async function(period) {
    let allData = [];
    let offset = 0;
    while(true) {
        const { data, error } = await supabaseClient
            .from('gains_with_stocks')
            .select('sector, pct_change')
            .eq('period', period)
            .range(offset, offset + 999);
            
        if (error || !data || data.length === 0) break;
        allData = allData.concat(data);
        if (data.length < 1000) break;
        offset += 1000;
    }

    const sectorsMap = {};
    allData.forEach(row => {
        if (!row.sector) return;
        if (!sectorsMap[row.sector]) {
            sectorsMap[row.sector] = { sector: row.sector, stock_count: 0, sum_change: 0, positive: 0, negative: 0 };
        }
        const s = sectorsMap[row.sector];
        s.stock_count++;
        s.sum_change += row.pct_change;
        if (row.pct_change > 0) s.positive++;
        else s.negative++;
    });

    const sectors = Object.values(sectorsMap).map(s => {
        return {
            sector: s.sector,
            stock_count: s.stock_count,
            avg_change: s.sum_change / s.stock_count,
            positive: s.positive,
            negative: s.negative
        };
    }).sort((a, b) => b.avg_change - a.avg_change);

    return { sectors };
};

window.SupabaseAPI.getCountryPerformance = async function(period) {
    let allData = [];
    let offset = 0;
    while(true) {
        const { data, error } = await supabaseClient
            .from('gains_with_stocks')
            .select('country, pct_change')
            .eq('period', period)
            .range(offset, offset + 999);
            
        if (error || !data || data.length === 0) break;
        allData = allData.concat(data);
        if (data.length < 1000) break;
        offset += 1000;
    }

    const countriesMap = {};
    allData.forEach(row => {
        if (!row.country) return;
        if (!countriesMap[row.country]) {
            countriesMap[row.country] = { country: row.country, stock_count: 0, sum_change: 0, positive: 0, negative: 0 };
        }
        const c = countriesMap[row.country];
        c.stock_count++;
        c.sum_change += row.pct_change;
        if (row.pct_change > 0) c.positive++;
        else c.negative++;
    });

    const countries = Object.values(countriesMap).map(c => {
        return {
            country: c.country,
            stock_count: c.stock_count,
            avg_change: c.sum_change / c.stock_count,
            positive: c.positive,
            negative: c.negative
        };
    }).sort((a, b) => b.avg_change - a.avg_change);

    return { countries };
};
