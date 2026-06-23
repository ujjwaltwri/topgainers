import "jsr:@supabase/functions-js/edge-runtime.d.ts"
import { GoogleAuth } from 'npm:google-auth-library@9.10.0';
import { corsHeaders } from '../_shared/cors.ts';

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
    const { stocks } = await req.json();
    if (!stocks || !Array.isArray(stocks) || stocks.length < 2) {
      return new Response(JSON.stringify({ error: "Must provide at least 2 stocks" }), { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } });
    }

    let stocksData = '';
    for (const s of stocks) {
      stocksData += `\n**${s.name || s.ticker} (${s.ticker})**\n- Sector: ${s.sector}\n- Gain: ${s.pct_change}%\n- Market Cap: ${s.market_cap}\n- P/E: ${s.pe_ratio}\n- Vol Ratio: ${s.volume_ratio}x\n`;
    }

    const prompt = `Compare these stocks based on their metrics and sector. Provide a concise, highly insightful comparison highlighting which looks structurally stronger. Keep it under 3 paragraphs. Do not give financial advice.
Data:${stocksData}`;

    const token = await getAccessToken();
    const gcpProjectId = Deno.env.get('GCP_PROJECT_ID');
    const gcpLocation = Deno.env.get('GCP_LOCATION');
    const url = `https://${gcpLocation}-aiplatform.googleapis.com/v1/projects/${gcpProjectId}/locations/${gcpLocation}/publishers/google/models/gemini-2.5-flash:generateContent`;
    
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({
        contents: [{ role: "user", parts: [{ text: prompt }] }],
        systemInstruction: { parts: [{ text: "You are an elite quantitative analyst." }] },
        generationConfig: { temperature: 0.3 }
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
