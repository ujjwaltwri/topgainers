import yfinance as yf
t = yf.Ticker("1757.HK")
df = t.history(period="1y")
print(f"Total trading days: {len(df)}")
print(df.head())
print("...")
print(df.tail())
