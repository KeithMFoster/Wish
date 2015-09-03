import wishdb


db = wishdb.WishDB()
db = db.connection
cursor = db.cursor()

sql = "select Standard_Shipping, API_KEY from feedersettings.wish where storefront = 'old_glory'"
cursor.execute(sql)
results = cursor.fetchall()

for row in results:
    WISH_SHIPPING = row[0]
    WISH_KEY = row[1]
db.close()


WISH_STOREFRONT = 'old_glory'