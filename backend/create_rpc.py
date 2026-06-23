import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

sql = """
CREATE OR REPLACE FUNCTION get_exchange_performance(period_param text)
RETURNS TABLE (
  name text,
  avg_change numeric
) AS $$
BEGIN
  RETURN QUERY
  SELECT 
    s.exchange as name,
    AVG(g.pct_change)::numeric as avg_change
  FROM gains g
  JOIN stocks s ON g.ticker = s.ticker
  WHERE g.period = period_param AND s.exchange IS NOT NULL
  GROUP BY s.exchange
  ORDER BY avg_change DESC;
END;
$$ LANGUAGE plpgsql;
"""

response = supabase.rpc('exec_sql', {'sql_string': sql}).execute()
print(response)
