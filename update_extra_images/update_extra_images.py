import wish_settings
import wishdb
import requests
import datetime
import logging
LOG_FILENAME = 'errorlog.txt'
logging.basicConfig(filename=LOG_FILENAME,
                    level=logging.DEBUG,
                    )

WISH_UPDATE_PRODUCT_URL = 'https://merchant.wish.com/api/v1/product/update'
WISH_KEY = wish_settings.WISH_KEY



def update_images(parentskus_wishids_imagecounts, size):
    # skus_alt_images is a list of tuples
    # each tuple has the parent sku, the wishid and the number of alt images according to the database

    # size is a string that corresponds to the file name corresponding size chart

    # create a error log file
    time = datetime.datetime.now().strftime('%m_%d_%Y_%H%M%S')
    error_file_name = 'errorlog/' + time
    f = open(error_file_name, 'w')
    f.close()

    for parentsku_wishid_imagecount in parentskus_wishids_imagecounts:
        images = []
        alt_image_url = 'http://images.oldglory.com/product/'

        # unpack the tuple
        parentsku, wishid, alt_image_count = parentsku_wishid_imagecount

        if alt_image_count:
            for i in range(1, alt_image_count + 1):
                url = alt_image_url + parentsku + '.' + str(i) + 'f.jpg'
                images.append(url)

        # get the correct size chart and append it to the images
        size_chart_image_url = 'http://images.oldglory.com/wish/' + size
        images.append(size_chart_image_url)
        extra_images = '|'.join(images)
        data = {'key': wish_settings.WISH_KEY, 'id': wishid, 'extra_images': extra_images}
        while True:
            try:
                r = requests.post(WISH_UPDATE_PRODUCT_URL, data=data)
            except requests.exceptions.ConnectionError:
                # try again
                pass
            else:
                break

        print str(r.status_code), wishid, extra_images
        if r.status_code != 200:
            print 'Error: ', r.status_code, wishid
            with open(error_file_name, 'a') as f:
                f.write(str(r.status_code) + ' ' + str(wishid) + ' ' + parentsku)


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
    size_charts = ['infant.png']

    print size_charts
    for size in size_charts:
        db = wishdb.WishDB()
        connection = db.connection
        cursor = connection.cursor()

        # this query will get the wish ids associated with the appropriate size chart
        get_skus_sql = ('select distinct p.parentsku, ptw.WishID, p.AltImageCount from redrocket.producttable p'
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
        parentskus_wishids_imagecounts = [(row[0], row[1], row[2]) for row in results]
        if parentskus_wishids_imagecounts:
            update_images(parentskus_wishids_imagecounts, size)

if __name__ == '__main__':
    main()