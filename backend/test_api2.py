import urllib.request
import urllib.error

url = "http://localhost:5000/api/top-movers?direction=gainers&period=6M&sort=pct_change&limit=25&page=1"
try:
    req = urllib.request.urlopen(url)
    print(req.read().decode())
except urllib.error.HTTPError as e:
    print("Error code:", e.code)
    print("Response body:", e.read().decode())
