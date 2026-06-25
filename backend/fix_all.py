"""
Combined one-time repair: re-fetch name + raw marketCap from yfinance for all non-USD stocks,
plus bad-named USD stocks. Stores marketCap as-is from yfinance (native currency, no FX math).
The frontend's toUSD() handles display conversion.

Run from backend/:
    python fix_all.py
"""

import os
import re
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
import yfinance as yf
from supabase import create_client

try:
    from deep_translator import GoogleTranslator
    HAS_TRANSLATOR = True
except ImportError:
    HAS_TRANSLATOR = False

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)-7s | %(message)s')
log = logging.getLogger(__name__)

WORKERS = 50
UPSERT_CHUNK = 500

MCAP_TIERS = {
    'mega':  (200e9, float('inf')),
    'large': (10e9, 200e9),
    'mid':   (2e9, 10e9),
    'small': (300e6, 2e9),
    'micro': (50e6, 300e6),
    'nano':  (0, 50e6),
}

# Approximate USD conversion just for tier bucketing (doesn't need to be perfect)
USD_RATES = {
    'KRW': 1380, 'JPY': 157, 'INR': 83, 'CNY': 7.25, 'HKD': 7.83,
    'GBP': 0.79, 'EUR': 0.92, 'CAD': 1.36, 'AUD': 1.53, 'BRL': 5.0,
    'TWD': 32, 'SGD': 1.34, 'MYR': 4.7, 'IDR': 16000, 'THB': 35,
    'PHP': 56, 'NZD': 1.63, 'CHF': 0.89, 'SEK': 10.4, 'NOK': 10.5,
    'DKK': 6.9, 'PLN': 3.9, 'MXN': 17, 'ARS': 900, 'CLP': 950,
    'ILS': 3.7, 'TRY': 32, 'EGP': 48, 'QAR': 3.64, 'AED': 3.67,
    'ZAR': 18.5, 'SAR': 3.75,
}

def get_tier(mcap_native, currency):
    if not mcap_native:
        return None
    rate = USD_RATES.get(currency, 1)
    mcap_usd = mcap_native / rate
    for tier, (lo, hi) in MCAP_TIERS.items():
        if lo <= mcap_usd < hi:
            return tier
    return None

def looks_like_ticker(name):
    if not name:
        return True
    return bool(re.match(r'^[A-Z0-9.\-]+$', name)) and ' ' not in name

def translate_if_foreign(name):
    if not name:
        return name
    if re.search(r'[^\x00-\x7F]', name) and HAS_TRANSLATOR:
        try:
            translated = GoogleTranslator(source='auto', target='en').translate(name)
            if translated and 'Error 500' not in translated:
                return translated
        except Exception:
            pass
    return name

def fetch_stock(row):
    ticker = row['ticker']
    try:
        info = yf.Ticker(ticker).info
        if not info or not isinstance(info, dict):
            return None

        long_name = info.get('longName')
        short_name = info.get('shortName')
        if short_name and looks_like_ticker(short_name):
            short_name = None
        raw_name = long_name or short_name

        # Filter out garbage comma-separated yfinance names
        if raw_name and ',' in raw_name and ' ' not in raw_name:
            raw_name = None

        name = translate_if_foreign(raw_name)
        mcap = info.get('marketCap')  # raw from yfinance, native currency

        update = {'ticker': ticker}
        if name and not looks_like_ticker(name):
            update['name'] = name
        if mcap:
            update['market_cap'] = mcap
            update['market_cap_tier'] = get_tier(mcap, row['currency'])

        return update if len(update) > 1 else None
    except Exception as e:
        log.warning(f'{ticker}: fetch failed — {e}')
        return None

def fetch_all_pages(sb, select, filters=None):
    rows = []
    offset, chunk = 0, 1000
    while True:
        q = sb.table('stocks').select(select)
        if filters:
            q = filters(q)
        r = q.range(offset, offset + chunk - 1).execute()
        batch = r.data
        if not batch:
            break
        rows += batch
        offset += chunk
        if len(batch) < chunk:
            break
    return rows

def main():
    sb = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))

    log.info('Fetching stocks to repair from Supabase...')

    # All non-USD stocks (need market cap re-fetch regardless of name)
    non_usd = fetch_all_pages(sb, 'ticker, name, currency',
                              lambda q: q.neq('currency', 'USD'))

    # USD stocks with bad names
    usd_bad = [r for r in fetch_all_pages(sb, 'ticker, name, currency',
                                           lambda q: q.eq('currency', 'USD'))
               if looks_like_ticker(r['name'])]

    targets = {r['ticker']: r for r in non_usd}
    for r in usd_bad:
        targets[r['ticker']] = r

    log.info(f'Targeting {len(targets)} stocks ({len(non_usd)} non-USD + {len(usd_bad)} USD with bad names)')
    log.info('Fetching from yfinance...')

    updates = []
    done = 0
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futures = {ex.submit(fetch_stock, row): row['ticker'] for row in targets.values()}
        for fut in as_completed(futures):
            result = fut.result()
            done += 1
            if done % 1000 == 0:
                log.info(f'  {done}/{len(targets)} fetched...')
            if result:
                updates.append(result)

    log.info(f'Upserting {len(updates)} rows...')
    for i in range(0, len(updates), UPSERT_CHUNK):
        chunk = updates[i:i + UPSERT_CHUNK]
        sb.table('stocks').upsert(chunk).execute()
        log.info(f'  Upserted {i + 1}–{min(i + UPSERT_CHUNK, len(updates))}')

    log.info('Done.')
    log.info('Spot check:')
    for t in ['005930.KS', '000660.KS', '7203.T', 'RELIANCE.NS', 'TSLA']:
        r = sb.table('stocks').select('ticker, name, currency, market_cap, market_cap_tier').eq('ticker', t).execute()
        if r.data:
            d = r.data[0]
            mcap_usd = d['market_cap'] / USD_RATES.get(d['currency'], 1) if d['market_cap'] else None
            log.info(f"  {d['ticker']} | {d['name']} | {d['currency']} {d['market_cap']:,.0f} | ~${mcap_usd/1e9:.1f}B USD | {d['market_cap_tier']}")

if __name__ == '__main__':
    main()
