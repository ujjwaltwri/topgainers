import requests

def test_search(query):
    url = f"https://query2.finance.yahoo.com/v1/finance/search?q={query}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        data = res.json()
        quotes = data.get('quotes', [])
        if quotes:
            print(f"Results for {query}:")
            for q in quotes[:2]:
                print(f" - {q.get('symbol')}: {q.get('shortname')} | {q.get('longname')}")
        else:
            print(f"No results for {query}")
    else:
        print(f"Failed with {res.status_code}")

test_search("352770.KS")
test_search("080220.KS")
test_search("126640.KS")
