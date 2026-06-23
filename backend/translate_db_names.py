import os
import re
from supabase import create_client
from deep_translator import GoogleTranslator

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

if not url or not key:
    from dotenv import load_dotenv
    load_dotenv()
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")

supabase = create_client(url, key)

print("Fetching all stocks to find foreign names...")
all_stocks = []
page = 0
while True:
    res = supabase.table('stocks').select('ticker, name').range(page*1000, (page+1)*1000-1).execute()
    if not res.data:
        break
    all_stocks.extend(res.data)
    page += 1

print(f"Total stocks in DB: {len(all_stocks)}")

translator = GoogleTranslator(source='auto', target='en')
updates = []

for r in all_stocks:
    name = r.get('name')
    if not name:
        continue
    
    # If the name contains non-ASCII characters (like Korean, Chinese, Arabic, Cyrillic)
    if re.search(r'[^\x00-\x7F]', name):
        try:
            english_name = translator.translate(name)
            if english_name and english_name != name:
                print(f"Translated: {name} -> {english_name}")
                updates.append({'ticker': r['ticker'], 'name': english_name})
        except Exception as e:
            print(f"Failed to translate {name}: {e}")

if updates:
    print(f"Updating {len(updates)} translated names in Supabase...")
    chunk_size = 500
    for i in range(0, len(updates), chunk_size):
        chunk = updates[i:i+chunk_size]
        supabase.table('stocks').upsert(chunk).execute()
    print("Success!")
else:
    print("No foreign names found to update.")
