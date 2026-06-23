import sqlite3
import pandas as pd

conn = sqlite3.connect('../data/stocks.db')

# Find stocks with > 500% gains in any period
query = """
SELECT g.ticker, s.name, g.period, g.pct_change, g.avg_volume
FROM gains g
JOIN stocks s ON g.ticker = s.ticker
WHERE g.pct_change > 300 AND g.period = '6M'
ORDER BY g.pct_change DESC
"""
df = pd.read_sql_query(query, conn)
print(f"Stocks with >300% 6M gains: {len(df)}")
print(df.head(20))

conn.close()
