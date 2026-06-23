import financedatabase as fd
import yfinance as yf

equities = fd.Equities()
df_eq = equities.select(country="South Korea")
print(df_eq.head())

t = yf.Ticker("352770.KS")
print(t.info.get('shortName'), t.info.get('longName'))
