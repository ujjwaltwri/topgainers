import yfinance as yf

t = yf.Ticker("1757.HK")
hist = t.history(period="1mo")
print(hist)
print("---")
print(t.fast_info)
