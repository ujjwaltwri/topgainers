from collections import OrderedDict

# Maps exchange name to {suffix, country, region, currency, benchmark_index}
EXCHANGES = {
    'NYSE': {'suffix': '', 'country': 'United States', 'region': 'Americas', 'currency': 'USD', 'benchmark_index': '^GSPC'},
    'NASDAQ': {'suffix': '', 'country': 'United States', 'region': 'Americas', 'currency': 'USD', 'benchmark_index': '^GSPC'},
    'NSE': {'suffix': '.NS', 'country': 'India', 'region': 'Asia-Pacific', 'currency': 'INR', 'benchmark_index': '^NSEI'},
    'BSE': {'suffix': '.BO', 'country': 'India', 'region': 'Asia-Pacific', 'currency': 'INR', 'benchmark_index': '^BSESN'},
    'KOSPI': {'suffix': '.KS', 'country': 'South Korea', 'region': 'Asia-Pacific', 'currency': 'KRW', 'benchmark_index': '^KS11'},
    'KOSDAQ': {'suffix': '.KQ', 'country': 'South Korea', 'region': 'Asia-Pacific', 'currency': 'KRW', 'benchmark_index': '^KQ11'},
    'TSE': {'suffix': '.T', 'country': 'Japan', 'region': 'Asia-Pacific', 'currency': 'JPY', 'benchmark_index': '^N225'},
    'SSE': {'suffix': '.SS', 'country': 'China', 'region': 'Asia-Pacific', 'currency': 'CNY', 'benchmark_index': '000001.SS'},
    'SZSE': {'suffix': '.SZ', 'country': 'China', 'region': 'Asia-Pacific', 'currency': 'CNY', 'benchmark_index': '399001.SZ'},
    'HKEX': {'suffix': '.HK', 'country': 'Hong Kong', 'region': 'Asia-Pacific', 'currency': 'HKD', 'benchmark_index': '^HSI'},
    'LSE': {'suffix': '.L', 'country': 'United Kingdom', 'region': 'Europe', 'currency': 'GBP', 'benchmark_index': '^FTSE'},
    'XETRA': {'suffix': '.DE', 'country': 'Germany', 'region': 'Europe', 'currency': 'EUR', 'benchmark_index': '^GDAXI'},
    'Euronext Paris': {'suffix': '.PA', 'country': 'France', 'region': 'Europe', 'currency': 'EUR', 'benchmark_index': '^FCHI'},
    'Euronext Amsterdam': {'suffix': '.AS', 'country': 'Netherlands', 'region': 'Europe', 'currency': 'EUR', 'benchmark_index': '^AEX'},
    'TSX': {'suffix': '.TO', 'country': 'Canada', 'region': 'Americas', 'currency': 'CAD', 'benchmark_index': '^GSPTSE'},
    'ASX': {'suffix': '.AX', 'country': 'Australia', 'region': 'Asia-Pacific', 'currency': 'AUD', 'benchmark_index': '^AXJO'},
    'B3': {'suffix': '.SA', 'country': 'Brazil', 'region': 'Americas', 'currency': 'BRL', 'benchmark_index': '^BVSP'},
    'Tadawul': {'suffix': '.SR', 'country': 'Saudi Arabia', 'region': 'Middle East', 'currency': 'SAR', 'benchmark_index': None}
}

REGIONS = {
    'Americas': ['United States', 'Canada', 'Brazil'],
    'Europe': ['United Kingdom', 'Germany', 'France', 'Netherlands'],
    'Asia-Pacific': ['India', 'Japan', 'South Korea', 'China', 'Hong Kong', 'Australia'],
    'Middle East': ['Saudi Arabia']
}

TIME_PERIODS = [
    ('1D', 1), ('5D', 5), ('1M', 21), ('3M', 63), ('6M', 126),
    ('1Y', 252), ('2Y', 504), ('3Y', 756), ('5Y', 1260),
    ('YTD', None), ('MAX', None), ('CUSTOM', None)
]

MCAP_TIERS = OrderedDict([
    ('mega', (200e9, float('inf'))),
    ('large', (10e9, 200e9)),
    ('mid', (2e9, 10e9)),
    ('small', (300e6, 2e9)),
    ('micro', (50e6, 300e6)),
    ('nano', (0, 50e6))
])

GICS_SECTORS = [
    'Energy', 'Materials', 'Industrials', 'Consumer Discretionary', 
    'Consumer Staples', 'Health Care', 'Financials', 'Information Technology', 
    'Communication Services', 'Utilities', 'Real Estate'
]

FX_PAIRS = {
    'INR': 'INRUSD=X',
    'KRW': 'KRWUSD=X',
    'JPY': 'JPYUSD=X',
    'CNY': 'CNYUSD=X',
    'HKD': 'HKDUSD=X',
    'GBP': 'GBPUSD=X',
    'EUR': 'EURUSD=X',
    'CAD': 'CADUSD=X',
    'AUD': 'AUDUSD=X',
    'BRL': 'BRLUSD=X',
    'SAR': 'SARUSD=X'
}

DB_PATH = '../data/stocks.db'
DEFAULT_LIMIT = 25
DEFAULT_PERIOD = '6M'
VOLUME_SURGE_THRESHOLD = 3.0
W52_THRESHOLD = 0.02
