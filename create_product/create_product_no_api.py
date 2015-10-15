'''
This program creates adds new products to wish. It reads from the first column of a csv file that contains the parent
skus for new products. In order to create a product on wish with a particular parent sku, you must first create a 'Product'.
Then all the children (called 'variations' on Wish) must be created with that parent sku.

For example if you had a parent sku 1978 and the children skus 1978-L and 1978-M you must first post a request to wish
to create the 'Product' with the parent sku of 1978 and then once that product is created on wish you can then upload
the children. However, there is a sneaky, little caveat. Say, you upload the previous sku 1978 successfully to wish
and created a new product. If the children (or 'variations') failed to upload, the 1978 product will appear as a normal
product on wish, even though it doesn't really exist. Because of this, before I create product on wish, I quickly check
a parent's children in the database to see if I have enough information to create those children.
'''

import csv
import glob
import requests
import json
import argparse
from sqlalchemy import *
from sqlalchemy.orm.exc import NoResultFound
import time
from helpers import send_email_with_attachment, DictUnicodeWriter
from requests.exceptions import ConnectionError
import sys
import os
import io
from models import Product, Session, Pricing, WishTag, WishTracking, Exempt
from config import C1_ENABLED, C1_LIMIT, R1_ENABLED, R1_LIMIT, WISH_KEY, WISH_SHIPPING


# this will be a csv file of failed orders
CSV_FILENAME = time.strftime("%Y%m%d-%H%M%S") + '-wish-failed_create_order.csv'
FIELDNAMES = ['key', 'name', 'description', 'tags', 'sku', 'inventory', 'price', 'shipping',
              'parent_sku', 'main_image', 'extra_images', 'color', 'size', 'response', 'passfail']

def write_to_wish_template(filename, product_create_data, variation_create_data):
    csv_data = {
            '*Parent Unique ID': product_create_data.get('sku'),
            '*Unique ID': variation_create_data.get('sku'),
            'UPC': '',
            'Merchant Name': '',
            '*Product Name': product_create_data.get('name', ''),
            'Color': variation_create_data.get('color', ''),
            'Size': variation_create_data.get('size', ''),
            '*Quantity': variation_create_data.get('inventory'),
            '*Tags': product_create_data.get('tags', ''),
            'Description': product_create_data.get('description', ''),
            'MSRP': '',
            '*Price': variation_create_data.get('price', ''),
            '*Shipping': product_create_data.get('shipping' ''),
            'Product Page': '',
            'Main Image URL': product_create_data.get('main_image', ''),
            'Extra Image URL(s)': product_create_data.get('extra_images', ''),
            'Brand': product_create_data.get('brand', '')
        }

    print csv_data
    fieldnames = csv_data.keys()

    try:
        # test to see if file exists so wee can write the initial header if it doesn't
        f = open(filename , 'r')
        f.close()
    except IOError:
        f = open(filename, 'wb')
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        f.close()
    with open(filename, 'a+b') as f:
        writer = DictUnicodeWriter(f, fieldnames=fieldnames)
        # convert the float or integers to unicode
        writer.writerow({k:unicode(v) for k, v in csv_data.items()})

# TODO add size charts
# TODO log products that might not have been created on wish


def get_skus(fname):
    '''
    :return: a list of all the rows of the first column of the csv files except the first
    parses through a csv and returns the first column of data as a list. Ignores the first field.
    '''
    with open(fname, 'rU') as f:
        reader = csv.reader(f)
        # strip of any whitespace in case this is a tab separated value file
        skus = [row[0].strip() for row in reader]
    return set(skus[1:])

def get_high_child_price(parent_sku):
    '''
    finds the highest children sku price in the pricing table of the redrocket database. If it cannot find
    any children, it returns the price of the parent sku.
    :param parent_sku:
    :return:
    '''
    session = Session()
    # since the parent skus in the pricing table might be price at $0 I this function will take a parent sku and
    # and return the highest child sku price
    # I had to escape the percent and use the text function imported from sqlalchemy for this to work
    # TODO Reformat queries
    sql = ("select max(pr.ItemPrice) from pricingtable pr"
           " join producttable pt on pr.sku like concat(pt.parentsku, '-%')"
           " where pt.parentsku = :parent_sku;"
        )

    results = session.execute(text(sql), {'parent_sku': parent_sku})
    session.close()
    result = results.fetchone()
    highest_price = result[0]

    return highest_price

def has_size_and_color(child_sku):
    color = get_color(child_sku)
    size = get_size(child_sku)
    if size and color:
        return True
    return False

def get_wish_inventory(product_status, inventory):

    print 'inventory before ', inventory
    if (product_status == 'C1' or product_status == '') and (C1_ENABLED > 0) and (inventory <= C1_LIMIT):
        inventory = 0
        # disable = True

    if (product_status == 'R1' or product_status == '') and (R1_ENABLED > 0) and (inventory <= C1_LIMIT):
        inventory = 0
    print 'inventory after ', inventory
    return inventory

def get_alt_images(parent_sku, altimagecount):
    images = []
    for i in range(1, altimagecount + 1):
        images_url = 'http://images.oldglory.com/product/' + parent_sku + '.' + str(i) + 'f.jpg'
        images.append(images_url)
    return images

def get_size_chart(parent_sku):
    session = Session()

    # get the size_chart wish this query. Joins the producttable
    # and the wish_size_image_table on the categorytable on the product category. primarycategory is the same as
    # category_id in these fields.
    size_chart_query = ("select s.wish_sizeimage from producttable p"
                        " join wish_size_image_table s on s.category_id = p.primaryproductcategory"
                        " where p.sku = :parent_sku"
                        " and p.department = s.gender;")
    results = session.execute(text(size_chart_query), {'parent_sku': parent_sku})
    # this returns None if nothing is found
    result = results.fetchone()
    if result:
        wish_sizeimage = result.wish_sizeimage
        if wish_sizeimage:
            session.close()
            return 'http://images.oldglory.com/wish/{}'.format(result.wish_sizeimage)

    # try without the gender and department match
    size_chart_query = ("select s.wish_sizeimage from producttable p"
                        " join wish_size_image_table s on s.category_id = p.primaryproductcategory"
                        " where p.sku = :parent_sku;")

    results = session.execute(text(size_chart_query), {'parent_sku': parent_sku})
    result = results.fetchone()
    if result:
        wish_sizeimage = result.wish_sizeimage
        if wish_sizeimage:
            session.close()
            return 'http://images.oldglory.com/wish/{}'.format(result.wish_sizeimage)

def get_brand(parent_sku):
    session = Session()
    sql = (
        "select if((ct.category_description = '' or ct.category_description is null), if(p.producttype = 'FINISHED_GOOD', 'Old Glory','Tees Plus'), ct.category_description) as 'Brand'"
         " from redrocket.producttable pt"
        " inner join redrocket.productcategories pc on pt.sku = pc.sku"
        " inner join redrocket.categorytable ct on pc.category_name = ct.category_id"
        " inner join redrocket.categorytable ctp on ct.category_parent = ctp.category_id"
        " join redrocket.producttable p on p.sku = pt.sku"

        " where pt.storefront = 'old_glory'"
        " and pt.parentchild <> 'parent'"
        " and (ct.category_id like 'ent_%%' or ct.category_id like 'mus_%%' or ct.category_id like 'sp_%%' or ct.category_id like 'br_%%' or ct.category_id like 'ga_%%' )"
        # only lone or child skus only.
        " and pt.sku like :string;"
    )
    string = parent_sku + '-%%'

    results = session.execute(text(sql), {'string': string})
    result = results.fetchone()
    session.close()
    if result is not None:
        return result.Brand

def get_product_data(parent_sku):

    # TODO get the image url from the database table imageprocessortable so that this is not hard coded
    main_image_url = 'http://images.oldglory.com/product/{}f.jpg'.format(parent_sku)

    # first get the content for the product we need name, description, quantity, altimage count, itemprice. Parentchild
    # I need to know if this is a lone product. If it's a lone product then it won't have any children. I need to pass
    # the lone products to the create_wish_variation function.
    product = get_product(parent_sku)
    if product is None:
        return
    price = get_price(parent_sku)

    wish_quantity = get_wish_inventory(product.productstatus, product.quantity)
    
    size_chart = get_size_chart(parent_sku)

    if product.altimagecount > 0:
        # will return a list of alt images
        alt_images = get_alt_images(parent_sku, product.altimagecount)
    else:
        alt_images = None

    # in wish the extra images must be joined by a pipe character
    
    # alt_images is a list
    # size_chart is a string or None
    if not alt_images and not size_chart:
        extra_images = ''
    elif alt_images and size_chart:
        alt_images.append(size_chart)
        extra_images = '|'.join(alt_images)
    elif alt_images and not size_chart:
        extra_images = '|'.join(alt_images)
    elif not alt_images and size_chart:
        extra_images = size_chart


    # get the size_chart wish this query. Joins the producttable
    # and the wish_size_image_table on the categorytable on the product category. primarycategory is the same as
    # category_id in these fields.


    # if the brand does not exist in the producttable, get it from get_brand
    if not product.brand:
        brand = get_brand(parent_sku)

        # if we still don't have a brand just base the brand on the producttype in the
        # producttable
        if not brand:
            if product.producttype == 'FINISHED_GOOD':
                brand = 'Old Glory'
            else:
                brand = 'Tees Plus'
    else:
        brand = product.brand

    # get the tags
    #
    session = Session()
    wishtag = session.query(WishTag).get(product.primaryproductcategory)
    session.close()

    # tags starts out as a list of tags
    if wishtag:
        tags = wishtag.get_tags()
        if tags:
            tags = ','.join(tags)
    else:
        tags = ''



    # i want to make sure I don't set the price as zero so i'm grabbing the highest price of the child skus
    # the parent sku price might be set to zero so just to make sure we're not giving stuff away
    print 'first price ', price
    if not price:
        price = get_high_child_price(parent_sku)
    print 'second price ', price

    # will return 0 if under threshold inventory
    wish_inventory = get_wish_inventory(product.productstatus, product.quantity)

    # this data is getting sent to wish via requests to create a new product
    product_create_data = {
        'name': product.productname,
        'description': product.longdescription,
        'tags': tags,
        'sku': parent_sku,
        'inventory': wish_inventory,
        'price': price,
        'shipping': WISH_SHIPPING,
        'parent_sku': parent_sku,
        'main_image': main_image_url,
        'extra_images': extra_images,
        'brand': brand,
    }

    return product_create_data

def create_product(product_data):
    # this creates a new product on wish with the following data:
    # name, description, tags, sku, inventory, price, shipping, parent sku, main image, extra images
    # if successful, it will return the newly created wish id from the response
    # if not successful, it will return None

    # check to see if we have at least one variant to add for this product
    # if not has_one_variation_with_size_and_color(parent_sku):
    #     write_to_csv({'passfail': 'fail', 'sku': parent_sku, 'response': 'No size and color for any variants'})
    #     print "No size or color so passing on this product"
    #     return None

    # wish needs the api key as a paramater
    print product_data
    product_data.update({'key': WISH_KEY})

    for i in range(3):
        try:
            url = "https://merchant.wish.com/api/v1/product/add"
            r = requests.post(url, data=product_data)
        except ConnectionError:
            if i == 2:
                raise
            print "couldn't connect to wish, trying again..."
        else:
            break

    if r.status_code == 200:

        # get the wish id from the response json and return it
        data = r.json()
        wishid = data['data']['Product']['id']

        return wishid

    elif r.status_code == 400:
        print 'could not create this product'
        print r.text
        # a 400 could mean either it couldn't find the product or it already exists
        # check to see if this product is already on wish just in case this product just got created already

        # this function returns the wish id if i can get it from wish
        parent_sku = product_data['parent_sku']
        wishid = product_is_on_wish(parent_sku)
        if wishid:
            # it's on wish so get the wishid, update the database and return the wishid
            return wishid

    else:
        # not a 200 or 400
        return None

def is_lone_sku(sku):
    """Checks the producttable to see whether parent sku is lone or not"""
    s = Session()
    q = s.query(Product).filter_by(sku=sku)
    s.close()
    result = q.first()
    return result.parentchild == 'lone'

def get_color(child_sku):
    # color_query = (        "SELECT ct.wishcolor"
    #     " FROM   redrocket.productfeatures pf"
    #            " INNER JOIN redrocket.featuretable ft"
    #                    " ON pf.featureid = ft.feature_id"
    #            " INNER JOIN redrocket.colortable ct"
    #                    " ON ft.feature_description = ct.bizcolor"
    #     " WHERE  ft.product_feature_type_id = 'color'"
    #     " AND pf.sku = :child_sku;"
    #     )
    color_query = "SELECT color from producttable where sku = :sku;"
    session = Session()
    results = session.execute(text(color_query), {'child_sku': child_sku})
    session.close()
    result = results.fetchone()

    # fetchone returns None if nothing is found
    if result is None:
        return result
    # we found a record so return the color
    return result.wishcolor

def get_child_skus(parent_sku):
    """ Querys the producttable and returns the child skus for the parent_sku """
    session = Session()
    results = session.query(Product).with_entities(Product.sku).\
            filter(Product.sku.like(parent_sku + "-%")).all()
    session.close()
    return [result.sku for result in results]

def get_size(child_sku):
    session = Session()
    size_query = (
        "SELECT "
        " st.wish_value, pt.id_code, st.item_type as 'sizing_item_type', pt.itemtype as 'product_item_type'"
        " FROM   redrocket.producttable pt"
        " INNER JOIN redrocket.sizingtable st"
        " ON pt.id_code = st.id_code"
        " WHERE  pt.sku = :child_sku"
    )
    results = session.execute(text(size_query), {'child_sku': child_sku})
    session.close()
    if results.rowcount == 1:
        return results.fetchone().wish_value

    else:
        rows = results.fetchall()
        size = None
        for row in rows:
            if row.sizing_item_type == row.product_item_type:
                size = row.wish_value
        if not size:
            for row in rows:
                if row.sizing_item_type == '*':
                    size = row.wish_value
        return size

def get_product(child_sku):
    session = Session()
    product = session.query(Product).get(child_sku)
    session.close()
    return product

def get_price(child_sku):
    session = Session()
    try:
        itemprice = session.query(Pricing).get(child_sku).itemprice
        session.close()
    except AttributeError:
        # could not find this record in the pricingtable
        session.close()
        return None
    return itemprice

def update_database(product_data, variation_data):

    database_data = {
        'sku': variation_data['sku'],
        'wishsku': variation_data['sku'],
        'wishid': variation_data['wishid'],
        'wishparentsku': variation_data['parent_sku'],
        'wish_quantity': variation_data['inventory'],
        'on_wish': 1
    }


    # sku is the kkk
    session = Session()
    sku = database_data['sku']
    result = session.query(WishTracking).filter_by(sku=sku).first()
    if result:
        print 'updated record', database_data['sku']
        # we found this so update it
        result = session.query(WishTracking).filter_by(sku=sku).update(database_data)
        session.commit()
    else:
        print 'inserted new record', database_data['sku']
        session.add(WishTracking(**database_data))
        session.commit()

    session.close()
        
def variant_is_on_wish(child_sku):
    for i in range(3):
        try:
            r = requests.get('https://merchant.wish.com/api/v1/variant',
                         params={'key': WISH_KEY, 'sku': child_sku})
    
        except ConnectionError:
            if i == 2:
                raise
            print "couldn't connect to wish, trying again..."
        else:
            break

    if r.status_code == 200:
        return True

def product_is_on_wish(parent_sku):
    for i in range(3):
        try:
            r = requests.get('https://merchant.wish.com/api/v1/product',
                         params={'key': WISH_KEY, 'parent_sku': parent_sku})
    
        except ConnectionError:
            if i == 2:
                raise
            print "couldn't connect to wish, trying again..."
        else:
            break

    if r.status_code == 200:
        data = r.json()
        wishid = data['data']['Product']['id']
        return wishid

def get_variation_data(child_sku):

    color = get_color(child_sku)
    # get the size of the product
    size = get_size(child_sku)

    # gets a record from the producttable
    product = get_product(child_sku)
    if product is None:
        return

    # C1 or R1
    product_status = product.productstatus

    wish_inventory = get_wish_inventory(product_status, product.quantity)
    productname = product.productname

    price = get_price(child_sku)

    # this is the data to be passed to wish and NOT to the database
    variation_data = {
        'sku': child_sku,
        'color': color,
        'size': size,
        'inventory': wish_inventory,
        'price': price,
        'shipping': WISH_SHIPPING
    }

    return variation_data

def create_variation(variation_data):
    # creates wish variation from the parent sku
    # sku, color, size, inventory, price, shipping

    # wish need the api key as a paramter
    variation_data.update({'key': WISH_KEY})
    

    for i in range(3):
        try:
            url = 'https://merchant.wish.com/api/v1/variant/add'
            r = requests.post(url, data=variation_data)

        except ConnectionError:
            if i == 2:
                raise
            print "couldn't connect to wish, trying again..."
        else:
            break

    if r.status_code == 200:
        # this will replace the above write to csv function
        print 'this variation was successfully added to wish ', variation_data['sku']
        return True

        # update_product_tracking_wish(database_data)

    elif r.status_code == 400:
        print r.text
        # check to see if this variant is already on wish just in case this product just got created already and
        # i'm getting a 400 for another reason.
        child_sku = variation_data['sku']
        print 'variation data', variation_data
        if variant_is_on_wish(child_sku):
            # it's on wish so get the wishid, update the database and return the wishid
            # raw_json = r.text
            # data = json.loads(raw_json)
            return True
    else:
        return False

def has_size_and_color(product_variation_data):
    return bool(product_variation_data['size']) and \
            bool(product_variation_data['color'])

def get_exempt_status(sku):
    session = Session()
    q = session.query(Exempt).filter_by(sku=sku)
    try:
        result = q.one()
        if result.wish > 0:
            return True
        return False
    except NoResultFound:
        True

def main():
    # if no argument is provided, make this the default file
    if len(sys.argv) == 1:
        fname = 'V:\NewOGproducts.csv'
    elif len(sys.argv) == 2:
        fname = sys.argv[1]

    skus = get_skus(fname)

    SUCCESS_TEMPLATE = time.strftime("%Y%m%d-%H%M%S") + '_successful_uploads.csv'
    FAILED_TEMPLATE = time.strftime("%Y%m%d-%H%M%S") + '_failed_uploads.csv'
    # skus = ['120071']

    for sku in skus:
        # get_product_data will return information from the database on the sku that wish requires.
        # it is a dictionary that will serve as the paramaters to create a product on wish. The keys
        # to the dictionary are named so that they can be posted to wish without any manipulation
        product_data = get_product_data(sku)
        exempt = get_exempt_status(sku)
        if product_data is None or not exempt:
            write_to_wish_template(FAILED_TEMPLATE, {'sku': sku}, {})
            continue
        lone_sku = is_lone_sku(sku)
        if lone_sku: 
            child_skus = [sku]
        else:
            child_skus = get_child_skus(sku)

        # iterate through the child_skus
        # for each, get the data required to make a variation for wish
        # if all the data we need is there attempt to create product and
        # the variation

        # initially set this flag to false so we know if we have created a wish product already
        product_exists = False
        for child_sku in child_skus:
            # i recieved a wish id from wish, now I can create the variation on wish this function will also call the
            # function that updates the product_tracking_wish table in the redrocket database
            # and write to a csv file loggig the data that was created
            variation_data = get_variation_data(child_sku)

            # lone skus can sneak by without size and color
            if has_size_and_color(variation_data) or lone_sku:
                # the variation data is complete enough where we can post to wish
                if not product_exists:
                    wishid = create_product(product_data)

                # set the flag to True so we don't try to unecessarily post to Wish
                # with data that's already there
                # make sure the price is valid
                if wishid and variation_data['price'] != 0\
                        or variation_data['price'] is not None:
                    product_exists = True
                    # create_variation posts data to wish to create a variation
                    variation_data.update({'parent_sku': sku, 'wishid': wishid})
                    # post to wish. create_variation will return False if unsuccessful
                    variation_created = create_variation(variation_data)
                else:
                    variation_created = False
            else:
                variation_created = False

            if variation_created:
                write_to_wish_template(SUCCESS_TEMPLATE, product_data, variation_data)
                update_database(product_data, variation_data)
            else:
                print 'writing to failed'
                write_to_wish_template(FAILED_TEMPLATE, product_data, variation_data)

    # send the email with the csvfile
    send_email_with_attachment(SUCCESS_TEMPLATE, FAILED_TEMPLATE)
    for fname in [SUCCESS_TEMPLATE, FAILED_TEMPLATE]:
        try:
            os.remove(fname)
        except OSError:
            pass


if __name__ == '__main__':
    main()
