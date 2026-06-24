import { serve } from "https://deno.land/std@0.168.0/http/server.ts"

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
}

serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders })
  }

  try {
    let tickers: string[] = []

    if (req.method === 'POST') {
      const body = await req.json()
      tickers = body.tickers || []
    } else {
      const url = new URL(req.url)
      const t = url.searchParams.get('tickers')
      if (t) tickers = t.split(',')
    }

    if (!tickers.length) {
      return new Response(JSON.stringify({ error: 'tickers required' }), {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        status: 400,
      })
    }

    // Yahoo Finance batch quote endpoint — handles up to ~200 tickers per call
    const symbols = tickers.slice(0, 100).join(',')
    const yfUrl = `https://query1.finance.yahoo.com/v7/finance/quote?symbols=${symbols}&fields=regularMarketPrice,regularMarketChangePercent,regularMarketPreviousClose`

    const response = await fetch(yfUrl, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
      },
    })

    if (!response.ok) {
      return new Response(JSON.stringify({ error: `Yahoo Finance ${response.status}` }), {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        status: 502,
      })
    }

    const json = await response.json()
    const quotes = json?.quoteResponse?.result || []

    const data: Record<string, { ticker: string; price: number; pct_change: number; prev_close: number }> = {}

    for (const q of quotes) {
      if (q.regularMarketPrice !== undefined) {
        data[q.symbol] = {
          ticker: q.symbol,
          price: q.regularMarketPrice,
          pct_change: q.regularMarketChangePercent ?? 0,
          prev_close: q.regularMarketPreviousClose ?? q.regularMarketPrice,
        }
      }
    }

    return new Response(JSON.stringify({ data }), {
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
