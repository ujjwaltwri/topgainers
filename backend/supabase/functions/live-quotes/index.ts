import "jsr:@supabase/functions-js/edge-runtime.d.ts"
import { corsHeaders } from '../_shared/cors.ts';

const YF_SPARK_URL = "https://query2.finance.yahoo.com/v8/finance/chart/";

Deno.serve(async (req) => {
  // Handle CORS preflight requests
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders });
  }

  try {
    const { tickers } = await req.json();

    if (!tickers || !Array.isArray(tickers) || tickers.length === 0) {
      return new Response(JSON.stringify({ error: "Missing or invalid tickers array" }), { 
        status: 400, 
        headers: { ...corsHeaders, 'Content-Type': 'application/json' } 
      });
    }

    // Limit to 50 tickers per request to avoid huge payloads/timeouts
    const batch = tickers.slice(0, 50);

    // Fetch spark data for all tickers in parallel
    const fetchPromises = batch.map(async (ticker) => {
      try {
        const url = `${YF_SPARK_URL}${encodeURIComponent(ticker)}?interval=1d&range=1d`;
        const res = await fetch(url, { headers: { 'User-Agent': 'Mozilla/5.0' } });
        
        if (!res.ok) {
          return { ticker, error: 'Failed to fetch' };
        }
        
        const data = await res.json();
        const result = data?.chart?.result?.[0];
        
        if (result && result.meta) {
          const currentPrice = result.meta.regularMarketPrice;
          const previousClose = result.meta.chartPreviousClose;
          let pctChange = 0;
          
          if (currentPrice && previousClose) {
            pctChange = ((currentPrice - previousClose) / previousClose) * 100;
          }
          
          return {
            ticker,
            price: currentPrice,
            pct_change: parseFloat(pctChange.toFixed(2))
          };
        }
        
        return { ticker, error: 'No data' };
      } catch (e) {
        return { ticker, error: e.message };
      }
    });

    const results = await Promise.all(fetchPromises);
    
    // Filter out errors and map to a clean object
    const liveData = results.reduce((acc, curr) => {
      if (!curr.error) {
        acc[curr.ticker] = curr;
      }
      return acc;
    }, {});

    return new Response(JSON.stringify({ data: liveData }), { 
      headers: { ...corsHeaders, 'Content-Type': 'application/json' } 
    });

  } catch (error) {
    return new Response(JSON.stringify({ error: error.message }), { 
      status: 500, 
      headers: { ...corsHeaders, 'Content-Type': 'application/json' } 
    });
  }
});
