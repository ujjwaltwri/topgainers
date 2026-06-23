import "jsr:@supabase/functions-js/edge-runtime.d.ts"
import { GoogleAuth } from 'npm:google-auth-library@9.10.0';
import { corsHeaders } from '../_shared/cors.ts';

const YF_SEARCH_URL = "https://query2.finance.yahoo.com/v1/finance/search";

async function getStockNews(ticker: string) {
  try {
    const url = `${YF_SEARCH_URL}?q=${encodeURIComponent(ticker)}`;
    const res = await fetch(url, { headers: { 'User-Agent': 'Mozilla/5.0' } });
    if (!res.ok) return [];
    const data = await res.json();
    return data.news || [];
  } catch (err) {
    return [];
  }
}

async function getAccessToken(): Promise<string> {
  const saJson = Deno.env.get("GCP_SERVICE_ACCOUNT_JSON");
  if (!saJson) throw new Error("Missing GCP_SERVICE_ACCOUNT_JSON");
  const auth = new GoogleAuth({
    credentials: JSON.parse(saJson),
    scopes: ['https://www.googleapis.com/auth/cloud-platform']
  });
  const client = await auth.getClient();
  const token = await client.getAccessToken();
  return token.token;
}

Deno.serve(async (req) => {
  if (req.method === 'OPTIONS') return new Response('ok', { headers: corsHeaders });
  try {
    const body = await req.json();
    const { ticker, name, pct_change, sector, industry, market_cap, pe_ratio, at_52w_high, at_52w_low, volume_ratio } = body;
    if (!ticker) return new Response(JSON.stringify({ error: "Missing ticker" }), { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } });

    const rawNews = await getStockNews(ticker);
    // Filter out generic news that doesn't mention the ticker to avoid AI hallucination/confusion
    const newsItems = rawNews.filter((n: any) => {
      const matchTicker = n.relatedTickers?.includes(ticker);
      const matchName = name && n.title.toLowerCase().includes(name.split(' ')[0].toLowerCase());
      return matchTicker || matchName;
    });

    const headlines = newsItems.slice(0, 3).map((n: any) => `- ${n.title} (${n.publisher})`).join('\n');
    const direction = parseFloat(pct_change) >= 0 ? 'up' : 'down';
    
    const context = `
Sector: ${sector || 'Unknown'}
Industry: ${industry || 'Unknown'}
Market Cap: ${market_cap || 'Unknown'}
PE Ratio: ${pe_ratio || 'N/A'}
At 52W High: ${at_52w_high ? 'Yes' : 'No'}
At 52W Low: ${at_52w_low ? 'Yes' : 'No'}
Volume Ratio: ${volume_ratio ? volume_ratio + 'x average' : 'Normal'}
`;

    const prompt = `You are an elite financial analyst. The stock ${name || ticker} (${ticker}) is currently moving ${direction} by ${pct_change}%.

Context: ${context}
News:
${headlines || 'No recent specific news.'}

Provide a 2-3 sentence extremely concise summary explaining WHY this stock might be moving.
CRITICAL INSTRUCTION: If there is no specific news, DO NOT mention the lack of news, DO NOT complain that the articles don't mention the stock, and DO NOT say you cannot determine the reason. Instead, synthesize a plausible explanation based on its sector (${sector}), technical signals (like 52W high/low), volume surge, and general market dynamics. Sound confident and professional. Get straight to the point.`;

    const token = await getAccessToken();
    const gcpProjectId = Deno.env.get('GCP_PROJECT_ID');
    const gcpLocation = Deno.env.get('GCP_LOCATION');
    const url = `https://${gcpLocation}-aiplatform.googleapis.com/v1/projects/${gcpProjectId}/locations/${gcpLocation}/publishers/google/models/gemini-2.5-flash:generateContent`;
    
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({
        contents: [{ role: "user", parts: [{ text: prompt }] }],
        tools: [{ googleSearch: {} }],
        systemInstruction: { parts: [{ text: "You are an elite financial analyst. Keep responses under 3 sentences." }] },
        generationConfig: { temperature: 0.2 }
      })
    });

    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();
    let text = data.candidates?.[0]?.content?.parts?.[0]?.text || "No insights generated.";
    
    // Extract live Google Search grounding links
    const groundingChunks = data.candidates?.[0]?.groundingMetadata?.groundingChunks || [];
    for (const chunk of groundingChunks) {
      if (chunk.web?.uri && chunk.web?.title) {
        newsItems.push({
          title: chunk.web.title,
          link: chunk.web.uri,
          publisher: 'Google Search'
        });
      }
    }
    
    // Fallback cleanup if the model disobeys
    text = text.replace(/The provided news articles do not mention.*?\./g, '');
    text = text.replace(/Therefore, the reason for its significant upward movement cannot be determined from the given articles\./g, '');

    return new Response(JSON.stringify({ result: text.trim(), news: newsItems }), { headers: { ...corsHeaders, 'Content-Type': 'application/json' } });
  } catch (error) {
    return new Response(JSON.stringify({ error: error.message }), { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } });
  }
});
