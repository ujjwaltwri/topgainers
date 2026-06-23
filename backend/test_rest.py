import os
import requests
from dotenv import load_dotenv

load_dotenv()
url = os.environ.get("SUPABASE_URL") + "/rest/v1/gains_with_stocks?period=eq.6M&order=market_cap.desc.nullslast&limit=5"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InhwbWZ3cHFreWtpcW1zd3Vtb3h1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODIxNTEwNjYsImV4cCI6MjA5NzcyNzA2Nn0.TAFycwI-cScW88ynt9SZNkLUqskOxdO3e7PQh-zUZyk"

headers = {
    "apikey": key,
    "Authorization": f"Bearer {key}"
}
response = requests.get(url, headers=headers)
data = response.json()
print("Raw JSON text:", response.text)
for row in data:
    print(type(row.get('market_cap')), row.get('market_cap'))
