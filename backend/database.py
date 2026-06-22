import sqlite3
import pandas as pd
from typing import List, Dict, Any, Optional

class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self.get_connection() as conn:
            conn.execute('PRAGMA journal_mode=WAL')
            self._create_tables(conn)

    def _create_tables(self, conn: sqlite3.Connection):
        conn.executescript('''
            CREATE TABLE IF NOT EXISTS stocks (
                ticker TEXT PRIMARY KEY,
                name TEXT,
                sector TEXT,
                industry TEXT,
                country TEXT,
                exchange TEXT,
                region TEXT,
                market_cap REAL,
                market_cap_tier TEXT,
                currency TEXT,
                ipo_date TEXT,
                pe_ratio REAL,
                revenue_growth REAL,
                earnings_growth REAL,
                dividend_yield REAL,
                recommendation TEXT,
                earnings_date TEXT,
                last_updated TEXT
            );

            CREATE TABLE IF NOT EXISTS price_history (
                ticker TEXT,
                date TEXT,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                adj_close REAL,
                volume INTEGER,
                PRIMARY KEY (ticker, date),
                FOREIGN KEY (ticker) REFERENCES stocks(ticker)
            );

            CREATE TABLE IF NOT EXISTS gains (
                ticker TEXT,
                period TEXT,
                pct_change REAL,
                abs_change REAL,
                start_price REAL,
                end_price REAL,
                start_date TEXT,
                end_date TEXT,
                avg_volume REAL,
                recent_volume REAL,
                volume_ratio REAL,
                sector_avg_change REAL,
                country_avg_change REAL,
                vs_sector REAL,
                vs_country REAL,
                high_52w REAL,
                low_52w REAL,
                pct_from_52w_high REAL,
                pct_from_52w_low REAL,
                at_52w_high BOOLEAN,
                at_52w_low BOOLEAN,
                volatility_30d REAL,
                max_drawdown REAL,
                sharpe_ratio REAL,
                pct_change_usd REAL,
                rsi_14 REAL,
                ma_50 REAL,
                ma_200 REAL,
                above_ma_50 BOOLEAN,
                above_ma_200 BOOLEAN,
                gain_streak INTEGER,
                PRIMARY KEY (ticker, period),
                FOREIGN KEY (ticker) REFERENCES stocks(ticker)
            );

            CREATE TABLE IF NOT EXISTS fx_rates (
                currency TEXT,
                date TEXT,
                rate_to_usd REAL,
                PRIMARY KEY (currency, date)
            );

            CREATE TABLE IF NOT EXISTS pipeline_meta (
                key TEXT PRIMARY KEY,
                value TEXT
            );
            
            -- Create performance indexes
            CREATE INDEX IF NOT EXISTS idx_gains_period_pct ON gains(period, pct_change DESC);
            CREATE INDEX IF NOT EXISTS idx_gains_period_pct_asc ON gains(period, pct_change ASC);
            CREATE INDEX IF NOT EXISTS idx_gains_sector ON gains(sector_avg_change, period, pct_change DESC);
            CREATE INDEX IF NOT EXISTS idx_gains_country ON gains(country_avg_change, period, pct_change DESC);
            CREATE INDEX IF NOT EXISTS idx_gains_volume ON gains(period, volume_ratio DESC);
            CREATE INDEX IF NOT EXISTS idx_gains_52w_high ON gains(period, at_52w_high, pct_change DESC);
            CREATE INDEX IF NOT EXISTS idx_gains_vs_sector ON gains(period, vs_sector DESC);
            CREATE INDEX IF NOT EXISTS idx_stocks_mcap ON stocks(market_cap DESC);
            CREATE INDEX IF NOT EXISTS idx_stocks_search ON stocks(ticker, name);
        ''')

    def get_top_movers(self, direction='gainers', period='6M', sector=None, industry=None, 
                       country=None, region=None, exchange=None, mcap_tiers=None, 
                       min_volume=None, min_price=None, max_price=None, min_pe=None, max_pe=None, 
                       at_52w_high=None, at_52w_low=None, volume_surge=None, 
                       sort_by='pct_change', limit=25, page=1):
        
        offset = (page - 1) * limit
        
        query = """
            SELECT s.*, g.* 
            FROM gains g
            JOIN stocks s ON g.ticker = s.ticker
            WHERE g.period = ?
        """
        params = [period]
        
        if sector:
            query += " AND s.sector = ?"
            params.append(sector)
        if industry:
            query += " AND s.industry = ?"
            params.append(industry)
        if country:
            query += " AND s.country = ?"
            params.append(country)
        if region:
            query += " AND s.region = ?"
            params.append(region)
        if exchange:
            query += " AND s.exchange = ?"
            params.append(exchange)
        if mcap_tiers:
            tiers = mcap_tiers.split(',')
            placeholders = ','.join(['?'] * len(tiers))
            query += f" AND s.market_cap_tier IN ({placeholders})"
            params.extend(tiers)
            
        if min_volume is not None:
            query += " AND g.avg_volume >= ?"
            params.append(min_volume)
        if min_price is not None:
            query += " AND g.end_price >= ?"
            params.append(min_price)
        if max_price is not None:
            query += " AND g.end_price <= ?"
            params.append(max_price)
            
        if min_pe is not None:
            query += " AND s.pe_ratio >= ?"
            params.append(min_pe)
        if max_pe is not None:
            query += " AND s.pe_ratio <= ?"
            params.append(max_pe)
            
        if at_52w_high:
            query += " AND g.at_52w_high = 1"
        if at_52w_low:
            query += " AND g.at_52w_low = 1"
        if volume_surge:
            query += " AND g.volume_ratio >= 3.0"

        order_dir = "DESC" if direction == 'gainers' else "ASC"
        
        allowed_sorts = ['pct_change', 'vs_sector', 'vs_country', 'volume_ratio', 'volatility_30d', 'market_cap', 'pe_ratio']
        if sort_by not in allowed_sorts:
            sort_by = 'pct_change'
            
        if sort_by in ['market_cap', 'pe_ratio']:
            query += f" ORDER BY s.{sort_by} {order_dir}"
        else:
            query += f" ORDER BY g.{sort_by} {order_dir}"
            
        count_query = f"SELECT COUNT(*) FROM ({query})"
        
        query += " LIMIT ? OFFSET ?"
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(count_query, params)
            total = cursor.fetchone()[0]
            
            params.extend([limit, offset])
            cursor.execute(query, params)
            results = [dict(row) for row in cursor.fetchall()]
            
        pages = (total + limit - 1) // limit
        
        return {
            'results': results,
            'total': total,
            'page': page,
            'pages': pages,
            'period': period,
            'direction': direction
        }

    def search_stocks(self, query: str, limit: int = 10):
        with self.get_connection() as conn:
            q = f"%{query}%"
            cursor = conn.cursor()
            cursor.execute("""
                SELECT ticker, name, sector, country, exchange, market_cap 
                FROM stocks 
                WHERE ticker LIKE ? OR name LIKE ? 
                ORDER BY market_cap DESC LIMIT ?
            """, (q, q, limit))
            return [dict(row) for row in cursor.fetchall()]

    def get_stock_detail(self, ticker: str):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM stocks WHERE ticker = ?", (ticker,))
            stock = cursor.fetchone()
            if not stock: return None
            
            cursor.execute("SELECT * FROM gains WHERE ticker = ?", (ticker,))
            gains_rows = cursor.fetchall()
            gains = {row['period']: dict(row) for row in gains_rows}
            
            cursor.execute("SELECT * FROM price_history WHERE ticker = ? ORDER BY date DESC LIMIT 365", (ticker,))
            prices = [dict(row) for row in cursor.fetchall()]
            
            return {
                'stock': dict(stock),
                'gains': gains,
                'price_history': prices
            }

    def get_available_filters(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            return {
                'sectors': [r[0] for r in cursor.execute("SELECT DISTINCT sector FROM stocks WHERE sector IS NOT NULL ORDER BY sector").fetchall()],
                'industries': [r[0] for r in cursor.execute("SELECT DISTINCT industry FROM stocks WHERE industry IS NOT NULL ORDER BY industry").fetchall()],
                'countries': [r[0] for r in cursor.execute("SELECT DISTINCT country FROM stocks WHERE country IS NOT NULL ORDER BY country").fetchall()],
                'exchanges': [r[0] for r in cursor.execute("SELECT DISTINCT exchange FROM stocks WHERE exchange IS NOT NULL ORDER BY exchange").fetchall()]
            }

    def get_stats(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            total_stocks = cursor.execute("SELECT COUNT(*) FROM stocks").fetchone()[0]
            total_prices = cursor.execute("SELECT COUNT(*) FROM price_history").fetchone()[0]
            last_updated = cursor.execute("SELECT value FROM pipeline_meta WHERE key = 'last_updated'").fetchone()
            
            exchanges = {}
            for row in cursor.execute("SELECT exchange, COUNT(*) as c FROM stocks GROUP BY exchange"):
                exchanges[row['exchange']] = row['c']
                
            return {
                'total_stocks': total_stocks,
                'total_prices': total_prices,
                'last_updated': last_updated[0] if last_updated else None,
                'exchanges': exchanges
            }

    def upsert_stocks(self, df: pd.DataFrame):
        with self.get_connection() as conn:
            df.to_sql('stocks', conn, if_exists='append', index=False)
            
    def upsert_prices(self, df: pd.DataFrame):
        with self.get_connection() as conn:
            df.to_sql('price_history', conn, if_exists='append', index=False)

    def upsert_gains(self, df: pd.DataFrame):
        with self.get_connection() as conn:
            df.to_sql('gains', conn, if_exists='append', index=False)
            
    def set_meta(self, key: str, value: str):
        with self.get_connection() as conn:
            conn.execute("INSERT OR REPLACE INTO pipeline_meta (key, value) VALUES (?, ?)", (key, value))
            
    def get_meta(self, key: str):
        with self.get_connection() as conn:
            row = conn.execute("SELECT value FROM pipeline_meta WHERE key = ?", (key,)).fetchone()
            return row[0] if row else None
