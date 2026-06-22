const { createClient } = require('@supabase/supabase-js');
const SUPABASE_URL = 'https://oqgwwidykukkqcgvvsnm.supabase.co';
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9xZ3d3aWR5a3Vra3FjZ3Z2c25tIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODIxMjc5NDEsImV4cCI6MjA5NzcwMzk0MX0.Yk8nSX_7NCvPqfv0_8I0kPmZCWhyoH7QRICaz2i_fjw';
const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

async function test() {
    console.log("Fetching gains...");
    let query = supabase.from('gains').select('*, stocks!inner(*)', { count: 'exact' });
    query = query.eq('period', '6M');
    query = query.range(0, 24);
    
    const { data, error, count } = await query;
    if (error) {
        console.error("Error:", error);
    } else {
        console.log(`Success! Got ${data.length} records. Total count: ${count}`);
    }
}
test();
