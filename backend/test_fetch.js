async function test() {
  const url = "https://xpmfwpqkykiqmswumoxu.supabase.co/rest/v1/gains_with_stocks?period=eq.6M&order=market_cap.desc.nullslast&limit=5";
  const key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InhwbWZ3cHFreWtpcW1zd3Vtb3h1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODIxNTEwNjYsImV4cCI6MjA5NzcyNzA2Nn0.TAFycwI-cScW88ynt9SZNkLUqskOxdO3e7PQh-zUZyk";
  
  const res = await fetch(url, {
    headers: {
      "apikey": key,
      "Authorization": `Bearer ${key}`
    }
  });
  const data = await res.json();
  console.log(typeof data[0].market_cap, data[0].market_cap);
  
  const totalMcap = data.reduce((sum, s) => sum + s.market_cap, 0);
  console.log("totalMcap:", typeof totalMcap, totalMcap);
}
test();
