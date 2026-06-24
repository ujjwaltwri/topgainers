"""
Backfill company names for stocks where name == ticker (yfinance returned nothing useful).
Runs in batches, rate-limited, safe to re-run.
"""
import os, time
import yfinance as yf
from supabase import create_client

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
if not url or not key:
    from dotenv import load_dotenv
    load_dotenv()
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")

supabase = create_client(url, key)

print("Fetching stocks where name == ticker or name contains commas (garbage)...")

# Fetch ALL stocks — we'll filter in Python
res = supabase.table('stocks').select('ticker, name').execute()
all_stocks = res.data
print(f"Total stocks in DB: {len(all_stocks)}")

# Identify those that need fixing:
# 1. name == ticker  (no real name fetched)
# 2. name contains a comma but no space (garbage yfinance format like "352770.KS,0P0001L88C,208430")
def needs_fix(row):
    name = row.get('name') or ''
    ticker = row['ticker']
    if name == ticker:
        return True
    if ',' in name and ' ' not in name:
        return True
    return False

bad = [r for r in all_stocks if needs_fix(r)]
print(f"Stocks needing name fix: {len(bad)}")

if not bad:
    print("Nothing to fix.")
    exit(0)

updates = []
failed = []

consecutive_failures = 0

for i, row in enumerate(bad):
    ticker = row['ticker']
    raw_name = None

    for attempt in range(3):
        try:
            info = yf.Ticker(ticker).info
            raw_name = info.get('longName') or info.get('shortName') or ''
            consecutive_failures = 0
            break
        except Exception as e:
            msg = str(e)
            if 'Too Many Requests' in msg or 'Rate limited' in msg:
                consecutive_failures += 1
                # If we keep hitting rate limits, do a long cooldown
                if consecutive_failures >= 3:
                    print(f"  Sustained rate limit hit — cooling down 5 minutes...")
                    time.sleep(300)
                    consecutive_failures = 0
                else:
                    wait = 30 * (attempt + 1)
                    print(f"  [{i+1}/{len(bad)}] {ticker}: rate limited, waiting {wait}s...")
                    time.sleep(wait)
            else:
                print(f"  [{i+1}/{len(bad)}] {ticker}: ERROR {e}")
                failed.append(ticker)
                break

    if raw_name is None:
        continue

    # Skip if yfinance still returns nothing or returns the ticker
    if not raw_name or raw_name == ticker:
        print(f"  [{i+1}/{len(bad)}] {ticker}: no name from yfinance, skipping")
        continue
    # Skip garbage comma-format names
    if ',' in raw_name and ' ' not in raw_name:
        print(f"  [{i+1}/{len(bad)}] {ticker}: garbage name '{raw_name}', skipping")
        continue
    print(f"  [{i+1}/{len(bad)}] {ticker} -> {raw_name}")
    updates.append({'ticker': ticker, 'name': raw_name})

    # 2 seconds between requests — slow enough to avoid rate limits
    time.sleep(2)

print(f"\nResolved {len(updates)} names, {len(failed)} errors.")

if updates:
    print("Upserting to Supabase...")
    for i in range(0, len(updates), 500):
        chunk = updates[i:i+500]
        supabase.table('stocks').upsert(chunk).execute()
        print(f"  Upserted {i + len(chunk)}/{len(updates)}")
    print("Done.")

if failed:
    print(f"Failed tickers: {failed}")
