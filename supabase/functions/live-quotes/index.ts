import { serve } from "https://deno.land/std@0.168.0/http/server.ts"

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
}

const YF_HEADERS = {
  'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
  'Accept': 'application/json',
  'Accept-Language': 'en-US,en;q=0.9',
  'Referer': 'https://finance.yahoo.com/',
  'Origin': 'https://finance.yahoo.com',
}

async function fetchQuote(ticker: string): Promise<{ ticker: string; price: number; pct_change: number; prev_close: number } | null> {
  try {
    // v8 chart with 1d range, 1d interval — same endpoint that yfinance-proxy uses (known working)
    const url = `https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(ticker)}?interval=1d&range=5d`
    const res = await fetch(url, { headers: YF_HEADERS })
    if (!res.ok) return null

    const json = await res.json()
    const result = json?.chart?.result?.[0]
    if (!result) return null

    const closes = result.indicators?.quote?.[0]?.close || []
    const meta = result.meta || {}

    // Filter out nulls
    const validCloses = closes.filter((c: number | null) => c !== null && c !== undefined)
    if (validCloses.length < 2) return null

    const price = meta.regularMarketPrice ?? validCloses[validCloses.length - 1]
    const prev_close = meta.chartPreviousClose ?? meta.previousClose ?? validCloses[validCloses.length - 2]
    const pct_change = prev_close ? ((price - prev_close) / prev_close) * 100 : 0

    return { ticker, price, pct_change, prev_close }
  } catch {
    return null
  }
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

    // Fetch all in parallel, cap at 25 (what's visible on screen)
    const results = await Promise.all(tickers.slice(0, 25).map(fetchQuote))

    const data: Record<string, object> = {}
    for (const q of results) {
      if (q) data[q.ticker] = q
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
