import MySQLdb
from secret import DATABASE


def get_wish_key():
    db = MySQLdb.Connect(db='redrocket', host=DATABASE['host'], user=DATABASE['username'], passwd=DATABASE['password'])
    cursor = db.cursor()

    sql = "SELECT api_key FROM feedersettings.wish WHERE storefront = 'old_glory';"
    cursor.execute(sql)
    results = cursor.fetchall()
    for row in results:
        key = row[0]
    db.close()

    return key

WISH_KEY = get_wish_key()
