import datetime
import logging
import os
from exhaustive_pipeline import RealPipeline

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)-7s | %(message)s')
logger = logging.getLogger(__name__)

# Market hours in UTC (rough approximation — good enough for scheduling)
MARKET_HOURS_UTC = {
    'US':       (13, 20, ['US']),
    'Europe':   (8,  16, ['UK', 'Germany', 'France', 'Netherlands', 'Switzerland', 'Italy', 'Spain', 'Sweden', 'Norway', 'Denmark', 'Finland', 'Poland', 'Austria']),
    'Japan':    (0,  6,  ['Japan']),
    'China':    (1,  8,  ['China', 'HongKong']),
    'India':    (3,  10, ['India']),
    'Australia':(23, 6,  ['Australia']),
    'Korea':    (0,  6,  ['Korea']),
}

# Map to actual TICKER_LISTS keys (from exhaustive_pipeline.py)
REGION_TO_GROUPS = {
    'US':          ['US'],
    'Europe':      ['UK', 'Germany', 'France', 'Netherlands', 'Switzerland', 'Italy', 'Spain',
                    'Sweden', 'Norway', 'Denmark', 'Finland', 'Poland', 'Austria', 'Ireland',
                    'Portugal', 'Greece', 'Frankfurt'],
    'Japan':       ['Japan'],
    'China':       [],  # China tickers not in master_tickers yet
    'India':       ['India'],
    'Australia':   ['Australia'],
    'Korea':       ['Korea'],
    'HongKong':    ['HongKong'],
    'Vietnam':     ['Vietnam'],
}


def get_open_market_groups():
    now_utc = datetime.datetime.utcnow()
    h = now_utc.hour
    weekday = now_utc.weekday()

    if weekday >= 5:  # Saturday=5, Sunday=6
        return []

    open_groups = []
    for region, (start, end, _) in MARKET_HOURS_UTC.items():
        if start > end:  # wraps midnight (e.g. Australia 23-06)
            is_open = h >= start or h <= end
        else:
            is_open = start <= h <= end
        if is_open:
            open_groups.extend(REGION_TO_GROUPS.get(region, []))

    return list(dict.fromkeys(open_groups))  # deduplicate, preserve order


def main():
    logger.info("Starting TopGainers Live Sweep …")

    open_groups = get_open_market_groups()
    if not open_groups:
        logger.info("All markets closed. Nothing to sweep.")
        return

    logger.info(f"Open market groups: {open_groups}")

    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_KEY')
    if not supabase_url or not supabase_key:
        logger.error("SUPABASE_URL / SUPABASE_KEY not set. Exiting.")
        return

    pipeline = RealPipeline(supabase_url=supabase_url, supabase_key=supabase_key, batch_size=50)
    pipeline.run(exchange_groups=open_groups, limit=500, resume=True)
    logger.info("Sweep complete.")


if __name__ == '__main__':
    main()
