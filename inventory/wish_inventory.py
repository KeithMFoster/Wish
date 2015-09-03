from __future__ import print_function
import requests
import wishdb
import wish_settings
import logging

LOG_FILENAME = 'errorlog.txt'
logging.basicConfig(filename=LOG_FILENAME,
                    level=logging.DEBUG,
                    )

def get_threshold_settings():
    # this pulls from the feedersettings.threshold_settings table
    global gC1_LimitValue
    global gC1_Enabled
    global gC1_ZeroSwitch

    global gR1_LimitValue
    global gR1_Enabled
    global gR1_ZeroSwitch

    global gHighLimitValue
    global gHighLimitSwitch
    # Get Threasholds.

    # this is a MySQLdb.Connection() object
    db = wishdb.WishDB()
    db = db.connection
    cursor = db.cursor()

    sql = "select * from feedersettings.threshold_settings where channel = 'Wish' and storefront = '{}';".format(wish_settings.WISH_STOREFRONT)
    cursor.execute(sql)
    results = cursor.fetchall()
    for row in results:
        gC1_LimitValue = row[3]
        gC1_Enabled = row[4]
        gC1_ZeroSwitch = row[5]

        gR1_LimitValue = row[6]
        gR1_Enabled = row[7]
        gR1_ZeroSwitch = row[8]

        gHighLimitValue = row[9]
        gHighLimitSwitch = row[10]

    db.close()

def get_products_to_check():

    global gC1_LimitValue
    global gC1_Enabled
    global gC1_ZeroSwitch

    global gR1_LimitValue
    global gR1_Enabled
    global gR1_ZeroSwitch

    global gHighLimitValue
    global gHighLimitSwitch

    # this is a MySQLdb.Connection() object
    # http://mysql-python.sourceforge.net/MySQLdb.html
    db = wishdb.WishDB()
    db = db.connection
    cursor = db.cursor()

    sql = "select p.sku, p.wishsku, p.wish_quantity, p.WishInventoryUpdateDate, pt.quantity, pt.productstatus from redrocket.product_tracking_wish p "
    sql += "inner join redrocket.producttable pt on p.sku = pt.sku "
    sql += "where p.on_wish > 0 and p.storefront = '" + wish_settings.WISH_STOREFRONT + "' "
    sql += " and (p.wish_quantity <> pt.quantity or p.WishInventoryUpdateDate < Now() - INTERVAL 1 MONTH)"

    sql += " ORDER BY pt.sku limit 500"
    # myQuantity = 0
    OnWishClear = 0
    cursor.execute(sql)
    results = cursor.fetchall()
    # disable = False
    # enable = False
    if cursor.rowcount > 0:
        for row in results:
            try:

                # myQuantity may end up being different from myTrueQuantity depending on whether or not the product
                # is 'C1' enabled in the database and what the C1_LimitValue is in the database
                myQuantity = row[4]
                myTrueQuantity = row[4]
                mySKU = row[0]

                print(myQuantity)
                # if the product status is an empty string it counts as C1
                if (row[5] == 'C1' or row[5] == '') and (gC1_Enabled > 0) and (myQuantity <= gC1_LimitValue):
                    myQuantity = 0
                    # disable = True

                if (row[5] == 'R1') and (gR1_Enabled > 0) and (myQuantity <= gR1_LimitValue):
                    myQuantity = 0

                if (gHighLimitSwitch > 0) and (myQuantity > gHighLimitValue):
                    myQuantity = gHighLimitValue

                # if (row[5] == 'R1') and (gR1_Enabled > 0) and (myQuantity >= gR1_LimitValue):
                #     enable = True

                # if disable:
                #     payload = {'key': wish_settings.WISH_KEY, 'sku': mySKU}
                #     wishapi = "https://merchant.wish.com/api/v1/variant/disable"
                #     requests.post(wishapi, payload)
                #
                # if enable:
                #     payload = {'key': wish_settings.WISH_KEY, 'sku': mySKU}
                #     wishapi = 'https://merchant.wish.com/api/v1/product/enable'
                #     requests.post(wishapi, payload)
                payload = {'key': wish_settings.WISH_KEY, 'sku': mySKU, 'inventory': str(myQuantity)}
                print(payload)
                wishapi = "https://merchant.wish.com/api/v1/variant/update-inventory"
                r = requests.post(wishapi, data=payload)
                status = 'SKU: ' + mySKU + ' Status Code: ' + str(r.status_code) + ' Quantity: ' + str(myQuantity)
                print(status)

                print(r.text)
                ResponseCode = r.status_code
                if ResponseCode == 400:
                    # try again because sometime we get a 400 even though the product really is on wish

                    sql = "update redrocket.product_tracking_wish set "
                    sql = sql + "Wish_quantity = " + chr(39) + str(myTrueQuantity) + chr(39)
                    sql = sql + ", WishInventoryUpdateDate = NOW()"
                    sql = sql + ", on_wish = 0"
                    sql = sql + " where sku = " + chr(39) + mySKU + chr(39)
                    print('setting mySKU', mySKU, 'to not on_wish')
                    cursor.execute(sql)
                    db.commit()

                if ResponseCode == 200:
                    sql = "update redrocket.product_tracking_wish set "
                    sql = sql + "Wish_quantity = " + chr(39) + str(myTrueQuantity) + chr(39)
                    sql = sql + ", WishInventoryUpdateDate = NOW()"
                    sql = sql + " where sku = " + chr(39) + mySKU + chr(39)
                    cursor.execute(sql)
                    db.commit()
                elif ResponseCode > 500:
                    logging.debug(status)
                else:
                    logging.debug(r.text)
                    # sql = "update redrocket.product_tracking_wish set "
                    # sql = sql + "on_wish  = " + chr(39) + str(OnWishClear) + chr(39)
                    # sql = sql + ", WishInventoryUpdateDate = NOW()"
                    # sql = sql + " where sku = " + chr(39) + mySKU + chr(39)
                    # cursor.execute(sql)
                    # db.commit()

            except TypeError:
                logging.debug(status)
                print('TypeError Exception. Passing on this data.')
    else:
        print('nothing to update')

    db.close()

def main():
    get_threshold_settings()
    get_products_to_check()


if __name__ == "__main__":
    main()
