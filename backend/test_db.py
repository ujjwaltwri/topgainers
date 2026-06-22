from database import Database
db = Database('../data/stocks.db')
print(db.get_top_movers('gainers', '6M', limit=5))
