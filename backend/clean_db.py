import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

print("Deleting all gains...")
supabase.table("gains").delete().neq("ticker", "NULL").execute()

print("Deleting all stocks...")
supabase.table("stocks").delete().neq("ticker", "NULL").execute()

print("Database cleared. Ready for fresh pipeline run.")
