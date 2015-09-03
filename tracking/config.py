import MySQLdb
from secret import DATABASE


def get_wish_key():
    host = DATABASE['host']
    user = DATABASE['user']
    passwd = DATABASE['passwd']

    connection = MySQLdb.Connect(host=host, db='redrocket', passwd=passwd, user=user)
    cursor = connection.cursor()

    sql = "select api_key from feedersettings.wish where storefront = %(store_front)s;"
    cursor.execute(sql, {'store_front': 'old_glory'})
    row = cursor.fetchone()
    key = row[0]
    connection.close()

    return key

WISH_KEY = get_wish_key()
