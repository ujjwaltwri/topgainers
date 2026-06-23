import os
from supabase import create_client

url = "https://xpmfwpqkykiqmswumoxu.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InhwbWZ3cHFreWtpcW1zd3Vtb3h1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODIxNTEwNjYsImV4cCI6MjA5NzcyNzA2Nn0.TAFycwI-cScW88ynt9SZNkLUqskOxdO3e7PQh-zUZyk"
supabase = create_client(url, key)

response = supabase.table('gains_with_stocks').select('ticker, name, sector, market_cap, pct_change').eq('period', '6M').limit(5).execute()
print(response.data)
