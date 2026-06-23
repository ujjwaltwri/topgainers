import time
import datetime
import logging
from database import Database
from exhaustive_pipeline import DataPipeline
import config
from supabase import create_client

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)-7s | %(message)s')
logger = logging.getLogger(__name__)

SUPABASE_URL = "https://xpmfwpqkykiqmswumoxu.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." # Replace with service role key if needed. We'll use the anon key for now or rely on the pipeline pushing.
# Wait, the exhaustive pipeline actually uses environment variables for Supabase. Let's rely on the environment variables just like the main pipeline.

def get_open_markets():
    """Determine which markets are currently open based on UTC time."""
    now_utc = datetime.datetime.utcnow()
    current_hour_utc = now_utc.hour
    current_day = now_utc.weekday()

    open_exchanges = []

    # Weekends (Saturday=5, Sunday=6) - No markets are open
    if current_day >= 5:
        return []

    # Extremely rough market hours approximation (UTC):
    # US (NYSE/NASDAQ): 13:30 - 20:00 UTC
    if 13 <= current_hour_utc <= 20:
        open_exchanges.extend(["NYSE", "NASDAQ", "TSX", "B3"])

    # Europe (LSE, XETRA, Paris, Amsterdam): 08:00 - 16:30 UTC
    if 8 <= current_hour_utc <= 16:
        open_exchanges.extend(["LSE", "XETRA", "Euronext Paris", "Euronext Amsterdam"])

    # Asia (TSE, KOSPI, KOSDAQ): 00:00 - 06:00 UTC
    if 0 <= current_hour_utc <= 6:
        open_exchanges.extend(["TSE", "KOSPI", "KOSDAQ"])

    # China/HK (SSE, SZSE, HKEX): 01:30 - 08:00 UTC
    if 1 <= current_hour_utc <= 8:
        open_exchanges.extend(["SSE", "SZSE", "HKEX"])

    # India (NSE, BSE): 03:45 - 10:00 UTC
    if 3 <= current_hour_utc <= 10:
        open_exchanges.extend(["NSE", "BSE"])

    # Australia (ASX): 23:00 (prev day) - 06:00 UTC
    if current_hour_utc >= 23 or current_hour_utc <= 6:
        open_exchanges.extend(["ASX"])

    return open_exchanges

def main():
    logger.info("Starting Global Radar Sweep (GitHub Actions)...")
    pipeline = DataPipeline(db_path="../data/stocks.db", min_mcap=50_000_000)

    open_exchanges = get_open_markets()
    
    if not open_exchanges:
        logger.info("All global markets are currently closed (Weekend or after-hours). Exiting sweep.")
        return

    logger.info(f"Open markets detected: {open_exchanges}")
    
    try:
        # We run a "fast update" for only the open exchanges
        logger.info("Running fast hydration sweep on open markets...")
        pipeline.run_full(exchanges=open_exchanges, limit=1000)
        logger.info("Sweep complete. Rankings updated.")
    except Exception as e:
        logger.error(f"Sweep failed: {e}")

if __name__ == "__main__":
    main()
