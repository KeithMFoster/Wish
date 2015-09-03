import wish_settings
import wishdb
import requests
import datetime
import logging
import pickle


LOG_FILENAME = 'errorlog.txt'
logging.basicConfig(filename=LOG_FILENAME,
                    level=logging.DEBUG,
                    )

WISH_UPDATE_PRODUCT_URL = 'https://merchant.wish.com/api/v1/product/update'
WISH_KEY = wish_settings.WISH_KEY





def main():

    # db = wishdb.WishDB()
    #
    # connection = db.connection
    # cursor = connection.cursor()
    #
    # size_charts_sql = "select distinct wish_sizeimage from wish_size_image_table where wish_sizeimage != '';"
    # cursor.execute(size_charts_sql)
    # size_charts = [row[0] for row in cursor.fetchall()]
    # connection.close()

    gender = ['Boys_Youth_T-Shirt.png', 'Girls_Youth_T-Shirt.png', 'Boys_Juvenile_T-Shirt.png', 'Girls_Juvenile_T-Shirt.png']

    size_charts = ['Boys_Youth_T-Shirt.png', 'Girls_Youth_T-Shirt.png', 'Toddler_T-Shirt.png',
                   'Juniors_T-Shirt.png', 'Juniors_Raglans.png', 'Juniors_Hoodie.png', 'Boys_Juvenile_T-Shirt.png',
                   'Girls_Juvenile_T-Shirt.png', 'Mens_Hoodie.png', 'Mens_T-Shirt.png', 'Womens_Hoodie.png',
                   'Womens_T-Shirt.png']

    print size_charts
    sku_set = set()
    for size in size_charts:
        db = wishdb.WishDB()
        connection = db.connection
        cursor = connection.cursor()

        # this query will get the wish ids associated with the appropriate size chart
        get_skus_sql = ('select p.sku from redrocket.producttable p'
                        ' join redrocket.wish_size_image_table wsi on p.primaryproductcategory = wsi.category_id'
                        ' join redrocket.product_tracking_wish ptw on ptw.sku = p.sku'
                        ' where wsi.wish_sizeimage = \'{size}\''
                        ' and ptw.on_wish > 0').format(size=size)
        if size in gender:
            get_skus_sql += " and p.department = wsi.gender;"
        else:
            get_skus_sql += ';'
        print get_skus_sql

        cursor.execute(get_skus_sql)
        results = cursor.fetchall()
        connection.close()
        skus = [row[0] for row in results]
        for sku in skus:
            sku_set.add(sku)

    
    f = open('already_updated_skus.pickle', 'wb')
    pickle.dump(sku_set, f)
    f.close()
if __name__ == '__main__':
    main()

