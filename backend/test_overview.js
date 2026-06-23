const { createClient } = require('@supabase/supabase-js');
require('dotenv').config();

const supabaseClient = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_KEY);

const period = '1D';

async function test() {
  try {
    const statsResult = await supabaseClient.from('pipeline_meta').select('*');
    console.log("Stats error:", statsResult.error);

    const breadthResult = await supabaseClient.rpc('get_market_breadth', { period_param: period });
    console.log("Breadth error:", breadthResult.error);
    console.log("Breadth data:", breadthResult.data);

    const treemapResult = await supabaseClient
      .from('gains_with_stocks')
      .select('ticker, name, sector, market_cap, pct_change')
      .eq('period', period)
      .order('market_cap', { ascending: false })
      .limit(100);
    console.log("Treemap error:", treemapResult.error);
    console.log("Treemap length:", treemapResult.data?.length);
  } catch (e) {
    console.error("Crash:", e);
  }
}
test();
