import yfinance as yf
t = yf.Ticker('CAU.L')
print(t.history(period="5d"))
