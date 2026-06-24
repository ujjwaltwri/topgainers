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

// Batch fetch up to 25 tickers in a single request using the spark endpoint
async function fetchBatchQuotes(tickers: string[]): Promise<Record<string, { ticker: string; price: number; pct_change: number; prev_close: number }>> {
  const symbols = tickers.slice(0, 25).map(encodeURIComponent).join(',')
  const url = `https://query1.finance.yahoo.com/v8/finance/spark?symbols=${symbols}&range=1d&interval=5m`

  try {
    const res = await fetch(url, { headers: YF_HEADERS })
    if (!res.ok) return {}

    const json = await res.json()
    const result: Record<string, { ticker: string; price: number; pct_change: number; prev_close: number }> = {}

    for (const ticker of tickers) {
      const sym = json?.[ticker]
      if (!sym) continue

      const closes: (number | null)[] = sym.close || []
      const validCloses = closes.filter((c): c is number => c !== null && c !== undefined)
      if (validCloses.length === 0) continue

      const price = validCloses[validCloses.length - 1]
      const prev_close = sym.previousClose ?? validCloses[0]
      if (!prev_close) continue

      const pct_change = ((price - prev_close) / prev_close) * 100
      result[ticker] = { ticker, price, pct_change, prev_close }
    }

    return result
  } catch {
    return {}
  }
}

// Fallback: single ticker via v8 chart (used when spark returns nothing for a ticker)
async function fetchSingleQuote(ticker: string): Promise<{ ticker: string; price: number; pct_change: number; prev_close: number } | null> {
  try {
    const url = `https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(ticker)}?interval=1d&range=5d`
    const res = await fetch(url, { headers: YF_HEADERS })
    if (!res.ok) return null

    const json = await res.json()
    const result = json?.chart?.result?.[0]
    if (!result) return null

    const closes = result.indicators?.quote?.[0]?.close || []
    const meta = result.meta || {}
    const validCloses = closes.filter((c: number | null) => c !== null && c !== undefined)
    if (validCloses.length < 2) return null

    const price = meta.regularMarketPrice ?? validCloses[validCloses.length - 1]
    const lastClose = validCloses[validCloses.length - 1]
    const isMarketClosed = lastClose && Math.abs(price - lastClose) / lastClose < 0.001
    const prev_close = isMarketClosed
      ? validCloses[validCloses.length - 2]
      : lastClose ?? meta.chartPreviousClose ?? meta.previousClose
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

    // One batch request for all tickers
    const batchResults = await fetchBatchQuotes(tickers)

    // For any ticker the spark endpoint missed, fall back to single v8 chart calls
    const missing = tickers.filter(t => !batchResults[t])
    if (missing.length > 0) {
      const fallbacks = await Promise.all(missing.map(fetchSingleQuote))
      for (const q of fallbacks) {
        if (q) batchResults[q.ticker] = q
      }
    }

    return new Response(JSON.stringify({ data: batchResults }), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      status: 200,
    })

  } catch (error) {
    return new Response(JSON.stringify({ error: (error as Error).message }), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      status: 500,
    })
  }
})
