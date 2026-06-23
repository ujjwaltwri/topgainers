import os
from supabase import create_client
from pykrx import stock
from googletrans import Translator
import time

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

supabase = create_client(url, key)

print("Fetching all South Korean stocks with fallback ticker names...")
res = supabase.table('stocks').select('ticker, name').eq('country', 'South Korea').execute()
stocks = res.data

# Find stocks where name exactly equals ticker (the ones we patched previously)
bad_stocks = [s for s in stocks if s['name'] == s['ticker']]
print(f"Found {len(bad_stocks)} Korean stocks missing real names.")

translator = Translator()
updates = []

for i, s in enumerate(bad_stocks):
    t = s['ticker']
    base = t.split('.')[0]
    kr_name = stock.get_market_ticker_name(base)
    
    if kr_name:
        try:
            # Translate Korean name to English
            eng_name = translator.translate(kr_name, src='ko', dest='en').text
            if eng_name:
                updates.append({'ticker': t, 'name': eng_name})
                print(f"[{i+1}/{len(bad_stocks)}] {t} -> {kr_name} -> {eng_name}")
            else:
                updates.append({'ticker': t, 'name': kr_name})
                print(f"[{i+1}/{len(bad_stocks)}] {t} -> {kr_name} (Translation failed)")
        except Exception as e:
            updates.append({'ticker': t, 'name': kr_name})
            print(f"[{i+1}/{len(bad_stocks)}] {t} -> {kr_name} (Translation Error: {e})")
            # recreate translator to avoid ban
            translator = Translator()
            time.sleep(1)

if updates:
    print(f"Updating {len(updates)} names...")
    # Chunk updates
    chunk_size = 100
    for i in range(0, len(updates), chunk_size):
        chunk = updates[i:i+chunk_size]
        supabase.table('stocks').upsert(chunk).execute()
    print("Done!")
else:
    print("No updates needed.")
