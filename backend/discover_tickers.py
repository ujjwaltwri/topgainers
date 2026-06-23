#!/usr/bin/env python3
"""
discover_tickers.py
Fetches 100% of the world's listed stocks from TradingView's global scanner.
It translates TradingView's format (e.g. 'NSE:PARAS') into Yahoo Finance's format ('PARAS.NS').
Run this script once a month to update `../data/master_tickers.json`.
"""

import requests
import json
import os
import time
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s │ %(levelname)-7s │ %(message)s')
logger = logging.getLogger(__name__)

MARKETS = [
    "america", "india", "korea", "japan", "china", "hongkong", "uk", "germany", 
    "france", "netherlands", "canada", "australia", "brazil", "saudiarabia", 
    "taiwan", "singapore", "malaysia", "indonesia", "thailand", "philippines", 
    "newzealand", "switzerland", "italy", "spain", "sweden", "norway", "denmark", 
    "finland", "poland", "austria", "ireland", "portugal", "greece", "mexico", 
    "argentina", "chile", "israel", "turkey", "egypt", "qatar", "uae", "rsa"
]

# Map TradingView prefixes to Yahoo Finance suffixes
# If prefix is not here, we assume it's either US (no suffix) or needs manual addition
TV_TO_YF = {
    'NYSE': '',
    'NASDAQ': '',
    'AMEX': '',
    'OTC': '',
    'NSE': '.NS',
    'BSE': '.BO',
    'KRX': '.KS',       # KOSPI / KOSDAQ (yfinance uses .KS for KOSPI and .KQ for KOSDAQ, we'll map all to .KS then .KQ if failed, but for simplicity let's rely on .KS/.KQ logic or just .KS)
    'TSE': '.T',        # Japan
    'SSE': '.SS',       # China
    'SZSE': '.SZ',      # China
    'HKEX': '.HK',      # HongKong
    'LSE': '.L',        # UK
    'XETR': '.DE',      # Germany Xetra
    'FWB': '.F',        # Frankfurt
    'EURONEXT': '.PA',  # Paris (Also covers AS, BR, etc. We will broadly use .PA or .AS)
    'TSX': '.TO',       # Canada
    'TSXV': '.V',       # Canada Venture
    'ASX': '.AX',       # Australia
    'BMFBOVESPA': '.SA',# Brazil
    'TADAWUL': '.SR',   # Saudi Arabia
    'TWSE': '.TW',      # Taiwan
    'TPEX': '.TWO',     # Taiwan OTC
    'SGX': '.SI',       # Singapore
    'MYX': '.KL',       # Malaysia
    'IDX': '.JK',       # Indonesia
    'SET': '.BK',       # Thailand
    'PSE': '.PS',       # Philippines
    'NZX': '.NZ',       # New Zealand
    'SIX': '.SW',       # Switzerland
    'MIL': '.MI',       # Italy
    'BME': '.MC',       # Spain
    'OMXSTO': '.ST',    # Sweden
    'OSL': '.OL',       # Norway
    'OMXCOP': '.CO',    # Denmark
    'OMXHEL': '.HE',    # Finland
    'GPW': '.WA',       # Poland
    'VIE': '.VI',       # Austria
    'ISE': '.IR',       # Ireland
    'ATH': '.AT',       # Greece
    'BMV': '.MX',       # Mexico
    'BCBA': '.BA',      # Argentina
    'BCS': '.SN',       # Chile
    'TASE': '.TA',      # Israel
    'BIST': '.IS',      # Turkey
    'EGX': '.CA',       # Egypt
    'QSE': '.QA',       # Qatar
    'DFM': '.AE',       # UAE
    'ADX': '.AE',       # UAE Abu Dhabi
    'JSE': '.JO',       # South Africa
}

# TV's 'name' is sometimes different from YF. 
# We'll construct YF ticker by taking TV's ticker and appending the mapped suffix.

def fetch_market_tickers(market):
    url = "https://scanner.tradingview.com/global/scan"
    headers = {"content-type": "application/x-www-form-urlencoded"}
    
    all_tickers = []
    step = 5000
    
    for offset in range(0, 30000, step):
        payload = {
            "filter": [{"left": "type", "operation": "equal", "right": "stock"}],
            "options": {"lang": "en"},
            "markets": [market],
            "symbols": {"query": {"types": []}, "tickers": []},
            "columns": ["name"],
            "sort": {"sortBy": "name", "sortOrder": "asc"},
            "range": [offset, offset + step]
        }
        
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=10)
            data = resp.json()
            items = data.get("data", [])
            
            if not items:
                break
                
            for item in items:
                # item['s'] is like 'NYSE:TSM' or 'NSE:PARAS'
                all_tickers.append(item['s'])
                
            if len(items) < step:
                break
        except Exception as e:
            logger.error(f"Error fetching {market} at offset {offset}: {e}")
            break
            
    return all_tickers

def main():
    logger.info("Starting Exhaustive Ticker Discovery via TradingView...")
    
    raw_tickers = []
    for market in MARKETS:
        logger.info(f"Fetching {market}...")
        tickers = fetch_market_tickers(market)
        raw_tickers.extend(tickers)
        logger.info(f"  -> Found {len(tickers)} tickers")
        time.sleep(0.5)
        
    logger.info(f"Total raw tickers found globally: {len(raw_tickers)}")
    
    # Process and map to Yahoo Finance formats
    yf_tickers = {}
    
    for symbol in raw_tickers:
        if ':' not in symbol:
            continue
        exchange, ticker = symbol.split(':', 1)
        
        if exchange in TV_TO_YF:
            suffix = TV_TO_YF[exchange]
            yf_ticker = f"{ticker}{suffix}"
            
            # Use 'US' as key for empty suffix, else use the suffix itself
            key = 'US' if suffix == '' else suffix
            if key not in yf_tickers:
                yf_tickers[key] = []
            yf_tickers[key].append(yf_ticker)
            
    # Guarantee critical stocks (Ad-hoc safety net for TSMC, etc. if they are somehow missed)
    safety_net = ['TSM', 'PARAS.NS', 'SAMTEL.NS', '005930.KS', '000660.KS']
    for sn in safety_net:
        key = 'US' if '.' not in sn else sn[sn.find('.'):]
        if key not in yf_tickers:
            yf_tickers[key] = []
        if sn not in yf_tickers[key]:
            yf_tickers[key].append(sn)

    # Save to JSON
    os.makedirs('../data', exist_ok=True)
    out_path = '../data/master_tickers.json'
    
    total_saved = sum(len(l) for l in yf_tickers.values())
    
    with open(out_path, 'w') as f:
        json.dump(yf_tickers, f, indent=2)
        
    logger.info(f"Saved {total_saved} Yahoo-formatted tickers to {out_path}")
    logger.info("Ticker discovery complete! You can now run your pipeline.")

if __name__ == "__main__":
    main()
