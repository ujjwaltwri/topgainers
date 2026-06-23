import requests
import re

def get_name(ticker):
    url = f"https://finance.yahoo.com/quote/{ticker}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        match = re.search(r'<title>(.*?) \(' + re.escape(ticker) + r'\)', res.text)
        if match:
            return match.group(1)
        # fallback
        match2 = re.search(r'<title>(.*?)</title>', res.text)
        if match2:
            return match2.group(1)
    return None

print("352770.KS:", get_name("352770.KS"))
print("080220.KS:", get_name("080220.KS"))
