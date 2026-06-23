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
    const { ticker, name, pct_change } = await req.json();
    if (!ticker) return new Response(JSON.stringify({ error: "Missing ticker" }), { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } });

    const newsItems = await getStockNews(ticker);
    const headlines = newsItems.map((n: any) => `- ${n.title} (${n.publisher})`).join('\n');
    const direction = parseFloat(pct_change) >= 0 ? 'up' : 'down';
    const prompt = `You are a financial analyst. The stock ${name || ticker} (${ticker}) is currently moving ${direction} by ${pct_change}%.
News:
${headlines || 'No recent news.'}
Provide a 2-3 sentence extremely concise summary explaining WHY this stock is moving. Do not give financial advice. Get straight to the point.`;

    const token = await getAccessToken();
    const gcpProjectId = Deno.env.get('GCP_PROJECT_ID');
    const gcpLocation = Deno.env.get('GCP_LOCATION');
    const url = `https://${gcpLocation}-aiplatform.googleapis.com/v1/projects/${gcpProjectId}/locations/${gcpLocation}/publishers/google/models/gemini-2.5-flash:generateContent`;
    
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({
        contents: [{ role: "user", parts: [{ text: prompt }] }],
        systemInstruction: { parts: [{ text: "You are an elite financial analyst. Keep responses under 3 sentences." }] },
        generationConfig: { temperature: 0.2 }
      })
    });

    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();
    const text = data.candidates?.[0]?.content?.parts?.[0]?.text || "No insights generated.";

    return new Response(JSON.stringify({ result: text }), { headers: { ...corsHeaders, 'Content-Type': 'application/json' } });
  } catch (error) {
    return new Response(JSON.stringify({ error: error.message }), { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } });
  }
});
