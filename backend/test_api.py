import urllib.request
import json

url = "http://localhost:5000/api/top-movers?direction=gainers&period=6M&sort=pct_change&limit=25&page=1"
try:
    req = urllib.request.urlopen(url)
    data = json.loads(req.read())
    print("API Response keys:", data.keys())
    print("Number of results:", len(data.get('results', [])))
    if data.get('results'):
        print("First result ticker:", data['results'][0]['ticker'])
except Exception as e:
    print("Error:", e)
