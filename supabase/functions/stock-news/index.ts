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

interface NewsItem {
  title: string
  publisher: string
  link: string
  providerPublishTime: number
}

async function fetchNews(ticker: string): Promise<NewsItem[]> {
  try {
    const url = `https://query2.finance.yahoo.com/v1/finance/search?q=${encodeURIComponent(ticker)}&newsCount=8&enableFuzzyQuery=false&enableCb=false&enableNavLinks=false&enableEnhancedTrivialQuery=false`
    const res = await fetch(url, { headers: YF_HEADERS })
    if (!res.ok) return []

    const json = await res.json()
    const raw: Array<Record<string, unknown>> = json?.news ?? []

    return raw
      .filter((item) => typeof item.title === 'string' && item.title.length > 0)
      .map((item) => ({
        title: item.title as string,
        publisher: (item.publisher as string) ?? '',
        link: (item.link as string) ?? '',
        providerPublishTime: (item.providerPublishTime as number) ?? 0,
      }))
  } catch {
    return []
  }
}

serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders })
  }

  try {
    const body = await req.json()
    const ticker: string = body.ticker || ''

    if (!ticker) {
      return new Response(JSON.stringify({ error: 'ticker required' }), {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        status: 400,
      })
    }

    const news = await fetchNews(ticker)

    return new Response(JSON.stringify({ news }), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      status: 200,
    })

  } catch {
    return new Response(JSON.stringify({ news: [] }), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      status: 200,
    })
  }
})
