"""
One-time repair: re-fetch names from yfinance for all stocks whose stored name
looks like a raw ticker symbol (no spaces, all caps/digits).

Run from the backend/ directory:
    python fix_names.py

Uses threading for speed — fetches ~16k names in batches of 50 threads.
"""

import os
import re
import time
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


def fetch_name(ticker):
    try:
        info = yf.Ticker(ticker).info
        if not info or not isinstance(info, dict):
            return ticker, None
        long_name = info.get('longName')
        short_name = info.get('shortName')
        if short_name and looks_like_ticker(short_name):
            short_name = None
        raw = long_name or short_name
        return ticker, translate_if_foreign(raw)
    except Exception as e:
        log.warning(f'{ticker}: fetch failed — {e}')
        return ticker, None


def main():
    sb = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))

    log.info('Fetching all stocks from Supabase...')
    bad = []
    offset, chunk = 0, 1000
    while True:
        r = sb.table('stocks').select('ticker, name').range(offset, offset + chunk - 1).execute()
        batch = r.data
        if not batch:
            break
        bad += [x['ticker'] for x in batch if looks_like_ticker(x['name'])]
        offset += chunk
        if len(batch) < chunk:
            break

    log.info(f'Found {len(bad)} stocks with bad names. Fetching from yfinance...')

    updates = []
    done = 0
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futures = {ex.submit(fetch_name, t): t for t in bad}
        for fut in as_completed(futures):
            ticker, name = fut.result()
            done += 1
            if done % 500 == 0:
                log.info(f'  {done}/{len(bad)} fetched...')
            if name and not looks_like_ticker(name):
                updates.append({'ticker': ticker, 'name': name})

    log.info(f'Got good names for {len(updates)}/{len(bad)} stocks. Upserting...')
    for i in range(0, len(updates), UPSERT_CHUNK):
        chunk_data = updates[i:i + UPSERT_CHUNK]
        sb.table('stocks').upsert(chunk_data).execute()
        log.info(f'  Upserted rows {i + 1}–{min(i + UPSERT_CHUNK, len(updates))}')

    still_bad = len(bad) - len(updates)
    log.info(f'Done. {len(updates)} names fixed, {still_bad} could not be resolved (yfinance returned nothing).')

    log.info('Spot check:')
    for t in ['005930.KS', '000660.KS', '7203.T', 'RELIANCE.NS']:
        r = sb.table('stocks').select('ticker, name').eq('ticker', t).execute()
        if r.data:
            log.info(f'  {r.data[0]}')


if __name__ == '__main__':
    main()
