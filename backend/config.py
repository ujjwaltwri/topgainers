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
    'Tadawul': {'suffix': '.SR', 'country': 'Saudi Arabia', 'region': 'Middle East / Africa', 'currency': 'SAR', 'benchmark_index': None},
    # --- EXPANDED ASIA-PACIFIC ---
    'TWSE': {'suffix': '.TW', 'country': 'Taiwan', 'region': 'Asia-Pacific', 'currency': 'TWD', 'benchmark_index': '^TWII'},
    'Taipei Exchange': {'suffix': '.TWO', 'country': 'Taiwan', 'region': 'Asia-Pacific', 'currency': 'TWD', 'benchmark_index': None},
    'SGX': {'suffix': '.SI', 'country': 'Singapore', 'region': 'Asia-Pacific', 'currency': 'SGD', 'benchmark_index': '^STI'},
    'KLSE': {'suffix': '.KL', 'country': 'Malaysia', 'region': 'Asia-Pacific', 'currency': 'MYR', 'benchmark_index': '^KLSE'},
    'IDX': {'suffix': '.JK', 'country': 'Indonesia', 'region': 'Asia-Pacific', 'currency': 'IDR', 'benchmark_index': '^JKSE'},
    'SET': {'suffix': '.BK', 'country': 'Thailand', 'region': 'Asia-Pacific', 'currency': 'THB', 'benchmark_index': '^SET.BK'},
    'PSE': {'suffix': '.PS', 'country': 'Philippines', 'region': 'Asia-Pacific', 'currency': 'PHP', 'benchmark_index': 'PSEI.PS'},
    'NZX': {'suffix': '.NZ', 'country': 'New Zealand', 'region': 'Asia-Pacific', 'currency': 'NZD', 'benchmark_index': '^NZ50'},
    # --- EXPANDED EUROPE ---
    'SIX': {'suffix': '.SW', 'country': 'Switzerland', 'region': 'Europe', 'currency': 'CHF', 'benchmark_index': '^SSMI'},
    'Borsa Italiana': {'suffix': '.MI', 'country': 'Italy', 'region': 'Europe', 'currency': 'EUR', 'benchmark_index': 'FTSEMIB.MI'},
    'BME': {'suffix': '.MC', 'country': 'Spain', 'region': 'Europe', 'currency': 'EUR', 'benchmark_index': '^IBEX'},
    'Nasdaq Stockholm': {'suffix': '.ST', 'country': 'Sweden', 'region': 'Europe', 'currency': 'SEK', 'benchmark_index': '^OMX'},
    'Oslo Bors': {'suffix': '.OL', 'country': 'Norway', 'region': 'Europe', 'currency': 'NOK', 'benchmark_index': '^OSEAX'},
    'Nasdaq Copenhagen': {'suffix': '.CO', 'country': 'Denmark', 'region': 'Europe', 'currency': 'DKK', 'benchmark_index': '^OMXC20'},
    'Nasdaq Helsinki': {'suffix': '.HE', 'country': 'Finland', 'region': 'Europe', 'currency': 'EUR', 'benchmark_index': '^OMXH25'},
    'GPW': {'suffix': '.WA', 'country': 'Poland', 'region': 'Europe', 'currency': 'PLN', 'benchmark_index': '^WIG'},
    'Wiener Börse': {'suffix': '.VI', 'country': 'Austria', 'region': 'Europe', 'currency': 'EUR', 'benchmark_index': '^ATX'},
    'Euronext Dublin': {'suffix': '.IR', 'country': 'Ireland', 'region': 'Europe', 'currency': 'EUR', 'benchmark_index': '^ISEQ'},
    'Euronext Lisbon': {'suffix': '.LS', 'country': 'Portugal', 'region': 'Europe', 'currency': 'EUR', 'benchmark_index': '^PSI20'},
    'Athens Exchange': {'suffix': '.AT', 'country': 'Greece', 'region': 'Europe', 'currency': 'EUR', 'benchmark_index': 'GD.AT'},
    # --- EXPANDED AMERICAS ---
    'BMV': {'suffix': '.MX', 'country': 'Mexico', 'region': 'Americas', 'currency': 'MXN', 'benchmark_index': '^MXX'},
    'BCBA': {'suffix': '.BA', 'country': 'Argentina', 'region': 'Americas', 'currency': 'ARS', 'benchmark_index': '^MERV'},
    'BCS': {'suffix': '.SN', 'country': 'Chile', 'region': 'Americas', 'currency': 'CLP', 'benchmark_index': None},
    # --- EXPANDED MIDDLE EAST / AFRICA ---
    'TASE': {'suffix': '.TA', 'country': 'Israel', 'region': 'Middle East / Africa', 'currency': 'ILS', 'benchmark_index': '^TA125.TA'},
    'Borsa Istanbul': {'suffix': '.IS', 'country': 'Turkey', 'region': 'Middle East / Africa', 'currency': 'TRY', 'benchmark_index': 'XU100.IS'},
    'EGX': {'suffix': '.CA', 'country': 'Egypt', 'region': 'Middle East / Africa', 'currency': 'EGP', 'benchmark_index': '^CASE30'},
    'QSE': {'suffix': '.QA', 'country': 'Qatar', 'region': 'Middle East / Africa', 'currency': 'QAR', 'benchmark_index': None},
    'DFM': {'suffix': '.AE', 'country': 'United Arab Emirates', 'region': 'Middle East / Africa', 'currency': 'AED', 'benchmark_index': None},
    'JSE': {'suffix': '.JO', 'country': 'South Africa', 'region': 'Middle East / Africa', 'currency': 'ZAR', 'benchmark_index': '^J203.JO'}
}

REGIONS = {
    'Americas': ['United States', 'Canada', 'Brazil', 'Mexico', 'Argentina', 'Chile'],
    'Europe': ['United Kingdom', 'Germany', 'France', 'Netherlands', 'Switzerland', 'Italy', 'Spain', 'Sweden', 'Norway', 'Denmark', 'Finland', 'Poland', 'Austria', 'Ireland', 'Portugal', 'Greece'],
    'Asia-Pacific': ['India', 'Japan', 'South Korea', 'China', 'Hong Kong', 'Australia', 'Taiwan', 'Singapore', 'Malaysia', 'Indonesia', 'Thailand', 'Philippines', 'New Zealand'],
    'Middle East / Africa': ['Saudi Arabia', 'Israel', 'Turkey', 'Egypt', 'Qatar', 'United Arab Emirates', 'South Africa']
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
