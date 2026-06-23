import os, re
from dotenv import load_dotenv
from supabase import create_client
from deep_translator import GoogleTranslator

load_dotenv()
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

print("Fetching 1000 stocks...")
res = supabase.table('stocks').select('ticker, name').limit(1000).execute()
stocks = res.data

foreign = [r for r in stocks if r.get('name') and re.search(r'[^\x00-\x7F]', r['name'])]
print(f"Found {len(foreign)} foreign names.")
for r in foreign[:5]:
    try:
        translated = GoogleTranslator(source='auto', target='en').translate(r['name'])
        print(f"{r['name']} -> {translated}")
    except Exception as e:
        print(e)
