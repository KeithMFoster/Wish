from config import WISH_KEY
from secret import DATABASE
import MySQLdb
import requests
from pprint import pprint


def update_wish(data):
    """Update both tracking up on wish and the tracking table"""
    
    url = 'https://merchant.wish.com/api/v1/order/fulfill-one'
    r = requests.post(url, data=data)
    print data
    if r.status_code == 200 and r.headers.get('content-type') == 'application/json':
        print r.status_code
        print r.text
        print data
        print
        return True

    elif r.status_code == 400 and r.headers.get('content-type') == 'application/json':
        print r.status_code
        print r.text
        print data
        print
        data = r.json()
        if data['code'] == 1002: # order has already started processing
            return True
        elif data['code'] == 1003: # tracking number has been used before
            return True
        elif data['code'] == 1014: # tracking number already confirmed
            return True
    else:
        print r.status_code
        print r.text
        print data
        print
        return False 


def update_database(conn, data):

    sql = (
        "UPDATE tracking_table"
        " SET sent_tracking = 1"
        " WHERE Sales_Channel = 'WISH_SALES_CHANNEL'"
        " AND external_id = %(external_id)s"
        " AND OrderSku = %(sku)s;"
    )
    cursor = conn.cursor()
    cursor.execute(sql, data)
    print cursor._last_executed
    conn.commit()
    cursor.close()


def get_unsent_orders(conn):

    fulfill_one_url = "https://merchant.wish.com/api/v1/order/fulfill-one"
    sql = (
        "SELECT s.sku, s.external_id, s.orderitemid, t.trackingcode, t.carrier FROM tracking_table t"
        " JOIN salesordertable s on s.external_id = t.external_id"
        " WHERE t.Sales_Channel = 'WISH_SALES_CHANNEL'"
        # " and t.sent_tracking = 0 and s.storefront = %(storefront)s LIMIT 10;"
        " and t.sent_tracking = 0"
        " and (s.order_id != '' or s.order_id is null)"
        " and s.storefront = %(storefront)s"
        " and s.orderitemid != '';"
    )
    cursor = conn.cursor()
    cursor.execute(sql, {'storefront': 'old_glory'})
    results = cursor.fetchall()
    cursor.close()
    return results

def main():
    host = DATABASE['host']
    user = DATABASE['user']
    passwd = DATABASE['passwd']

    conn = MySQLdb.Connect(host=host, db='redrocket', passwd=passwd,
                            user=user, cursorclass=MySQLdb.cursors.DictCursor)

    results = get_unsent_orders(conn)

    for row in results:
        carrier = row['carrier']
        orderitemid = row['orderitemid']
        trackingcode = row['trackingcode']
        sku = row['sku']
        external_id = row['external_id']
        if carrier == '_NA_':
            wish_tracking_provider = 'UPS'
        else:
            wish_tracking_provider = 'USPS'


        wish_tracking_number = trackingcode
        wish_id = orderitemid
        wish_tracking_data = {
                'key': WISH_KEY,
                'id': wish_id,
                'tracking_number': wish_tracking_number,
                'tracking_provider': wish_tracking_provider
            }

        wish_updated = update_wish(wish_tracking_data)

        if wish_updated:
           database_data = {
                'sku': sku,
                'external_id': external_id,
            }
           update_database(conn, database_data)

if __name__ == '__main__':
    main()
