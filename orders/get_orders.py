import requests
import json
import glob
import sys
import os
import MySQLdb
import MySQLdb.cursors
import io
from itertools import groupby
from pprint import pprint


# RemoveLeftOverFiles
# sometimes there will be files that are just left in the directory. This function is
# to do some house cleanup prior to any run.
def RemoveLeftOverFiles():
    filelist = glob.glob("*.json")
    for f in filelist:
        os.remove(f)


def UpdateDatabase(connection, child):

    # is this order item in the salesordertable table?
    # the external_id and sku uniquely identify the order item
    sql = (
        "select recnum from redrocket.sales_order_table"
        " where external_id = %(external_id)s and sku = %(sku)s;"
    )
    cursor = connection.cursor()
    rowcount = cursor.execute(sql, child)

    print child
    if rowcount == 0:
        # if this external_id is not in salesordertable table, insert the record
        sql = (
            "INSERT INTO sales_order_table"
            " SET sku = %(sku)s,"
            " storefront = %(storefront)s,"
            " sales_channel = %(sales_channel)s,"
            " OrderItemId = %(wish_order_id)s,"
            " external_id = %(external_id)s,"
            " quantity = %(quantity)s,"
            " order_date = %(order_date)s,"
            " updatetime = %(updatetime)s,"
            " `name` = %(name)s,"
            " address1 = %(address1)s,"
            " address2 = %(address2)s,"
            " city = %(city)s,"
            " country_code = %(country_code)s,"
            " state_province = %(state_province)s,"
            " postal_code = %(postal_code)s,"
            " order_line_item = %(order_line_item)s,"
            " unit_price = %(unit_price)s"
        )

        cursor.execute(sql, child)
        print cursor._last_executed
        connection.commit()
        cursor.close()
    else:
        # we found the external id and order item (or sku). insert or update the record depending on whether or not the wish_order_id is already
        # in there
        sql = (
            "UPDATE sales_order_table"
            " SET sku = %(sku)s,"
            " storefront = %(storefront)s,"
            " sales_channel = %(sales_channel)s,"
            " OrderItemId = %(wish_order_id)s,"
            " external_id = %(external_id)s,"
            " quantity = %(quantity)s,"
            " order_date = %(order_date)s,"
            " updatetime = %(updatetime)s,"
            " `name` = %(name)s,"
            " address1 = %(address1)s,"
            " address2 = %(address2)s,"
            " city = %(city)s,"
            " country_code = %(country_code)s,"
            " state_province = %(state_province)s,"
            " postal_code = %(postal_code)s,"
            " order_line_item = %(order_line_item)s,"
            " unit_price = %(unit_price)s"
            " WHERE external_id = %(external_id)s and sku = %(sku)s;"
        )

        cursor.execute(sql, child)
        print cursor._last_executed
        connection.commit()
        cursor.close()

def ProcessWishOrders(connection, sequence):
    global storefront

    # always start with the file that was requested from the prior request pull.
    with io.open("WishResultFile_{}.json".format(sequence), 'r', encoding="utf8") as f:
        data = json.load(f)
    order_list = data['data']
    pprint(order_list)

    # with the file loaded, now run through it and get all of the data. Save the data into the Tracking Table.
    # groupby groups the orders by the transaction
    # i do this so that we can keep track of the order_line_item
    for key, group in groupby(order_list, lambda item: item['Order']['transaction_id']):
        order_line_item = 1
        for order in group:
            print order
            order_info = order['Order']
            shipping_detail = order_info['ShippingDetail'] # shipping detail contains the customer info

            try:
            # each child object will be passed to the UpdateDatabase function to be inserted into the database
            # the child keys map to the name of the salesordertable database columns
                child = {
                    'sku': order_info['sku'],
                    'storefront': storefront,
                    'sales_channel': 'WISH_SALES_CHANNEL',
                    'wish_order_id': order_info['order_id'],
                    'external_id': order_info['transaction_id'],
                    'quantity': order_info['quantity'],
                    'order_line_item': order_line_item,
                    'order_date': order_info['order_time'],
                    'updatetime': order_info.get('last_updated', None),
                    'name': shipping_detail['name'],
                    'address1': shipping_detail.get('street_address1', u''),
                    'address2': shipping_detail.get('street_address2', u''),
                    'city': shipping_detail.get('city', u''),
                    'country_code': shipping_detail.get('country', u''),
                    'state_province': shipping_detail.get('state', u''),
                    'postal_code': shipping_detail.get('zipcode', u''),
                    # 'email_address': '',
                    'unit_price': order_info['price'],
                    # 'SalesRecord': '',
                    # 'TrackingNumber': '',
                    'days_to_fulfill': order_info['days_to_fulfill'],

                }
                order_line_item += 1

                UpdateDatabase(connection, child)
            except KeyError:
                print 'Error: Dictionary key error'

    paging = data.get('paging', None)
    if paging:
        next_url = paging.get('next', None)
        if next_url:
            r = requests.get(next_url)
            sequence += 1
            with open("WishResultFile_{}.json".format(sequence), "w") as f:
                f.write(r.content)
            ProcessWishOrders(connection, sequence)



def GetOrdersToCheck():
    global wishkey

    # format the payload selection. Note, we will be using JSON, the xml line is commented out.
    # payload = {
    #     'key': WISH_KEY,
    #     # 'format': 'xml',
    #     'start': '0',
    #     'limit': '500',
    #     'since': '2001-10-15'
    # }

    # url = "https://merchant.wish.com/api/v1/order/get-fulfill"

    # Request the first mult-get. The next request is actually the last part of the results of the request.
    # r = requests.get(url, params=payload)

    payload = {
        'key': wishkey,
    }

    r = requests.get('https://merchant.wish.com/api/v1/order/get-fulfill', params=payload)
    sequence = 1
    f = open("WishResultFile_{}.json".format(sequence), "w")  # opens file with name of "test.txt"
    f.write(r.content)
    f.close()

    # we have the first result file retrieved, now to process the results. At the completion of the
    # process, the recursive routine will start.
    host = os.environ.get("NEW_MYSQLDB_HOST")
    user = os.environ.get("MYSQLDB_USER")
    passwd = os.environ.get("MYSQLDB_PASSWD")
    connection = MySQLdb.Connect(host=host, user=user,
                                passwd=passwd, db='redrocket', charset="utf8",
                                cursorclass=MySQLdb.cursors.DictCursor)
    ProcessWishOrders(connection, sequence)
    connection.close()

    # all the loops are completed. Now to fall out and exit the script.
    print('all done.')


def main():
    global storefront
    global wishkey

    if len(sys.argv) == 2:
        storefront = sys.argv[1].lower()
        if storefront == 'old_glory':
            wishkey = os.environ.get("OG_WISH_KEY")
            print wishkey
        elif storefront == 'animalworld':
            wishkey == os.envrion.get("AW_WISH_KEY")
        else:
            print 'invalid storefront'
            sys.exit(1)
    else:
        print 'USAGE: python wish_orders.py [storefront]'
        sys.exit(1)
    # remove extra json files from previous run
    RemoveLeftOverFiles()
    # start recursive process
    GetOrdersToCheck()

if __name__ == "__main__":
    main()
