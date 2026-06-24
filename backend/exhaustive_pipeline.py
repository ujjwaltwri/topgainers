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
from dotenv import load_dotenv
load_dotenv()
import json
from supabase import create_client, Client
import sys
import time
import argparse
import sqlite3
from datetime import datetime, timedelta
from collections import OrderedDict
import pandas as pd
import numpy as np
import yfinance as yf
import financedatabase as fd
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
            # KOSPI Blue Chips
            '005930.KS',  # Samsung Electronics
            '000660.KS',  # SK Hynix
            '373220.KS',  # LG Energy Solution
            '005490.KS',  # POSCO Holdings
            '035420.KS',  # NAVER
            '035720.KS',  # Kakao
            '051910.KS',  # LG Chem
            '006400.KS',  # Samsung SDI
            '005380.KS',  # Hyundai Motor
            '000270.KS',  # Kia
            '068270.KS',  # Celltrion
            '105560.KS',  # KB Financial
            '055550.KS',  # Shinhan Financial
            '086790.KS',  # Hana Financial
            '015760.KS',  # Korea Electric Power (KEPCO)
            '096770.KS',  # SK Innovation
            '017670.KS',  # SK Telecom
            '030200.KS',  # KT Corp
            '032830.KS',  # Samsung Life Insurance
            '009150.KS',  # Samsung Electro-Mechanics
            '003550.KS',  # LG Corp
            '066570.KS',  # LG Electronics
            '034730.KS',  # SK Inc
            '010130.KS',  # Korea Zinc
            '329180.KS',  # HD Hyundai Heavy Industries
            '042660.KS',  # Hanwha Ocean
            '012330.KS',  # Hyundai Mobis
            '000810.KS',  # Samsung Fire & Marine
            '028260.KS',  # Samsung C&T
            '207940.KS',  # Samsung Biologics
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

    # ── Canada Venture (TSX Venture Exchange) ─────────────────────────────
    'CanadaVenture': {
        'exchange': 'TSXV',
        'country': 'Canada',
        'region': 'Americas',
        'currency': 'CAD',
        'tickers': [],
    },

    # ── Germany Frankfurt (FWB) ────────────────────────────────────────────
    'Frankfurt': {
        'exchange': 'FWB',
        'country': 'Germany',
        'region': 'Europe',
        'currency': 'EUR',
        'tickers': [],
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
        'tickers': [],
    },
    'France': { 'exchange': 'Euronext Paris', 'country': 'France', 'region': 'Europe', 'currency': 'EUR', 'tickers': [] },
    'Netherlands': { 'exchange': 'Euronext Amsterdam', 'country': 'Netherlands', 'region': 'Europe', 'currency': 'EUR', 'tickers': [] },
    'Saudi Arabia': { 'exchange': 'Tadawul', 'country': 'Saudi Arabia', 'region': 'Middle East / Africa', 'currency': 'SAR', 'tickers': [] },
    
    # --- EXPANDED ASIA-PACIFIC ---
    'Taiwan': { 'exchange': 'TWSE', 'country': 'Taiwan', 'region': 'Asia-Pacific', 'currency': 'TWD', 'tickers': [] },
    'Singapore': { 'exchange': 'SGX', 'country': 'Singapore', 'region': 'Asia-Pacific', 'currency': 'SGD', 'tickers': [] },
    'Malaysia': { 'exchange': 'KLSE', 'country': 'Malaysia', 'region': 'Asia-Pacific', 'currency': 'MYR', 'tickers': [] },
    'Indonesia': { 'exchange': 'IDX', 'country': 'Indonesia', 'region': 'Asia-Pacific', 'currency': 'IDR', 'tickers': [] },
    'Thailand': { 'exchange': 'SET', 'country': 'Thailand', 'region': 'Asia-Pacific', 'currency': 'THB', 'tickers': [] },
    'Philippines': { 'exchange': 'PSE', 'country': 'Philippines', 'region': 'Asia-Pacific', 'currency': 'PHP', 'tickers': [] },
    'New Zealand': { 'exchange': 'NZX', 'country': 'New Zealand', 'region': 'Asia-Pacific', 'currency': 'NZD', 'tickers': [] },
    
    # --- EXPANDED EUROPE ---
    'Switzerland': { 'exchange': 'SIX', 'country': 'Switzerland', 'region': 'Europe', 'currency': 'CHF', 'tickers': [] },
    'Italy': { 'exchange': 'Borsa Italiana', 'country': 'Italy', 'region': 'Europe', 'currency': 'EUR', 'tickers': [] },
    'Spain': { 'exchange': 'BME', 'country': 'Spain', 'region': 'Europe', 'currency': 'EUR', 'tickers': [] },
    'Sweden': { 'exchange': 'Nasdaq Stockholm', 'country': 'Sweden', 'region': 'Europe', 'currency': 'SEK', 'tickers': [] },
    'Norway': { 'exchange': 'Oslo Bors', 'country': 'Norway', 'region': 'Europe', 'currency': 'NOK', 'tickers': [] },
    'Denmark': { 'exchange': 'Nasdaq Copenhagen', 'country': 'Denmark', 'region': 'Europe', 'currency': 'DKK', 'tickers': [] },
    'Finland': { 'exchange': 'Nasdaq Helsinki', 'country': 'Finland', 'region': 'Europe', 'currency': 'EUR', 'tickers': [] },
    'Poland': { 'exchange': 'GPW', 'country': 'Poland', 'region': 'Europe', 'currency': 'PLN', 'tickers': [] },
    'Austria': { 'exchange': 'Wiener Börse', 'country': 'Austria', 'region': 'Europe', 'currency': 'EUR', 'tickers': [] },
    'Ireland': { 'exchange': 'Euronext Dublin', 'country': 'Ireland', 'region': 'Europe', 'currency': 'EUR', 'tickers': [] },
    'Portugal': { 'exchange': 'Euronext Lisbon', 'country': 'Portugal', 'region': 'Europe', 'currency': 'EUR', 'tickers': [] },
    'Greece': { 'exchange': 'Athens Exchange', 'country': 'Greece', 'region': 'Europe', 'currency': 'EUR', 'tickers': [] },
    
    # --- EXPANDED AMERICAS ---
    'Mexico': { 'exchange': 'BMV', 'country': 'Mexico', 'region': 'Americas', 'currency': 'MXN', 'tickers': [] },
    'Argentina': { 'exchange': 'BCBA', 'country': 'Argentina', 'region': 'Americas', 'currency': 'ARS', 'tickers': [] },
    'Chile': { 'exchange': 'BCS', 'country': 'Chile', 'region': 'Americas', 'currency': 'CLP', 'tickers': [] },
    
    # --- EXPANDED MIDDLE EAST / AFRICA ---
    'Israel': { 'exchange': 'TASE', 'country': 'Israel', 'region': 'Middle East / Africa', 'currency': 'ILS', 'tickers': [] },
    'Turkey': { 'exchange': 'Borsa Istanbul', 'country': 'Turkey', 'region': 'Middle East / Africa', 'currency': 'TRY', 'tickers': [] },
    'Egypt': { 'exchange': 'EGX', 'country': 'Egypt', 'region': 'Middle East / Africa', 'currency': 'EGP', 'tickers': [] },
    'Qatar': { 'exchange': 'QSE', 'country': 'Qatar', 'region': 'Middle East / Africa', 'currency': 'QAR', 'tickers': [] },
    'United Arab Emirates': { 'exchange': 'DFM', 'country': 'United Arab Emirates', 'region': 'Middle East / Africa', 'currency': 'AED', 'tickers': [] },
    'South Africa': { 'exchange': 'JSE', 'country': 'South Africa', 'region': 'Middle East / Africa', 'currency': 'ZAR', 'tickers': [] }
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

    def __init__(self, supabase_url: str = None, supabase_key: str = None, batch_size: int = 25):
        if not supabase_url or not supabase_key:
            supabase_url = os.getenv('SUPABASE_URL')
            supabase_key = os.getenv('SUPABASE_KEY')
        self.supabase = create_client(supabase_url, supabase_key)
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
        self.failed_file = 'failed_tickers.json'

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

    def _resolve_tickers(self, exchange_groups, limit=None):
        """Return list of dicts with ticker + metadata using master_tickers.json."""
        import json
        log.info("Loading Exhaustive Tickers from master_tickers.json...")
        try:
            with open('../data/master_tickers.json', 'r') as f:
                master_tickers = json.load(f)
        except Exception as e:
            log.error(f"Failed to load master_tickers.json: {e}. Please run discover_tickers.py first.")
            return []

        result = []
        for grp_name in exchange_groups:
            grp = TICKER_LISTS.get(grp_name)
            if grp is None:
                continue
            
            suffix = EXCHANGES.get(grp['exchange'], {}).get('suffix', '')
            key = 'US' if suffix == '' else suffix
            
            tickers_for_exchange = master_tickers.get(key, [])
            
            for ticker in tickers_for_exchange:
                result.append({
                    'ticker': ticker,
                    'name': None,
                    'sector': None,
                    'industry': None,
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
                auto_adjust=True,
                threads=False,
                progress=False,
                timeout=30,
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
    def _translate_if_foreign(self, name: str) -> str:
        if not name: return name
        import re
        if re.search(r'[^\x00-\x7F]', name):
            try:
                from deep_translator import GoogleTranslator
                translated = GoogleTranslator(source='auto', target='en').translate(name)
                if translated and "Error 500" not in translated and "That’s an error" not in translated and "There was an error" not in translated:
                    return translated
                return name
            except Exception as e:
                log.warning(f"Translation failed for {name}: {e}")
                return name
        return name

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
            raw_name = info.get('longName') or info.get('shortName')
            defaults['name'] = self._translate_if_foreign(raw_name)
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

    def _has_suspension_gap(self, period_df: pd.DataFrame, threshold_days: int = 30) -> bool:
        dates = pd.to_datetime(period_df['date']).sort_values()
        gaps = dates.diff().dropna()
        return bool((gaps > pd.Timedelta(days=threshold_days)).any())

    # ── compute all gain metrics for a single ticker ──────────────────────
    def _compute_gains(self, ticker: str, df: pd.DataFrame) -> list[dict]:
        """Compute gains for all TIME_PERIODS. Returns list of gain dicts."""
        gains = []
        
        # 0-VOLUME FILTER: Drop days where the stock did not trade
        # This prevents stale/unadjusted ghost prices from causing massive fake returns
        df = df[df['volume'] > 0].copy()
        
        if df.empty:
            return gains

        prices = df['close'].astype(float)
        volumes = df['volume'].astype(float)

        if len(prices) < 2:
            return gains

        current_price = float(prices.iloc[-1])

        # Pre-compute shared metrics
        rsi_14 = compute_rsi(prices)
        ma_50 = float(prices.rolling(50).mean().iloc[-1]) if len(prices) >= 50 else None
        ma_200 = float(prices.rolling(200).mean().iloc[-1]) if len(prices) >= 200 else None
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

        # Ensure date column is datetime for calendar slicing
        if not pd.api.types.is_datetime64_any_dtype(df['date']):
            df['date'] = pd.to_datetime(df['date'])
            
        latest_date = df['date'].max()

        for period_name, days in TIME_PERIODS:
            try:
                if period_name == 'CUSTOM':
                    continue

                if period_name == 'YTD':
                    start_of_year = f"{datetime.now().year}-01-01"
                    period_df = df[df['date'] >= start_of_year]
                elif period_name == 'MAX':
                    period_df = df
                else:
                    # Map periods to calendar time instead of trading days (to fix suspended stock bugs)
                    if period_name == '1D': delta = pd.Timedelta(days=1)
                    elif period_name == '5D': delta = pd.Timedelta(days=7)
                    elif period_name == '1M': delta = pd.DateOffset(months=1)
                    elif period_name == '3M': delta = pd.DateOffset(months=3)
                    elif period_name == '6M': delta = pd.DateOffset(months=6)
                    elif period_name == '1Y': delta = pd.DateOffset(years=1)
                    elif period_name == '2Y': delta = pd.DateOffset(years=2)
                    elif period_name == '3Y': delta = pd.DateOffset(years=3)
                    elif period_name == '5Y': delta = pd.DateOffset(years=5)
                    else: delta = pd.Timedelta(days=int(days * 1.45)) # fallback
                    
                    target_date = latest_date - delta
                    period_df = df[df['date'] >= target_date]

                if len(period_df) < 2:
                    continue

                # Sparse data check — require at least 50% of expected trading days,
                # but cap the expectation at what's actually available in the full history.
                # This prevents discarding all long-period gains for markets where
                # yfinance has limited history (e.g. KOSPI returns ~250 days max).
                available_days = len(df)
                expected_days = min(days * (5/7) * 0.85, available_days * 0.95) if days else 0
                if expected_days > 0 and len(period_df) < max(2, expected_days * 0.5):
                    log.warning(f"  [SPARSE] {ticker} {period_name}: only {len(period_df)} days, skipping.")
                    continue

                # Suspension gap check
                if self._has_suspension_gap(period_df):
                    log.warning(f"  [ANOMALY] {ticker} {period_name}: suspension gap detected. Skipping.")
                    continue

                p_prices = period_df['close'].astype(float)
                start_price = float(p_prices.iloc[0])
                end_price = float(p_prices.iloc[-1])
                start_date = period_df['date'].iloc[0].strftime('%Y-%m-%d')
                end_date = period_df['date'].iloc[-1].strftime('%Y-%m-%d')

                if start_price == 0:
                    continue

                pct_change = ((end_price / start_price) - 1.0) * 100.0

                # Thresholds by period — what's plausible in that window
                # Raised 1Y/2Y/3Y caps: legitimate multi-baggers (e.g. Samsung, NVDA)
                # were being incorrectly discarded at the old 300% limit.
                MAX_PLAUSIBLE = {
                    '1D': 25, '5D': 50, '1M': 100, '3M': 200,
                    '6M': 500, 'YTD': 1000, '1Y': 1000, '2Y': 2000,
                    '3Y': 5000, '5Y': 10000, 'MAX': 100000,
                }
                limit = MAX_PLAUSIBLE.get(period_name, 500)
                if pct_change > limit:
                    log.warning(f"  [ANOMALY] {ticker} {period_name}: {pct_change:.1f}% > {limit}% cap. Skipping.")
                    continue
                # A stock cannot lose more than 100% — anything below -100% is
                # a data artifact (currency mismatch, stale OTC price, bad tick).
                if pct_change < -100.0:
                    log.warning(f"  [ANOMALY] {ticker} {period_name}: {pct_change:.1f}% below -100% floor. Skipping.")
                    continue

                avg_vol = float(period_df['volume'].mean())
                vol_ratio = float(recent_vol / avg_vol) if avg_vol > 0 else 1.0

                drawdown = compute_max_drawdown(p_prices)
                volatility = compute_volatility(p_prices)

                gains.append({
                    'ticker': ticker,
                    'period': period_name,
                    'pct_change': round(pct_change, 4),
                    'start_price': round(start_price, 4),
                    'end_price': round(end_price, 4),
                    'start_date': start_date,
                    'end_date': end_date,
                    'avg_volume': round(avg_vol, 0),
                    'volume_ratio': round(vol_ratio, 4),
                    'high_52w': round(high_52w, 4),
                    'low_52w': round(low_52w, 4),
                    'pct_from_52w_high': round(pct_from_52w_high, 4) if pct_from_52w_high is not None else None,
                    'pct_from_52w_low': round(pct_from_52w_low, 4) if pct_from_52w_low is not None else None,
                    'at_52w_high': at_52w_high,
                    'at_52w_low': at_52w_low,
                    'volatility_30d': round(volatility, 4) if volatility is not None else None,
                    'max_drawdown': round(drawdown, 4) if drawdown is not None else None,
                    'rsi_14': round(rsi_14, 4) if rsi_14 is not None else None,
                    'ma_50': round(ma_50, 4) if ma_50 is not None else None,
                    'ma_200': round(ma_200, 4) if ma_200 is not None else None,
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
    def run(self, exchange_groups: list[str], limit: int | None = None, dry_run: bool = False, resume: bool = False):
        t0 = time.time()
        log.info("=" * 70)
        log.info("  TopGainers Exhaustive Pipeline — Starting")
        log.info("=" * 70)

        if not dry_run:
            self._fetch_fx_rates()

        # 1. Resolve tickers
        ticker_metas = self._resolve_tickers(exchange_groups, limit)
        tickers = [m['ticker'] for m in ticker_metas]
        meta_lookup = {m['ticker']: m for m in ticker_metas}
        
        # 1b. Handle Failed Tickers (with 30-day expiry)
        failed_tickers = set()
        failed_tickers_ts = {}  # ticker -> ISO timestamp of failure
        FAILED_EXPIRY_DAYS = 30
        if os.path.exists(self.failed_file):
            try:
                with open(self.failed_file, 'r') as f:
                    raw = json.load(f)
                # Support both old list format and new dict format
                if isinstance(raw, list):
                    now_ts = datetime.now().isoformat()
                    failed_tickers_ts = {t: now_ts for t in raw}
                else:
                    failed_tickers_ts = raw
                cutoff = datetime.now() - timedelta(days=FAILED_EXPIRY_DAYS)
                for t, ts in failed_tickers_ts.items():
                    try:
                        if datetime.fromisoformat(ts) > cutoff:
                            failed_tickers.add(t)
                    except Exception:
                        failed_tickers.add(t)
                log.info(f"Loaded {len(failed_tickers_ts)} failed tickers; {len(failed_tickers)} still within {FAILED_EXPIRY_DAYS}-day blacklist.")
            except Exception as e:
                log.warning(f"Could not load failed tickers: {e}")

        # 1c. Handle Resume Logic
        processed_tickers = set()
        if resume:
            log.info("Resume flag passed. Querying database for recently processed tickers...")
            try:
                yesterday = (datetime.now() - timedelta(days=1)).isoformat()
                page_size = 1000
                offset = 0
                while True:
                    response = (
                        self.supabase.table('stocks')
                        .select('ticker')
                        .gte('last_updated', yesterday)
                        .range(offset, offset + page_size - 1)
                        .execute()
                    )
                    batch = response.data or []
                    for row in batch:
                        processed_tickers.add(row['ticker'])
                    if len(batch) < page_size:
                        break
                    offset += page_size
                log.info(f"Found {len(processed_tickers)} recently processed tickers to skip.")
            except Exception as e:
                log.warning(f"Failed to query processed tickers from Supabase: {e}")

        # Filter tickers
        original_count = len(tickers)
        tickers = [t for t in tickers if t not in failed_tickers and t not in processed_tickers]
        
        if limit:
            tickers = tickers[:limit]

        self.stats['tickers_attempted'] = len(tickers)
        log.info(f"Resolved {original_count} tickers. After skipping, {len(tickers)} remain to process.")
        
        if dry_run:
            log.info("DRY RUN: Exiting before downloading.")
            return

        if not tickers:
            log.info("No tickers to process — aborting.")
            return

        # 2. Download prices in batches
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
            
            stock_rows = []
            all_prices = []
            all_gains = []
            batch_failures = []

            # 2b. For each ticker that has data, compute metrics + fetch .info
            for ticker in batch:
                if ticker not in ticker_dfs:
                    self.stats['tickers_failed'] += 1
                    batch_failures.append(ticker)
                    continue

                df = ticker_dfs[ticker]
                meta = meta_lookup[ticker]

                # DATA QUALITY FILTER: Liquidity (Ghost Stock Ban)
                avg_vol = float(df['volume'].mean()) if 'volume' in df.columns else 0
                if avg_vol < 10000:
                    log.warning(f"  [FILTER] {ticker} discarded (Avg Vol {avg_vol:.0f} < 10k)")
                    self.stats['tickers_failed'] += 1
                    batch_failures.append(ticker)
                    continue

                # Fetch .info first for Market Cap filtering
                try:
                    info = self._fetch_info(ticker)
                except Exception as e:
                    log.error(f"Failed to fetch info for {ticker}: {e}")
                    info = {
                        'name': meta.get('name', ticker), 'sector': meta.get('sector'),
                        'industry': meta.get('industry'), 'market_cap': None, 'pe_ratio': None,
                        'revenue_growth': None, 'earnings_growth': None, 'dividend_yield': None,
                        'recommendation': None, 'info_country': None, 'currency': meta['currency']
                    }

                mcap_usd = info['market_cap'] * self.fx_rates.get(info.get('currency') or meta['currency'], 1.0) if info.get('market_cap') else 0

                # DATA QUALITY FILTER: Market Cap (Microcap Ban)
                if mcap_usd < 10_000_000:
                    log.warning(f"  [FILTER] {ticker} discarded (Market Cap ${mcap_usd:,.0f} < $10M)")
                    self.stats['tickers_failed'] += 1
                    batch_failures.append(ticker)
                    continue

                try:
                    # Compute gains now that the stock is verified legitimate
                    gains = self._compute_gains(ticker, df)
                    if not gains:
                        self.stats['tickers_failed'] += 1
                        batch_failures.append(ticker)
                        continue

                    all_gains.extend(gains)
                    ok_tickers.add(ticker)
                    self.stats['tickers_ok'] += 1

                except Exception as e:
                    log.error(f"  ✗ {ticker} — metrics error: {e}")
                    self.stats['tickers_failed'] += 1
                    batch_failures.append(ticker)
                    continue
                
                # Filter out garbage yfinance names (e.g. '352770.KS,0P0001L88C,208430')
                yf_name = info['name']
                if yf_name and ',' in yf_name and ' ' not in yf_name:
                    yf_name = None
                    
                # Prefer yfinance name (real company name), then meta name, then ticker
                final_name = yf_name or meta.get('name') or ticker
                
                stock_rows.append({
                        'ticker': ticker,
                        'name': final_name,
                        'sector': info['sector'] or meta.get('sector'),
                        'industry': info['industry'] or meta.get('industry'),
                        'country': info.get('info_country') or meta['country'],
                        'exchange': meta['exchange'],
                        'region': meta['region'],
                        'market_cap': info['market_cap'] * self.fx_rates.get(info.get('currency') or meta['currency'], 1.0) if info['market_cap'] else None,
                        'market_cap_tier': get_market_cap_tier(info['market_cap'] * self.fx_rates.get(info.get('currency') or meta['currency'], 1.0) if info['market_cap'] else None) if info.get('market_cap') else None,
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
                    


            # Update failures
            if batch_failures:
                self.stats['failures'].extend(batch_failures)
                now_ts = datetime.now().isoformat()
                for t in batch_failures:
                    failed_tickers.add(t)
                    failed_tickers_ts[t] = now_ts
                with open(self.failed_file, 'w') as f:
                    json.dump(failed_tickers_ts, f)

            # ── 3. Write to Supabase (Incremental) ─────────────────────────────
            try:
                if stock_rows:
                    # Clean NaNs to None for JSON serialization
                    for row in stock_rows:
                        for k, v in row.items():
                            if pd.isna(v): row[k] = None
                    self.supabase.table('stocks').upsert(stock_rows).execute()

                # if all_prices:
                #     prices_df = pd.concat(all_prices, ignore_index=True)
                #     if 'volume' in prices_df.columns:
                #         prices_df['volume'] = pd.to_numeric(prices_df['volume'], errors='coerce').fillna(0).astype(int)
                #     # Convert dates to string, handle NaNs
                #     prices_df = prices_df.replace({np.nan: None})
                #     prices_records = prices_df.to_dict(orient='records')
                #     self.stats['prices_inserted'] += len(prices_records)
                #     
                #     # Supabase upsert has a limit of ~1000-2000 rows per request usually. 
                #     # 100 tickers * 1250 days = 125k rows. This will crash Supabase REST API!
                #     # We must chunk the prices_records.
                #     chunk_size = 2000
                #     for i in range(0, len(prices_records), chunk_size):
                #         self.supabase.table('price_history').upsert(prices_records[i:i+chunk_size]).execute()

                if all_gains:
                    gains_df = pd.DataFrame(all_gains)
                    for col in ['avg_volume']:
                        if col in gains_df.columns:
                            gains_df[col] = pd.to_numeric(gains_df[col], errors='coerce').fillna(0).astype(int)
                    gains_df = gains_df.replace({np.nan: None})
                    gains_records = gains_df.to_dict(orient='records')
                    
                    chunk_size = 2000
                    for i in range(0, len(gains_records), chunk_size):
                        self.supabase.table('gains').upsert(gains_records[i:i+chunk_size]).execute()
            except Exception as e:
                log.error(f"Supabase upsert failed for batch: {e}")

            # Adaptive Rate Limiting
            if batch_idx + self.batch_size < len(tickers):
                time.sleep(0.5)

        # 3d. Compute sector & country averages
        log.info("Computing sector & country relative strength via Supabase RPC …")
        try:
            self.supabase.rpc('compute_relative_strength').execute()
            log.info("✓ Relative strength computed")
        except Exception as e:
            log.error(f"Failed to compute relative strength (Make sure RPC exists!): {e}")

        # 3e. Pipeline metadata
        try:
            meta_rows = [
                {'key': 'last_updated', 'value': datetime.now().isoformat()},
                {'key': 'pipeline_version', 'value': 'supabase_pipeline_v1'},
                {'key': 'tickers_count', 'value': str(self.stats['tickers_ok'])}
            ]
            self.supabase.table('pipeline_meta').upsert(meta_rows).execute()
        except:
            pass

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
        '--batch-size', type=int, default=100,
        help='Tickers per yf.download batch (default 100)')
    parser.add_argument('--supabase-url', type=str, default=os.getenv('SUPABASE_URL'), help='Supabase Project URL')
    parser.add_argument('--supabase-key', type=str, default=os.getenv('SUPABASE_KEY'), help='Supabase Service Role Key')
    parser.add_argument(
        '--dry-run', action='store_true',
        help='Run without downloading anything')
    parser.add_argument(
        '--resume',
        action='store_true',
        help='Resume run by skipping already processed tickers in the DB')
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

    if not args.supabase_url or not args.supabase_key:
        print("ERROR: Supabase URL and Key are required. Pass via CLI or .env file (SUPABASE_URL, SUPABASE_KEY)")
        sys.exit(1)
        
    pipeline = RealPipeline(supabase_url=args.supabase_url, supabase_key=args.supabase_key, batch_size=args.batch_size)
    pipeline.run(exchange_groups=groups, limit=args.limit, dry_run=args.dry_run, resume=args.resume)


if __name__ == '__main__':
    main()
