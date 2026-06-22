const { createClient } = require('@supabase/supabase-js');
const supabase = createClient('https://oqgwwidykukkqcgvvsnm.supabase.co', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9xZ3d3aWR5a3Vra3FjZ3Z2c25tIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODIxMjc5NDEsImV4cCI6MjA5NzcwMzk0MX0.Yk8nSX_7NCvPqfv0_8I0kPmZCWhyoH7QRICaz2i_fjw');

async function test() {
    let { count: stocksCount } = await supabase.from('stocks').select('*', { count: 'exact', head: true });
    let { count: gainsCount } = await supabase.from('gains').select('*', { count: 'exact', head: true });
    console.log("Stocks count:", stocksCount);
    console.log("Gains count:", gainsCount);
}
test();
