import wishdb


def get_wish_key():
    db = wishdb.WishDB()
    db = db.connection
    cursor = db.cursor()

    sql = "select api_key from feedersettings.wish where storefront = 'old_glory'"
    cursor.execute(sql)
    results = cursor.fetchall()
    for row in results:
        key = row[0]
    db.close()

    return key

WISH_KEY = get_wish_key()
WISH_STOREFRONT = 'old_glory'