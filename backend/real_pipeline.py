#!/usr/bin/env python3
"""
real_pipeline.py — Production data pipeline for TopGainers.
Fetches REAL stock data via yfinance using a curated ticker list.
No dependency on financedatabase.

Usage:
    python real_pipeline.py --exchanges US India --limit 100
    python real_pipeline.py --exchanges US India Japan Korea UK Germany HongKong Canada Australia Brazil --full
    python real_pipeline.py --all
"""

import os
import sys
import time
import argparse
import sqlite3
from datetime import datetime, timedelta
from collections import OrderedDict
import pandas as pd
import numpy as np
import yfinance as yf
import logging

# ── Local imports ────────────────────────────────────────────────────────────
from config import EXCHANGES, TIME_PERIODS, MCAP_TIERS, DB_PATH, FX_PAIRS
from database import Database

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s │ %(levelname)-7s │ %(message)s',
    datefmt='%H:%M:%S',
)
log = logging.getLogger('real_pipeline')

# ═══════════════════════════════════════════════════════════════════════════════
# 1.  CURATED TICKER LISTS (organised by "exchange group")
# ═══════════════════════════════════════════════════════════════════════════════

TICKER_LISTS = {
    # ── US (NYSE + NASDAQ) ──────────────────────────────────────────────────
    'US': {
        'exchange': 'NYSE',           # primary label for the DB
        'country': 'United States',
        'region': 'Americas',
        'currency': 'USD',
        'tickers': [
            # Mega-cap tech
            'AAPL', 'MSFT', 'NVDA', 'TSLA', 'AMZN', 'META', 'GOOGL', 'GOOG',
            'NFLX', 'AMD', 'INTC', 'QCOM', 'AVGO', 'CRM', 'ORCL', 'ADBE',
            'CSCO', 'TXN', 'MU', 'MRVL', 'LRCX', 'AMAT', 'KLAC', 'ON',
            'MCHP', 'SWKS', 'QRVO',
            # AI / Data / Cloud / Cyber
            'SMCI', 'PLTR', 'SNOW', 'DDOG', 'NET', 'CRWD', 'ZS', 'PANW', 'FTNT',
            # Fintech
            'SQ', 'PYPL', 'COIN', 'HOOD', 'SOFI', 'AFRM', 'UPST',
            # Space / Quantum / Speculative
            'RKLB', 'JOBY', 'LUNR', 'ASTS', 'IONQ', 'RGTI', 'QUBT',
            # Meme / Retail
            'GME', 'AMC', 'BB', 'NOK', 'SOUN', 'BBAI',
            # Bitcoin miners / HPC
            'APLD', 'IREN', 'CORZ', 'BTBT', 'MARA', 'RIOT', 'CLSK', 'CIFR',
            'HUT', 'BITF',
            # Financials
            'JPM', 'BAC', 'WFC', 'GS', 'MS', 'C', 'BX', 'KKR', 'APO', 'ARES',
            'V', 'MA', 'AXP',
            # Media / Telecom
            'DIS', 'CMCSA', 'T', 'VZ', 'TMUS',
            # Consumer
            'WMT', 'COST', 'TGT', 'HD', 'LOW', 'MCD', 'SBUX', 'NKE',
            'PEP', 'KO', 'PG',
            # Healthcare / Pharma
            'JNJ', 'UNH', 'LLY', 'MRK', 'ABBV', 'PFE', 'BMY', 'GILD',
            'AMGN', 'BIIB', 'MRNA', 'BNTX', 'TMO', 'DHR', 'ABT', 'MDT',
            'SYK', 'ISRG', 'BSX', 'EW', 'ZTS', 'DXCM', 'ALGN', 'HIMS',
            # Energy / Oil & Gas
            'XOM', 'CVX', 'COP', 'EOG', 'SLB', 'OXY', 'DVN', 'MPC',
            'PSX', 'VLO', 'HAL', 'BKR',
            # Renewables
            'FSLR', 'ENPH', 'RUN', 'SEDG',
            # Utilities
            'NEE', 'DUK', 'SO', 'AEP', 'D', 'EXC', 'SRE',
            # Aerospace / Defense / Industrials
            'BA', 'LMT', 'RTX', 'GD', 'NOC', 'GE', 'HON', 'CAT', 'DE',
            'MMM', 'EMR', 'ETN', 'ITW', 'CMI',
            # Ride-hailing / Travel
            'UBER', 'LYFT', 'ABNB', 'DASH', 'BKNG', 'EXPE', 'MAR', 'HLT',
            # Airlines
            'LUV', 'DAL', 'UAL', 'AAL',
            # Autos / EV
            'F', 'GM', 'RIVN', 'LCID', 'NIO', 'XPEV', 'LI',
            # (FSR delisted, skip)
        ],
    },

    # ── India (NSE) ─────────────────────────────────────────────────────────
    'India': {
        'exchange': 'NSE',
        'country': 'India',
        'region': 'Asia-Pacific',
        'currency': 'INR',
        'tickers': [
            'RELIANCE.NS', 'TCS.NS', 'INFY.NS', 'HDFCBANK.NS', 'ICICIBANK.NS',
            'HINDUNILVR.NS', 'ITC.NS', 'SBIN.NS', 'BHARTIARTL.NS', 'LT.NS',
            'KOTAKBANK.NS', 'AXISBANK.NS', 'TITAN.NS', 'BAJFINANCE.NS',
            'ASIANPAINT.NS', 'MARUTI.NS', 'HCLTECH.NS', 'SUNPHARMA.NS',
            'WIPRO.NS', 'ULTRACEMCO.NS', 'TATAMOTORS.NS', 'TATASTEEL.NS',
            'ONGC.NS', 'NTPC.NS', 'POWERGRID.NS', 'COALINDIA.NS', 'JSWSTEEL.NS',
            'TECHM.NS', 'ADANIENT.NS', 'ADANIPORTS.NS', 'BAJAJFINSV.NS',
            'DIVISLAB.NS', 'DRREDDY.NS', 'CIPLA.NS', 'EICHERMOT.NS',
            'GRASIM.NS', 'HEROMOTOCO.NS', 'HINDALCO.NS', 'INDUSINDBK.NS',
            'M&M.NS', 'NESTLEIND.NS', 'SBILIFE.NS', 'TATACONSUM.NS',
            'APOLLOHOSP.NS', 'BPCL.NS', 'BRITANNIA.NS', 'HDFCLIFE.NS',
            'VEDL.NS', 'ZOMATO.NS', 'PAYTM.NS', 'NYKAA.NS', 'POLICYBZR.NS',
            'DELHIVERY.NS', 'YESBANK.NS', 'IDEA.NS', 'IRCTC.NS', 'HAL.NS',
            'BEL.NS', 'BHEL.NS', 'IRFC.NS', 'RVNL.NS', 'NHPC.NS', 'SJVN.NS',
            'RECLTD.NS', 'PFC.NS', 'TATAPOWER.NS', 'ADANIGREEN.NS',
            'ADANIPOWER.NS', 'SUZLON.NS', 'TRENT.NS', 'ZYDUSLIFE.NS',
            'MANKIND.NS', 'LICI.NS', 'JIOFIN.NS',
        ],
    },

    # ── Japan (TSE) ─────────────────────────────────────────────────────────
    'Japan': {
        'exchange': 'TSE',
        'country': 'Japan',
        'region': 'Asia-Pacific',
        'currency': 'JPY',
        'tickers': [
            '7203.T', '6758.T', '6861.T', '9984.T', '6902.T', '7741.T',
            '8306.T', '8316.T', '9432.T', '6501.T', '6594.T', '7974.T',
            '4502.T', '4661.T', '6367.T',
        ],
    },

    # ── South Korea (KOSPI) ─────────────────────────────────────────────────
    'Korea': {
        'exchange': 'KOSPI',
        'country': 'South Korea',
        'region': 'Asia-Pacific',
        'currency': 'KRW',
        'tickers': [
            '005930.KS', '000660.KS', '373220.KS', '005490.KS', '035420.KS',
            '035720.KS', '051910.KS', '006400.KS', '005380.KS',
        ],
    },

    # ── UK (LSE) ────────────────────────────────────────────────────────────
    'UK': {
        'exchange': 'LSE',
        'country': 'United Kingdom',
        'region': 'Europe',
        'currency': 'GBP',
        'tickers': [
            'AZN.L', 'SHEL.L', 'ULVR.L', 'HSBA.L', 'BP.L', 'GSK.L',
            'RIO.L', 'LSEG.L', 'DGE.L', 'REL.L', 'NG.L',
        ],
    },

    # ── Germany (XETRA) ────────────────────────────────────────────────────
    'Germany': {
        'exchange': 'XETRA',
        'country': 'Germany',
        'region': 'Europe',
        'currency': 'EUR',
        'tickers': [
            'SAP.DE', 'SIE.DE', 'ALV.DE', 'DTE.DE', 'BAS.DE', 'MBG.DE',
            'BMW.DE', 'MRK.DE', 'ADS.DE',
        ],
    },

    # ── Hong Kong (HKEX) ───────────────────────────────────────────────────
    'HongKong': {
        'exchange': 'HKEX',
        'country': 'Hong Kong',
        'region': 'Asia-Pacific',
        'currency': 'HKD',
        'tickers': [
            '9988.HK', '0700.HK', '3690.HK', '9618.HK', '1211.HK',
            '0005.HK', '0941.HK',
        ],
    },

    # ── Canada (TSX) ───────────────────────────────────────────────────────
    'Canada': {
        'exchange': 'TSX',
        'country': 'Canada',
        'region': 'Americas',
        'currency': 'CAD',
        'tickers': [
            'RY.TO', 'TD.TO', 'ENB.TO', 'CNR.TO', 'BN.TO', 'CP.TO',
            'BMO.TO', 'SHOP.TO', 'BCE.TO', 'SU.TO',
        ],
    },

    # ── Australia (ASX) ────────────────────────────────────────────────────
    'Australia': {
        'exchange': 'ASX',
        'country': 'Australia',
        'region': 'Asia-Pacific',
        'currency': 'AUD',
        'tickers': [
            'BHP.AX', 'CBA.AX', 'CSL.AX', 'NAB.AX', 'WBC.AX', 'ANZ.AX',
            'FMG.AX', 'WDS.AX', 'MQG.AX', 'WES.AX',
        ],
    },

    # ── Brazil (B3) ────────────────────────────────────────────────────────
    'Brazil': {
        'exchange': 'B3',
        'country': 'Brazil',
        'region': 'Americas',
        'currency': 'BRL',
        'tickers': [
            'PETR4.SA', 'VALE3.SA', 'ITUB4.SA', 'BBDC4.SA', 'B3SA3.SA',
            'ABEV3.SA', 'WEGE3.SA', 'RENT3.SA', 'BBAS3.SA', 'SUZB3.SA',
        ],
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# 2.  METRICS HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def compute_rsi(prices: pd.Series, period: int = 14):
    """Wilder-smoothed RSI-14."""
    if len(prices) < period + 1:
        return None
    delta = prices.diff()
    gain = delta.where(delta > 0, 0.0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100.0 - (100.0 / (1.0 + rs))
    val = rsi.iloc[-1]
    return float(val) if not pd.isna(val) else None


def compute_max_drawdown(prices: pd.Series):
    if len(prices) < 2:
        return None
    cummax = prices.cummax()
    dd = (prices / cummax) - 1.0
    return float(dd.min())


def compute_volatility(prices: pd.Series, window: int = 30):
    """30-day annualised volatility."""
    if len(prices) < max(window, 2):
        return None
    rets = prices.pct_change().dropna().iloc[-window:]
    return float(rets.std() * np.sqrt(252))


def compute_gain_streak(prices: pd.Series) -> int:
    if len(prices) < 2:
        return 0
    rets = prices.pct_change().dropna()
    streak = 0
    for r in reversed(rets.values):
        if r > 0:
            streak += 1
        else:
            break
    return streak


def compute_sharpe(prices: pd.Series, risk_free_annual: float = 0.05):
    """Annualised Sharpe ratio (excess return / volatility)."""
    if len(prices) < 30:
        return None
    rets = prices.pct_change().dropna()
    daily_rf = (1 + risk_free_annual) ** (1/252) - 1
    excess = rets - daily_rf
    if excess.std() == 0:
        return None
    return float((excess.mean() / excess.std()) * np.sqrt(252))


def get_market_cap_tier(mcap):
    if mcap is None or (isinstance(mcap, float) and np.isnan(mcap)):
        return None
    for tier, (lo, hi) in MCAP_TIERS.items():
        if lo <= mcap < hi:
            return tier
    return None


# ═══════════════════════════════════════════════════════════════════════════════
# 3.  MAIN PIPELINE CLASS
# ═══════════════════════════════════════════════════════════════════════════════

class RealPipeline:
    """Fetches real market data and populates the SQLite database."""

    def __init__(self, db_path: str = DB_PATH, batch_size: int = 25):
        self.db = Database(db_path)
        self.batch_size = batch_size
        # Counters
        self.stats = {
            'tickers_attempted': 0,
            'tickers_ok': 0,
            'tickers_failed': 0,
            'prices_inserted': 0,
            'gains_computed': 0,
            'info_fetched': 0,
            'failures': [],
        }
        self.fx_rates = {'USD': 1.0}

    def _fetch_fx_rates(self):
        log.info("Fetching FX rates...")
        try:
            tickers = list(FX_PAIRS.values())
            data = yf.download(tickers, period='5d', group_by='ticker', progress=False)
            for currency, ticker in FX_PAIRS.items():
                try:
                    if len(tickers) == 1:
                        self.fx_rates[currency] = float(data['Close'].dropna().iloc[-1])
                    else:
                        if ticker in data.columns.get_level_values(0):
                            self.fx_rates[currency] = float(data[ticker]['Close'].dropna().iloc[-1])
                except Exception as e:
                    log.warning(f"Could not get FX for {currency}: {e}")
        except Exception as e:
            log.error(f"Failed to download FX rates: {e}")
        log.info(f"Loaded FX rates: {self.fx_rates}")

    # ── build the list of (ticker, metadata) tuples ────────────────────────
    def _resolve_tickers(self, exchange_groups, limit=None):
        """Return list of dicts with ticker + metadata."""
        result = []
        for grp_name in exchange_groups:
            grp = TICKER_LISTS.get(grp_name)
            if grp is None:
                log.warning(f"Unknown exchange group '{grp_name}'. "
                            f"Available: {list(TICKER_LISTS.keys())}")
                continue
            for t in grp['tickers']:
                result.append({
                    'ticker': t,
                    'exchange': grp['exchange'],
                    'country': grp['country'],
                    'region': grp['region'],
                    'currency': grp['currency'],
                })
        # de-dup by ticker
        seen = set()
        deduped = []
        for r in result:
            if r['ticker'] not in seen:
                seen.add(r['ticker'])
                deduped.append(r)
        if limit and limit < len(deduped):
            deduped = deduped[:limit]
        return deduped

    # ── download price history for a batch of tickers ──────────────────────
    def _download_batch(self, tickers: list[str]) -> dict[str, pd.DataFrame]:
        """Download 5Y daily data for a list of tickers.
        Returns {ticker: DataFrame} for those that succeeded."""
        result = {}
        try:
            data = yf.download(
                tickers,
                period='5y',
                interval='1d',
                group_by='ticker',
                threads=True,
                progress=False,
            )
            if data is None or data.empty:
                return result

            for ticker in tickers:
                try:
                    if len(tickers) == 1:
                        df = data.copy()
                    else:
                        # Multi-ticker: columns are (Ticker, OHLCV)
                        if ticker not in data.columns.get_level_values(0):
                            continue
                        df = data[ticker].copy()

                    df = df.dropna(how='all')
                    if df.empty:
                        continue

                    df = df.reset_index()

                    # Normalise column names (yfinance >= 0.2.x uses different casing)
                    col_map = {}
                    for c in df.columns:
                        cl = str(c).lower().replace(' ', '_')
                        if cl == 'date':       col_map[c] = 'date'
                        elif cl == 'open':     col_map[c] = 'open'
                        elif cl == 'high':     col_map[c] = 'high'
                        elif cl == 'low':      col_map[c] = 'low'
                        elif cl == 'close':    col_map[c] = 'close'
                        elif cl in ('adj_close', 'adj close', 'adjclose'):
                            col_map[c] = 'adj_close'
                        elif cl == 'volume':   col_map[c] = 'volume'
                    df = df.rename(columns=col_map)

                    # Make sure we have a 'date' column
                    if 'date' not in df.columns:
                        # Might be 'Date' or index-based
                        if 'Date' in df.columns:
                            df = df.rename(columns={'Date': 'date'})
                        else:
                            continue

                    # Add adj_close if missing
                    if 'adj_close' not in df.columns:
                        df['adj_close'] = df['close']

                    # Convert dates
                    df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
                    df['ticker'] = ticker

                    df = df[['ticker', 'date', 'open', 'high', 'low',
                             'close', 'adj_close', 'volume']]

                    # Drop rows where close is NaN
                    df = df.dropna(subset=['close'])

                    if len(df) >= 2:
                        result[ticker] = df

                except Exception as e:
                    log.debug(f"  ↳ skip {ticker} in batch parse: {e}")

        except Exception as e:
            log.error(f"yf.download failed for batch: {e}")

        return result

    # ── fetch .info fundamentals for a single ticker ──────────────────────
    def _fetch_info(self, ticker: str) -> dict:
        """Fetch yf.Ticker(ticker).info — returns a dict of fields we care about."""
        defaults = {
            'name': None, 'sector': None, 'industry': None,
            'market_cap': None, 'pe_ratio': None, 'revenue_growth': None,
            'earnings_growth': None, 'dividend_yield': None,
            'recommendation': None, 'info_country': None,
        }
        try:
            info = yf.Ticker(ticker).info
            if not info or not isinstance(info, dict):
                return defaults
            defaults['name'] = info.get('longName') or info.get('shortName')
            defaults['sector'] = info.get('sector')
            defaults['industry'] = info.get('industry')
            defaults['market_cap'] = info.get('marketCap')
            defaults['pe_ratio'] = info.get('trailingPE')
            defaults['revenue_growth'] = info.get('revenueGrowth')
            defaults['earnings_growth'] = info.get('earningsGrowth')
            defaults['dividend_yield'] = info.get('dividendYield')
            defaults['recommendation'] = info.get('recommendationKey')
            defaults['info_country'] = info.get('country')
            defaults['currency'] = info.get('currency')
            self.stats['info_fetched'] += 1
        except Exception as e:
            log.debug(f"  ↳ .info failed for {ticker}: {e}")
        return defaults

    # ── compute all gain metrics for a single ticker ──────────────────────
    def _compute_gains(self, ticker: str, df: pd.DataFrame) -> list[dict]:
        """Compute gains for all TIME_PERIODS. Returns list of gain dicts."""
        gains = []
        prices = df['close'].astype(float)
        volumes = df['volume'].astype(float)

        if len(prices) < 2:
            return gains

        current_price = float(prices.iloc[-1])

        # Pre-compute shared metrics
        rsi_14 = compute_rsi(prices)
        ma_50 = float(prices.rolling(50).mean().iloc[-1]) if len(prices) >= 50 else None
        ma_200 = float(prices.rolling(200).mean().iloc[-1]) if len(prices) >= 200 else None
        above_ma_50 = bool(current_price >= ma_50) if ma_50 is not None else None
        above_ma_200 = bool(current_price >= ma_200) if ma_200 is not None else None
        streak = compute_gain_streak(prices)
        recent_vol = float(volumes.iloc[-5:].mean()) if len(volumes) >= 5 else float(volumes.mean())

        # 52-week high/low from last 252 trading days
        last_year = df.iloc[-252:] if len(df) > 252 else df
        high_52w = float(last_year['high'].max())
        low_52w = float(last_year['low'].min())
        pct_from_52w_high = ((current_price - high_52w) / high_52w * 100) if high_52w else None
        pct_from_52w_low = ((current_price - low_52w) / low_52w * 100) if low_52w else None
        at_52w_high = bool(current_price >= high_52w * 0.98)  # within 2%
        at_52w_low = bool(current_price <= low_52w * 1.02)

        for period_name, days in TIME_PERIODS:
            try:
                if period_name == 'CUSTOM':
                    continue  # skip CUSTOM, not applicable for pipeline

                if period_name == 'YTD':
                    start_of_year = f"{datetime.now().year}-01-01"
                    period_df = df[df['date'] >= start_of_year]
                elif period_name == 'MAX':
                    period_df = df
                else:
                    period_df = df.iloc[-days:] if len(df) > days else df

                if len(period_df) < 2:
                    continue

                p_prices = period_df['close'].astype(float)
                start_price = float(p_prices.iloc[0])
                end_price = float(p_prices.iloc[-1])
                start_date = period_df['date'].iloc[0]
                end_date = period_df['date'].iloc[-1]

                if start_price == 0:
                    continue

                pct_change = ((end_price / start_price) - 1.0) * 100.0
                abs_change = end_price - start_price

                avg_vol = float(period_df['volume'].mean())
                vol_ratio = float(recent_vol / avg_vol) if avg_vol > 0 else 1.0

                drawdown = compute_max_drawdown(p_prices)
                volatility = compute_volatility(p_prices)
                sharpe = compute_sharpe(p_prices)

                gains.append({
                    'ticker': ticker,
                    'period': period_name,
                    'pct_change': round(pct_change, 4),
                    'abs_change': round(abs_change, 4),
                    'start_price': round(start_price, 4),
                    'end_price': round(end_price, 4),
                    'start_date': start_date,
                    'end_date': end_date,
                    'avg_volume': round(avg_vol, 0),
                    'recent_volume': round(recent_vol, 0),
                    'volume_ratio': round(vol_ratio, 4),
                    'high_52w': round(high_52w, 4),
                    'low_52w': round(low_52w, 4),
                    'pct_from_52w_high': round(pct_from_52w_high, 4) if pct_from_52w_high is not None else None,
                    'pct_from_52w_low': round(pct_from_52w_low, 4) if pct_from_52w_low is not None else None,
                    'at_52w_high': at_52w_high,
                    'at_52w_low': at_52w_low,
                    'volatility_30d': round(volatility, 4) if volatility is not None else None,
                    'max_drawdown': round(drawdown, 4) if drawdown is not None else None,
                    'sharpe_ratio': round(sharpe, 4) if sharpe is not None else None,
                    'pct_change_usd': None,  # filled later for non-USD
                    'rsi_14': round(rsi_14, 4) if rsi_14 is not None else None,
                    'ma_50': round(ma_50, 4) if ma_50 is not None else None,
                    'ma_200': round(ma_200, 4) if ma_200 is not None else None,
                    'above_ma_50': above_ma_50,
                    'above_ma_200': above_ma_200,
                    'gain_streak': streak,
                    # placeholders — filled in bulk after all tickers
                    'sector_avg_change': None,
                    'country_avg_change': None,
                    'vs_sector': None,
                    'vs_country': None,
                })
                self.stats['gains_computed'] += 1

            except Exception as e:
                log.debug(f"  ↳ gains error for {ticker}/{period_name}: {e}")

        return gains

    # ── MAIN RUN ──────────────────────────────────────────────────────────
    def run(self, exchange_groups: list[str], limit: int | None = None):
        t0 = time.time()
        log.info("=" * 70)
        log.info("  TopGainers Real Pipeline — Starting")
        log.info("=" * 70)

        self._fetch_fx_rates()

        # 1. Resolve tickers
        ticker_metas = self._resolve_tickers(exchange_groups, limit)
        tickers = [m['ticker'] for m in ticker_metas]
        meta_lookup = {m['ticker']: m for m in ticker_metas}
        self.stats['tickers_attempted'] = len(tickers)

        log.info(f"Resolved {len(tickers)} tickers from groups: {exchange_groups}")

        if not tickers:
            log.error("No tickers to process — aborting.")
            return

        # 2. Download prices in batches
        all_prices: list[pd.DataFrame] = []
        all_gains: list[dict] = []
        stock_rows: list[dict] = []
        ok_tickers = set()

        n_batches = (len(tickers) + self.batch_size - 1) // self.batch_size

        for batch_idx in range(0, len(tickers), self.batch_size):
            batch = tickers[batch_idx: batch_idx + self.batch_size]
            batch_num = batch_idx // self.batch_size + 1
            log.info(f"Processing batch {batch_num}/{n_batches} "
                     f"({len(batch)} tickers) ... "
                     f"[{len(ok_tickers)} successful so far]")

            # 2a. Download price history
            ticker_dfs = self._download_batch(batch)

            # 2b. For each ticker that has data, compute metrics + fetch .info
            for ticker in batch:
                if ticker not in ticker_dfs:
                    self.stats['tickers_failed'] += 1
                    self.stats['failures'].append(ticker)
                    continue

                df = ticker_dfs[ticker]
                meta = meta_lookup[ticker]

                try:
                    # Compute gains
                    gains = self._compute_gains(ticker, df)
                    if not gains:
                        self.stats['tickers_failed'] += 1
                        self.stats['failures'].append(ticker)
                        continue

                    all_gains.extend(gains)
                    all_prices.append(df)
                    ok_tickers.add(ticker)
                    self.stats['tickers_ok'] += 1

                except Exception as e:
                    log.error(f"  ✗ {ticker} — metrics error: {e}")
                    self.stats['tickers_failed'] += 1
                    self.stats['failures'].append(ticker)
                    continue

                # 2c. Fetch .info (with rate limiting)
                try:
                    info = self._fetch_info(ticker)
                    stock_rows.append({
                        'ticker': ticker,
                        'name': info['name'],
                        'sector': info['sector'],
                        'industry': info['industry'],
                        'country': info.get('info_country') or meta['country'],
                        'exchange': meta['exchange'],
                        'region': meta['region'],
                        'market_cap': info['market_cap'] * self.fx_rates.get(info.get('currency') or meta['currency'], 1.0) if info['market_cap'] else None,
                        'market_cap_tier': get_market_cap_tier(info['market_cap'] * self.fx_rates.get(info.get('currency') or meta['currency'], 1.0) if info['market_cap'] else None),
                        'currency': meta['currency'],
                        'ipo_date': None,
                        'pe_ratio': info['pe_ratio'],
                        'revenue_growth': info['revenue_growth'],
                        'earnings_growth': info['earnings_growth'],
                        'dividend_yield': info['dividend_yield'],
                        'recommendation': info['recommendation'],
                        'earnings_date': None,
                        'last_updated': datetime.now().isoformat(),
                    })
                    time.sleep(0.5)  # rate-limit .info calls

                except Exception as e:
                    log.debug(f"  ↳ info/stock_row error {ticker}: {e}")
                    # Still create a row with what we have
                    stock_rows.append({
                        'ticker': ticker,
                        'name': ticker,
                        'sector': None,
                        'industry': None,
                        'country': meta['country'],
                        'exchange': meta['exchange'],
                        'region': meta['region'],
                        'market_cap': None,
                        'market_cap_tier': None,
                        'currency': meta['currency'],
                        'ipo_date': None,
                        'pe_ratio': None,
                        'revenue_growth': None,
                        'earnings_growth': None,
                        'dividend_yield': None,
                        'recommendation': None,
                        'earnings_date': None,
                        'last_updated': datetime.now().isoformat(),
                    })

            # Rate-limit between batches
            if batch_idx + self.batch_size < len(tickers):
                log.info("  … sleeping 2s (rate limit)")
                time.sleep(2)

        # ── 3. Write to SQLite ─────────────────────────────────────────────
        log.info("-" * 70)
        log.info("Writing data to SQLite …")

        # 3a. Stocks table
        if stock_rows:
            stocks_df = pd.DataFrame(stock_rows)
            with self.db.get_connection() as conn:
                stocks_df.to_sql('stocks_temp', conn, if_exists='replace', index=False)
                conn.execute('''
                    INSERT OR REPLACE INTO stocks
                        (ticker, name, sector, industry, country, exchange,
                         region, market_cap, market_cap_tier, currency,
                         ipo_date, pe_ratio, revenue_growth, earnings_growth,
                         dividend_yield, recommendation, earnings_date, last_updated)
                    SELECT ticker, name, sector, industry, country, exchange,
                           region, market_cap, market_cap_tier, currency,
                           ipo_date, pe_ratio, revenue_growth, earnings_growth,
                           dividend_yield, recommendation, earnings_date, last_updated
                    FROM stocks_temp
                ''')
                conn.execute('DROP TABLE IF EXISTS stocks_temp')
            log.info(f"  ✓ {len(stock_rows)} stocks upserted")

        # 3b. Price history
        if all_prices:
            prices_df = pd.concat(all_prices, ignore_index=True)
            self.stats['prices_inserted'] = len(prices_df)
            with self.db.get_connection() as conn:
                prices_df.to_sql('prices_temp', conn, if_exists='replace', index=False)
                conn.execute('''
                    INSERT OR REPLACE INTO price_history
                        (ticker, date, open, high, low, close, adj_close, volume)
                    SELECT ticker, date, open, high, low, close, adj_close, volume
                    FROM prices_temp
                ''')
                conn.execute('DROP TABLE IF EXISTS prices_temp')
            log.info(f"  ✓ {len(prices_df):,} price rows upserted")

        # 3c. Gains table
        if all_gains:
            gains_df = pd.DataFrame(all_gains)
            with self.db.get_connection() as conn:
                gains_df.to_sql('gains_temp', conn, if_exists='replace', index=False)
                conn.execute('''
                    INSERT OR REPLACE INTO gains
                        (ticker, period, pct_change, abs_change,
                         start_price, end_price, start_date, end_date,
                         avg_volume, recent_volume, volume_ratio,
                         sector_avg_change, country_avg_change,
                         vs_sector, vs_country,
                         high_52w, low_52w, pct_from_52w_high, pct_from_52w_low,
                         at_52w_high, at_52w_low,
                         volatility_30d, max_drawdown, sharpe_ratio,
                         pct_change_usd,
                         rsi_14, ma_50, ma_200, above_ma_50, above_ma_200,
                         gain_streak)
                    SELECT ticker, period, pct_change, abs_change,
                           start_price, end_price, start_date, end_date,
                           avg_volume, recent_volume, volume_ratio,
                           sector_avg_change, country_avg_change,
                           vs_sector, vs_country,
                           high_52w, low_52w, pct_from_52w_high, pct_from_52w_low,
                           at_52w_high, at_52w_low,
                           volatility_30d, max_drawdown, sharpe_ratio,
                           pct_change_usd,
                           rsi_14, ma_50, ma_200, above_ma_50, above_ma_200,
                           gain_streak
                    FROM gains_temp
                ''')
                conn.execute('DROP TABLE IF EXISTS gains_temp')
            log.info(f"  ✓ {len(gains_df):,} gain rows upserted")

            # 3d. Compute sector & country averages (in-place SQL update)
            log.info("  Computing sector & country relative strength …")
            with self.db.get_connection() as conn:
                conn.execute('''
                    UPDATE gains SET
                        sector_avg_change = (
                            SELECT AVG(g2.pct_change)
                            FROM gains g2
                            JOIN stocks s2 ON g2.ticker = s2.ticker
                            WHERE g2.period = gains.period
                              AND s2.sector = (SELECT sector FROM stocks WHERE ticker = gains.ticker)
                              AND s2.sector IS NOT NULL
                        ),
                        country_avg_change = (
                            SELECT AVG(g2.pct_change)
                            FROM gains g2
                            JOIN stocks s2 ON g2.ticker = s2.ticker
                            WHERE g2.period = gains.period
                              AND s2.country = (SELECT country FROM stocks WHERE ticker = gains.ticker)
                        )
                ''')
                conn.execute('''
                    UPDATE gains SET
                        vs_sector  = pct_change - sector_avg_change,
                        vs_country = pct_change - country_avg_change
                    WHERE sector_avg_change IS NOT NULL
                       OR country_avg_change IS NOT NULL
                ''')
            log.info("  ✓ Relative strength computed")

        # 3e. Pipeline metadata
        self.db.set_meta('last_updated', datetime.now().isoformat())
        self.db.set_meta('pipeline_version', 'real_pipeline_v1')
        self.db.set_meta('tickers_count', str(self.stats['tickers_ok']))

        elapsed = time.time() - t0
        log.info("=" * 70)
        log.info(f"  Pipeline complete in {elapsed:.1f}s")
        log.info(f"  Stocks inserted : {self.stats['tickers_ok']}")
        log.info(f"  Price rows      : {self.stats['prices_inserted']:,}")
        log.info(f"  Gains computed  : {self.stats['gains_computed']:,}")
        log.info(f"  .info fetched   : {self.stats['info_fetched']}")
        log.info(f"  Failures        : {self.stats['tickers_failed']}")
        if self.stats['failures']:
            log.info(f"  Failed tickers  : {self.stats['failures'][:20]}"
                     f"{'…' if len(self.stats['failures']) > 20 else ''}")
        log.info("=" * 70)


# ═══════════════════════════════════════════════════════════════════════════════
# 4.  CLI
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description='TopGainers Real Pipeline — fetch live market data')
    parser.add_argument(
        '--exchanges', nargs='+',
        help=f"Exchange groups to process. Available: {list(TICKER_LISTS.keys())}")
    parser.add_argument(
        '--all', action='store_true',
        help='Process ALL exchange groups')
    parser.add_argument(
        '--limit', type=int, default=None,
        help='Limit total number of tickers (for testing)')
    parser.add_argument(
        '--batch-size', type=int, default=25,
        help='Tickers per yf.download batch (default 25)')
    parser.add_argument(
        '--db', type=str, default=DB_PATH,
        help=f'Path to SQLite DB (default {DB_PATH})')
    args = parser.parse_args()

    if args.all:
        groups = list(TICKER_LISTS.keys())
    elif args.exchanges:
        groups = args.exchanges
    else:
        print("Usage: python real_pipeline.py --exchanges US India")
        print(f"       Available groups: {list(TICKER_LISTS.keys())}")
        print("       Or use --all to process everything")
        sys.exit(1)

    pipeline = RealPipeline(db_path=args.db, batch_size=args.batch_size)
    pipeline.run(exchange_groups=groups, limit=args.limit)


if __name__ == '__main__':
    main()
