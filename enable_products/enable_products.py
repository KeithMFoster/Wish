import json
import requests
import sys
from random import randint
import glob
import unicodedata
import datetime
import os
import wish_settings
from secret import DATABASE
from sqlalchemy import *
import csv
import time

# this will be a csv file of failed orders
CSV_FILENAME = time.strftime("%Y%m%d-%H%M%S") + '-failed-to-update.csv'
FIELDNAMES = ['on_wish', 'item_marker', 'inventory', 'product_id', 'sku', 'parent_sku', 'enabled', 'name']


def write_to_csv(item):
    fieldnames = FIELDNAMES
    try:
        # test to see if file exists so wee can write the initial header if it doesn't
        f = open(CSV_FILENAME, 'r')
        f.close()
    except IOError:
        f = open(CSV_FILENAME, 'w')
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        f.close()
    with open(CSV_FILENAME, 'ab') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator='\n')
        writer.writerow({k:v.encode('utf8') for k,v in item.items()})


# RemoveLeftOverFiles
# sometimes there will be files that are just left in the directory. This function is
# to do some house cleanup prior to any run.
def remove_json_files():
    file_list = glob.glob("*.json")
    for f in file_list:
        os.remove(f)


def update_database(connection, wish_child):

    global error_log_file_name

    sku = wish_child['sku']

    # remove or replace unicode characters in name with ascii equivalent
    if type(wish_child['name']) == unicode:
        wish_child['name'] = unicodedata.normalize('NFKD', wish_child['name']).encode('ascii', 'ignore')

    # is this product in the tracking table?
    trans = connection.begin()
    sql = "select * from redrocket.product_tracking_wish where sku = '{}'".format(sku)
    result = connection.execute(sql)

    if result.rowcount > 0:
        try:
            sql = ("UPDATE redrocket.product_tracking_wish SET"
                   " WishID = '{product_id}',"
                   " On_Wish = {on_wish},"
                   " ItemMarker = {item_marker},"
                   " WishSKU = '{sku}',"
                   " WishTitle = '{name}',"
                   " WishParentSKU = '{parent_sku}',"
                   " Wish_Status = '{enabled}',"
                   " Wish_quantity = {inventory}"
                   " WHERE sku = '{sku}';").format(**wish_child)
            print sql
            connection.execute(sql)
            trans.commit()
            print 'updated record'
            print
        except Exception, err:
            write_to_csv({'product_id': wish_child['product_id'], 'sku': wish_child['sku'], 'name': wish_child['name']})
            print 'rolling back'
            print sql
            trans.rollback()

    else:
        try:
            sql = ("INSERT INTO redrocket.product_tracking_wish"
                   " (sku, WishID, On_Wish, ItemMarker, WishSKU, WishParentSKU, Wish_Status, Wish_quantity )"
                   " VALUES ('{sku}', '{product_id}', {on_wish}, {item_marker}, '{sku}', '{parent_sku}', '{enabled}', {inventory});").format(**wish_child)
            print sql
            connection.execute(sql)
            trans.commit()
            print 'inserted new record'
            print

        except Exception, err:

            write_to_csv({'product_id': wish_child['product_id'], 'sku': wish_child['sku'], 'name': wish_child['name']})
            print 'rolling back'
            print sql
            trans.rollback()

def read_json_files(connection, sequence):
    global wishkey
    current_json_file = "wish_result_file_{}.json".format(sequence)
    # increment the json file sequence for next recursive call
    try:
        # try to open the file to see if it exists
        f = open(current_json_file, "r")
    except IOError:
        # this will end the recursive process
        return
    # turn the json into a python data structure
    wish_data = json.load(f)
    # data is an array that contains rows of products. each product
    for row in wish_data['data']:

        product = row['Product']
        name = product['name'].replace("'", "''")
        parent_sku = product.get('parent_sku', None)
        variants = product['variants']

        # now, for any of the children, but for Wish, any lone products will also be a child.
        for variant in variants:
            v = variant['Variant']
            print v
            if int(v['inventory']) >= 4:

                r = requests.post("https://merchant.wish.com/api/v1/variant/update", data={"enabled": True, 'key': wishkey, 'sku': v['sku']})
                print r.status_code
                print r.text
                if r.status_code == 200:
                    wish_child = {
                        "on_wish": 1,
                        "item_marker": randint(1, 99),
                        "parent_sku": parent_sku,
                        "sku": v['sku'],
                        "product_id": v['product_id'],
                        # "price": v.get('price', ''),
                        "enabled": "True",
                        # "shipping": v.get('shipping', ''),
                        "inventory": v.get('inventory', '0'),
                        # "shipping_time": v.get('shipping_time', ''),
                        # "id": v['id'],
                        # "msrp": v['msrp'],
                        "name": name,
                    }
                else:
                    continue

            update_database(connection, wish_child)
    return read_json_files(connection, sequence + 1)

def get_json_files(sequence):
    # this function retrieves all the json files from wish
    # until there is not "paging" key meaning ther are no
    # more files to retrieve
    global error_log_file_name
     # try to open the file to see if it exists
    current_json_file = "wish_result_file_{}.json".format(sequence)
    f = open(current_json_file, "r")
    # turn the json into a python data structure
    wish_data = json.load(f)

    try:
        next_file = wish_data['paging']
        r = requests.get(next_file['next'])
        print next_file['next']

        sequence += 1
        current_json_file = "wish_result_file_{}.json".format(sequence)
        with open(current_json_file, "w") as f:
            f.write(r.content)

        get_json_files(sequence)


    except KeyError:
        # this is the case that ends the recursive process

        error = 'no next file'
        error += str(sys.exc_info()[0])
        error += str(sys.exc_info()[0])
        error += '\n'
        with open(error_log_file_name, 'a') as f:
            f.write(error)


def get_products_to_check():
    global wishkey
    # this basically start the recursive process by calling process_wish_results(sequence)

    wish_url = "https://merchant.wish.com/api/v1/product/multi-get"
    payload = {
        'key': wishkey,
        # 'format': 'xml',
        'start': '0',
        'limit': '500',
        'since': '2001-10-15'
    }

    # Request the first multi-get. The next request is actually the last part of the results of the request.
    r = requests.get(wish_url, params=payload)
    sequence = 1
    current_json_file = "wish_result_file_{}.json".format(str(sequence))
    f = open(current_json_file, "w")
    f.write(r.content)
    f.close()
    engine = create_engine("mysql://{username}:{password}@{host}/redrocket".format(
                            username=DATABASE['username'], password=DATABASE['password'],
                            host=DATABASE['host']))
    connection = engine.connect()
    get_json_files(sequence)

    # read the json files we retrieved and start with the
    # first file
    read_json_files(connection, 1)
    connection.close()

    print 'all done'

def main():
    global error_log_file_name
    global storefront
    global wishkey
    if len(sys.argv) == 2:
        storefront = sys.argv[1]
        if storefront.lower() == 'old_glory':
            wishkey = os.environ.get('OG_WISH_KEY')
        elif storefront.lower() == 'animalworld':
            wishkey = os.environ.get('AW_WISH_KEY')
        else:
            print 'could not find wish api key'
            sys.exit(1)
    else:
        print 'please include storefront as argument'
        sys.exit(1)
    # create a log file for errors. opening in write mode will truncate the file if it exists
    date = datetime.datetime.now()

    error_log_dir = 'errorlog'
    error_log_file_name = os.path.join(error_log_dir, date.strftime('%Y%b%d%I%M%p'))

    f = open(error_log_file_name, 'w')
    f.close()
    # remove any old json files hangin around in the directory
    remove_json_files()
    get_products_to_check()

if __name__ == '__main__':


    main()
