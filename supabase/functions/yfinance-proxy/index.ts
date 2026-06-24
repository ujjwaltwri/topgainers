import { serve } from "https://deno.land/std@0.168.0/http/server.ts"

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
}

serve(async (req) => {
  // Handle CORS preflight requests
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders })
  }

  try {
    const url = new URL(req.url)
    let ticker = url.searchParams.get('ticker')
    let period = url.searchParams.get('period') || '1y'
    let interval = url.searchParams.get('interval') || '1d'

    if (req.method === 'POST') {
      try {
        const body = await req.json()
        if (body.ticker) ticker = body.ticker
        if (body.period) period = body.period
        if (body.interval) interval = body.interval
      } catch (e) {
        // ignore JSON parse errors
      }
    }

    if (!ticker) {
      return new Response(JSON.stringify({ error: 'Ticker is required' }), {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        status: 400,
      })
    }

    // Fetch from Yahoo Finance
    const yfUrl = `https://query1.finance.yahoo.com/v8/finance/chart/${ticker}?interval=${interval}&range=${period}`
    
    // Add headers to mimic a real browser to avoid 403 Forbidden from Yahoo
    const response = await fetch(yfUrl, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
      }
    })

    if (!response.ok) {
      return new Response(JSON.stringify({ error: `Yahoo Finance returned ${response.status}` }), {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        status: 502,
      })
    }

    const data = await response.json()
    
    // Parse the Yahoo Finance structure
    const result = data.chart?.result?.[0]
    if (!result) {
      return new Response(JSON.stringify({ error: 'No data found for ticker' }), {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        status: 404,
      })
    }

    const timestamps = result.timestamp || []
    const indicators = result.indicators?.quote?.[0] || {}
    
    const opens = indicators.open || []
    const highs = indicators.high || []
    const lows = indicators.low || []
    const closes = indicators.close || []
    const volumes = indicators.volume || []

    // Format for TradingView Lightweight Charts
    const chartData = []
    for (let i = 0; i < timestamps.length; i++) {
      if (closes[i] !== null && closes[i] !== undefined) {
        // TradingView uses YYYY-MM-DD for daily data
        const date = new Date(timestamps[i] * 1000)
        const timeString = date.toISOString().split('T')[0]
        
        chartData.push({
          date: timeString,
          open: opens[i],
          high: highs[i],
          low: lows[i],
          close: closes[i],
          volume: volumes[i] || 0
        })
      }
    }

    return new Response(JSON.stringify(chartData), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      status: 200,
    })

  } catch (error) {
    return new Response(JSON.stringify({ error: error.message }), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      status: 500,
    })
  }
})
