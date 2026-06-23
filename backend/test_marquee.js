const { createClient } = require('@supabase/supabase-js');
require('dotenv').config();

const supabaseClient = createClient(
  process.env.SUPABASE_URL,
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InhwbWZ3cHFreWtpcW1zd3Vtb3h1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODIxNTEwNjYsImV4cCI6MjA5NzcyNzA2Nn0.TAFycwI-cScW88ynt9SZNkLUqskOxdO3e7PQh-zUZyk"
);

async function test() {
  const { data, error } = await supabaseClient
    .from('gains')
    .select('pct_change, stocks!inner(exchange)')
    .eq('period', '6M')
    .not('stocks.exchange', 'is', null)
    .neq('stocks.exchange', '')
    .limit(10);
  console.log("Error:", error);
  console.log("Data:", data);
}
test();
