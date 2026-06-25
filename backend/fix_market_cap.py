"""
One-time migration: convert market_cap values in Supabase from USD back to native currency.

The pipeline was storing: market_cap = native_amount * fx_rate (already in USD)
But currency column still says e.g. 'KRW', so the frontend was double-converting.

Fix: market_cap = market_cap / fx_rate  => back to native currency.
The frontend's toUSD() will then do the single correct conversion at display time.
"""

import os
import yfinance as yf
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

FX_PAIRS = {
    'INR': 'INRUSD=X',
    'KRW': 'KRWUSD=X',
    'JPY': 'JPYUSD=X',
    'CNY': 'CNYUSD=X',
    'HKD': 'HKDUSD=X',
    'GBP': 'GBPUSD=X',
    'EUR': 'EURUSD=X',
    'CAD': 'CADUSD=X',
    'AUD': 'AUDUSD=X',
    'BRL': 'BRLUSD=X',
    'SAR': 'SARUSD=X',
    'TWD': 'TWDUSD=X',
    'SGD': 'SGDUSD=X',
    'MYR': 'MYRUSD=X',
    'IDR': 'IDRUSD=X',
    'THB': 'THBUSD=X',
    'PHP': 'PHPUSD=X',
    'NZD': 'NZDUSD=X',
    'CHF': 'CHFUSD=X',
    'SEK': 'SEKUSD=X',
    'NOK': 'NOKUSD=X',
    'DKK': 'DKKUSD=X',
    'PLN': 'PLNUSD=X',
    'MXN': 'MXNUSD=X',
    'ARS': 'ARSUSD=X',
    'CLP': 'CLPUSD=X',
    'ILS': 'ILSUSD=X',
    'TRY': 'TRYUSD=X',
    'EGP': 'EGPUSD=X',
    'QAR': 'QARUSD=X',
    'AED': 'AEDUSD=X',
    'ZAR': 'ZARUSD=X',
}

MCAP_TIERS = {
    'mega':  (200e9, float('inf')),
    'large': (10e9, 200e9),
    'mid':   (2e9, 10e9),
    'small': (300e6, 2e9),
    'micro': (50e6, 300e6),
    'nano':  (0, 50e6),
}

def get_market_cap_tier(usd_val):
    if not usd_val:
        return None
    for tier, (lo, hi) in MCAP_TIERS.items():
        if lo <= usd_val < hi:
            return tier
    return None

def fetch_fx_rates():
    rates = {'USD': 1.0}
    tickers = list(FX_PAIRS.values())
    print("Fetching FX rates...")
    data = yf.download(tickers, period='5d', group_by='ticker', progress=False)
    for currency, ticker in FX_PAIRS.items():
        try:
            if len(tickers) == 1:
                rates[currency] = float(data['Close'].dropna().iloc[-1])
            else:
                if ticker in data.columns.get_level_values(0):
                    rates[currency] = float(data[ticker]['Close'].dropna().iloc[-1])
        except Exception as e:
            print(f"  Could not get FX for {currency}: {e}")
    print(f"Loaded rates for: {list(rates.keys())}")
    return rates

def main():
    supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))
    fx_rates = fetch_fx_rates()

    # Fetch all stocks with non-USD currency and non-null market cap (paginated)
    print("Fetching stocks from Supabase...")
    rows = []
    offset, chunk = 0, 1000
    while True:
        resp = supabase.table('stocks').select('ticker, currency, market_cap').neq('currency', 'USD').not_.is_('market_cap', 'null').range(offset, offset + chunk - 1).execute()
        batch = resp.data
        if not batch:
            break
        rows += batch
        offset += chunk
        if len(batch) < chunk:
            break
    print(f"Found {len(rows)} non-USD stocks with market cap")

    updates = []
    skipped = []
    for row in rows:
        currency = row['currency']
        mcap = row['market_cap']
        rate = fx_rates.get(currency)
        if not rate:
            skipped.append(row['ticker'])
            continue
        # Current stored value is: native * rate (i.e. USD)
        # We want to store: native = stored / rate
        native_mcap = mcap / rate
        mcap_usd = mcap  # current stored value is already USD
        updates.append({
            'ticker': row['ticker'],
            'market_cap': native_mcap,
            'market_cap_tier': get_market_cap_tier(mcap_usd),
        })

    print(f"Skipped {len(skipped)} tickers (unknown currency FX rate): {skipped[:10]}")
    print(f"Updating {len(updates)} rows...")

    # Upsert in chunks of 500
    chunk_size = 500
    for i in range(0, len(updates), chunk_size):
        chunk = updates[i:i+chunk_size]
        supabase.table('stocks').upsert(chunk).execute()
        print(f"  Upserted rows {i+1}–{min(i+chunk_size, len(updates))}")

    print("Done. market_cap values are now in native currency.")
    print("Spot check a few:")
    for t in ['005930.KS', '7203.T', 'RELIANCE.NS']:
        r = supabase.table('stocks').select('ticker, currency, market_cap, market_cap_tier').eq('ticker', t).execute()
        if r.data:
            print(f"  {r.data[0]}")

if __name__ == '__main__':
    main()
