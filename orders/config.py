import MySQLdb
from secret import DATABASE

WISH_STOREFRONT = 'old_glory'

def get_wish_key():
    connection = MySQLdb.Connect(host=DATABASE['host'], user=DATABASE['username'], passwd=DATABASE['password'], db='feedersettings')
    cursor = connection.cursor()

    sql = "select api_key from feedersettings.wish where storefront = %(store_front)s;"
    cursor.execute(sql, {'store_front': WISH_STOREFRONT})
    row = cursor.fetchone()
    key = row[0]
    connection.close()

    return key


WISH_KEY = get_wish_key()
