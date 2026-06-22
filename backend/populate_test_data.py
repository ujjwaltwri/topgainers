import os
import random
import sqlite3
from datetime import datetime, timedelta

def populate():
    db_path = '../data/stocks.db'
    conn = sqlite3.connect(db_path)
    
    tickers = ['AAPL', 'MSFT', 'NVDA', 'TSLA', 'AMZN', 'META', 'GOOGL', 'PLTR', 'GME', 'AMC', 'RELIANCE.NS', 'TCS.NS', 'SMCGLOBAL.NS']
    
    # 1. Insert Stocks
    for t in tickers:
        conn.execute('''
            INSERT OR REPLACE INTO stocks (ticker, name, sector, industry, country, exchange, region, market_cap, market_cap_tier, currency, ipo_date, pe_ratio, revenue_growth, earnings_growth, dividend_yield, recommendation, earnings_date, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            t, f"{t} Inc.", 'Technology', 'Software', 
            'United States' if not t.endswith('.NS') else 'India',
            'NASDAQ' if not t.endswith('.NS') else 'NSE',
            'Americas' if not t.endswith('.NS') else 'Asia-Pacific',
            random.randint(1e9, 2e12), 'large',
            'USD' if not t.endswith('.NS') else 'INR',
            '2000-01-01', 30.5, 0.15, 0.20, 0.01, 'Buy', '2023-10-01', datetime.now().isoformat()
        ))

    # 2. Insert Gains for multiple periods
    periods = ['1D', '5D', '1M', '3M', '6M', '1Y', '2Y', '3Y', '5Y', 'YTD', 'MAX']
    for t in tickers:
        for p in periods:
            pct_change = random.uniform(-10.0, 50.0) if p != '1D' else random.uniform(-3.0, 5.0)
            if t == 'NVDA': pct_change += 20.0 # Make NVDA a top gainer
            
            conn.execute('''
                INSERT OR REPLACE INTO gains (
                    ticker, period, pct_change, abs_change, start_price, end_price, start_date, end_date, 
                    avg_volume, recent_volume, volume_ratio, high_52w, low_52w, at_52w_high, at_52w_low, 
                    volatility_30d, max_drawdown, rsi_14, ma_50, ma_200, gain_streak, sector_avg_change, country_avg_change, vs_sector, vs_country
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                t, p, pct_change, 10.0, 100.0, 110.0, '2023-01-01', '2023-06-01',
                1000000, 1500000, 1.5, 120.0, 80.0, 
                1 if random.random() > 0.8 else 0, # at_52w_high
                1 if random.random() > 0.9 else 0, # at_52w_low
                0.25, -0.15, 65.0, 105.0, 95.0, 3,
                5.0, 4.0, pct_change - 5.0, pct_change - 4.0
            ))
            
    conn.commit()
    conn.close()
    print(f"Inserted {len(tickers)} mock stocks and gains!")
    
if __name__ == '__main__':
    populate()
