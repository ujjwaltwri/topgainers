import os
import time
import argparse
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import yfinance as yf
import financedatabase as fd
from tqdm import tqdm
import logging
from config import EXCHANGES, TIME_PERIODS, MCAP_TIERS, DB_PATH
from database import Database

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class DataPipeline:
    def __init__(self, db_path: str = DB_PATH, min_mcap: float = 0):
        self.db = Database(db_path)
        self.min_mcap = min_mcap

    def compute_rsi(self, prices: pd.Series, period: int = 14) -> float:
        if len(prices) < period + 1:
            return None
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else None

    def compute_max_drawdown(self, prices: pd.Series) -> float:
        if len(prices) == 0:
            return None
        roll_max = prices.cummax()
        drawdown = prices / roll_max - 1.0
        return drawdown.min()

    def compute_volatility(self, prices: pd.Series, period: int = 30) -> float:
        if len(prices) < 2:
            return None
        returns = prices.pct_change().dropna()
        # Annualized volatility (assuming 252 trading days)
        return returns.std() * np.sqrt(252)

    def compute_gain_streak(self, prices: pd.Series) -> int:
        if len(prices) < 2:
            return 0
        returns = prices.pct_change().dropna()
        streak = 0
        for r in reversed(returns):
            if r > 0:
                streak += 1
            else:
                break
        return streak

    def get_market_cap_tier(self, mcap: float) -> str:
        if pd.isna(mcap) or mcap is None:
            return None
        for tier, (low, high) in MCAP_TIERS.items():
            if low <= mcap < high:
                return tier
        return None

    def run_full(self, exchanges_to_process=None, limit=None):
        logging.info("Starting full data pipeline run...")
        
        # 1. Load Equities
        equities = fd.Equities()
        all_stocks = []
        
        exchanges_list = exchanges_to_process if exchanges_to_process else EXCHANGES.keys()
        
        for exch_name in exchanges_list:
            if exch_name not in EXCHANGES:
                logging.warning(f"Unknown exchange: {exch_name}")
                continue
                
            exch_info = EXCHANGES[exch_name]
            country = exch_info['country']
            
            try:
                # Get stocks for this country
                # FinanceDatabase might use different exchange names, so we filter by country first
                country_stocks = equities.select(country=country)
                
                # Further filter or just take all for the country if we want broad coverage
                # For simplicity, taking all common stocks in the country
                df = equities.show_options('country')
                if country in df:
                   country_stocks = equities.select(country=country)

                   
                for symbol, row in country_stocks.iterrows():
                    details = row.to_dict()
                    # Handle ticker suffix mapping
                    yf_ticker = f"{symbol}{exch_info['suffix']}"
                    # Remove any spaces or weird chars
                    yf_ticker = yf_ticker.replace(" ", "").split(".")[0] + exch_info['suffix']
                    
                    all_stocks.append({
                        'ticker': yf_ticker,
                        'name': details.get('name', ''),
                        'sector': details.get('sector', ''),
                        'industry': details.get('industry', ''),
                        'country': country,
                        'exchange': exch_name,
                        'region': exch_info['region'],
                        'currency': exch_info['currency']
                    })
            except Exception as e:
                logging.error(f"Error loading stocks for {country}: {e}")

        # Remove duplicates
        unique_stocks = {s['ticker']: s for s in all_stocks}.values()
        tickers = [s['ticker'] for s in unique_stocks]
        
        if limit:
            tickers = tickers[:limit]
            unique_stocks = list(unique_stocks)[:limit]
            
        logging.info(f"Found {len(tickers)} tickers to process")
        
        if len(tickers) == 0:
            logging.error("No tickers found, aborting pipeline.")
            return

        # Insert initial stocks to DB
        stocks_df = pd.DataFrame(unique_stocks)
        # Ensure all columns exist
        for col in ['market_cap', 'market_cap_tier', 'ipo_date', 'pe_ratio', 'revenue_growth', 'earnings_growth', 'dividend_yield', 'recommendation', 'earnings_date', 'last_updated']:
            if col not in stocks_df.columns:
                stocks_df[col] = None
                
        # SQLite doesn't have UPSERT in older pandas to_sql, so we might need a workaround or just replace
        # We'll use a transaction to replace records
        with self.db.get_connection() as conn:
            # Create a temporary table
            stocks_df.to_sql('stocks_temp', conn, if_exists='replace', index=False)
            conn.execute('''
                INSERT OR REPLACE INTO stocks (ticker, name, sector, industry, country, exchange, region, market_cap, market_cap_tier, currency, ipo_date, pe_ratio, revenue_growth, earnings_growth, dividend_yield, recommendation, earnings_date, last_updated)
                SELECT ticker, name, sector, industry, country, exchange, region, market_cap, market_cap_tier, currency, ipo_date, pe_ratio, revenue_growth, earnings_growth, dividend_yield, recommendation, earnings_date, last_updated FROM stocks_temp
            ''')
            conn.execute('DROP TABLE stocks_temp')

        # Download prices in batches
        batch_size = 50
        all_prices = []
        all_gains = []
        updated_stocks = []
        
        for i in tqdm(range(0, len(tickers), batch_size), desc="Downloading prices"):
            batch = tickers[i:i+batch_size]
            try:
                # yf.download returns a multi-index dataframe if multiple tickers
                data = yf.download(batch, period='5y', interval='1d', group_by='ticker', threads=True, progress=False)
                time.sleep(1) # Rate limit
                
                # Fetch .info for fundamentals (this is slow, so we do it cautiously)
                for ticker in batch:
                    try:
                        # Extract single ticker data
                        if len(batch) == 1:
                            df = data.copy()
                        else:
                            if ticker not in data.columns.get_level_values(0):
                                continue
                            df = data[ticker].copy()
                            
                        df = df.dropna(how='all')
                        if df.empty: continue
                        
                        df.reset_index(inplace=True)
                        df['ticker'] = ticker
                        df.rename(columns={'Date': 'date', 'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Adj Close': 'adj_close', 'Volume': 'volume'}, inplace=True)
                        
                        # Convert date to string
                        df['date'] = df['date'].dt.strftime('%Y-%m-%d')
                        
                        # Keep only necessary columns
                        cols = ['ticker', 'date', 'open', 'high', 'low', 'close', 'adj_close', 'volume']
                        # Ensure all columns exist, handle missing 'adj_close'
                        for col in cols:
                            if col not in df.columns:
                                df[col] = df['close'] if col == 'adj_close' else None
                        
                        df = df[cols]
                        
                        # Store prices
                        all_prices.append(df)
                        
                        # Computations
                        prices = df['close']
                        volumes = df['volume']
                        
                        if len(prices) < 2: continue
                        
                        current_price = prices.iloc[-1]
                        current_date = df['date'].iloc[-1]
                        
                        # Fundamentals (fetch occasionally or lazily, here we do a quick fetch)
                        # To save time in tests, we skip info fetch or do it minimally
                        # t_info = yf.Ticker(ticker).info
                        # mcap = t_info.get('marketCap')
                        mcap = None # Skipping info fetch for speed in MVP, rely on price * volume as proxy or null
                        
                        updated_stocks.append({
                            'ticker': ticker,
                            'market_cap': mcap,
                            'market_cap_tier': self.get_market_cap_tier(mcap),
                            'last_updated': datetime.now().isoformat()
                        })
                        
                        # Compute gains
                        recent_vol = volumes.iloc[-5:].mean() if len(volumes) >=5 else volumes.mean()
                        rsi_14 = self.compute_rsi(prices)
                        ma_50 = prices.rolling(50).mean().iloc[-1] if len(prices) >= 50 else None
                        ma_200 = prices.rolling(200).mean().iloc[-1] if len(prices) >= 200 else None
                        streak = self.compute_gain_streak(prices)
                        
                        # Last 252 days for 52W
                        last_year_df = df.iloc[-252:] if len(df) > 252 else df
                        high_52w = last_year_df['high'].max()
                        low_52w = last_year_df['low'].min()
                        
                        at_high = high_52w is not None and current_price >= high_52w * (1 - 0.02)
                        at_low = low_52w is not None and current_price <= low_52w * (1 + 0.02)
                        
                        for period_name, days in TIME_PERIODS:
                            if period_name == 'YTD':
                                start_of_year = f"{datetime.now().year}-01-01"
                                period_df = df[df['date'] >= start_of_year]
                            elif period_name == 'MAX' or period_name == 'CUSTOM':
                                period_df = df
                            else:
                                period_df = df.iloc[-days:] if len(df) > days else df
                                
                            if len(period_df) < 2: continue
                            
                            start_price = period_df['close'].iloc[0]
                            end_price = period_df['close'].iloc[-1]
                            start_date = period_df['date'].iloc[0]
                            end_date = period_df['date'].iloc[-1]
                            
                            pct_change = ((end_price / start_price) - 1) * 100 if start_price else 0
                            abs_change = end_price - start_price
                            
                            avg_vol = period_df['volume'].mean()
                            vol_ratio = recent_vol / avg_vol if avg_vol else 1.0
                            
                            drawdown = self.compute_max_drawdown(period_df['close'])
                            volatility = self.compute_volatility(period_df['close'])
                            
                            all_gains.append({
                                'ticker': ticker,
                                'period': period_name,
                                'pct_change': pct_change,
                                'abs_change': abs_change,
                                'start_price': start_price,
                                'end_price': end_price,
                                'start_date': start_date,
                                'end_date': end_date,
                                'avg_volume': avg_vol,
                                'recent_volume': recent_vol,
                                'volume_ratio': vol_ratio,
                                'high_52w': high_52w,
                                'low_52w': low_52w,
                                'at_52w_high': at_high,
                                'at_52w_low': at_low,
                                'volatility_30d': volatility,
                                'max_drawdown': drawdown,
                                'rsi_14': rsi_14,
                                'ma_50': ma_50,
                                'ma_200': ma_200,
                                'gain_streak': streak,
                                # placeholders for relative metrics
                                'sector_avg_change': None,
                                'country_avg_change': None,
                                'vs_sector': None,
                                'vs_country': None
                            })
                            
                    except Exception as e:
                        logging.error(f"Error processing ticker {ticker}: {e}")
                        
            except Exception as e:
                logging.error(f"Error downloading batch {i}: {e}")

        # Update Database
        if all_prices:
            prices_df = pd.concat(all_prices, ignore_index=True)
            with self.db.get_connection() as conn:
                prices_df.to_sql('prices_temp', conn, if_exists='replace', index=False)
                conn.execute('''
                    INSERT OR REPLACE INTO price_history (ticker, date, open, high, low, close, adj_close, volume)
                    SELECT ticker, date, open, high, low, close, adj_close, volume FROM prices_temp
                ''')
                conn.execute('DROP TABLE prices_temp')

        if all_gains:
            gains_df = pd.DataFrame(all_gains)
            # Compute sector/country averages
            
            with self.db.get_connection() as conn:
                gains_df.to_sql('gains_temp', conn, if_exists='replace', index=False)
                conn.execute('''
                    INSERT OR REPLACE INTO gains (ticker, period, pct_change, abs_change, start_price, end_price, start_date, end_date, avg_volume, recent_volume, volume_ratio, high_52w, low_52w, at_52w_high, at_52w_low, volatility_30d, max_drawdown, rsi_14, ma_50, ma_200, gain_streak)
                    SELECT ticker, period, pct_change, abs_change, start_price, end_price, start_date, end_date, avg_volume, recent_volume, volume_ratio, high_52w, low_52w, at_52w_high, at_52w_low, volatility_30d, max_drawdown, rsi_14, ma_50, ma_200, gain_streak FROM gains_temp
                ''')
                
                # Update relative strength
                conn.execute('''
                    UPDATE gains SET
                        sector_avg_change = (SELECT AVG(g2.pct_change) FROM gains g2 JOIN stocks s2 ON g2.ticker = s2.ticker WHERE g2.period = gains.period AND s2.sector = (SELECT sector FROM stocks WHERE ticker = gains.ticker)),
                        country_avg_change = (SELECT AVG(g2.pct_change) FROM gains g2 JOIN stocks s2 ON g2.ticker = s2.ticker WHERE g2.period = gains.period AND s2.country = (SELECT country FROM stocks WHERE ticker = gains.ticker))
                ''')
                conn.execute('''
                    UPDATE gains SET
                        vs_sector = pct_change - sector_avg_change,
                        vs_country = pct_change - country_avg_change
                ''')
                
                conn.execute('DROP TABLE gains_temp')
                
        if updated_stocks:
            ustocks_df = pd.DataFrame(updated_stocks)
            with self.db.get_connection() as conn:
                for _, row in ustocks_df.iterrows():
                    conn.execute('''
                        UPDATE stocks SET 
                            market_cap = COALESCE(?, market_cap), 
                            market_cap_tier = COALESCE(?, market_cap_tier), 
                            last_updated = ? 
                        WHERE ticker = ?
                    ''', (row['market_cap'], row['market_cap_tier'], row['last_updated'], row['ticker']))

        self.db.set_meta('last_updated', datetime.now().isoformat())
        logging.info("Pipeline run complete.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--full', action='store_true', help='Run full download')
    parser.add_argument('--exchanges', nargs='+', help='Specific exchanges to update')
    parser.add_argument('--limit', type=int, help='Limit number of tickers (for testing)')
    args = parser.parse_args()
    
    pipeline = DataPipeline()
    if args.full or args.exchanges:
        pipeline.run_full(exchanges_to_process=args.exchanges, limit=args.limit)
    else:
        print("Please specify --full or --exchanges")
