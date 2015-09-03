import wish_settings
import wishdb
import requests
import pickle
import sys



WISH_UPDATE_PRODUCT_URL = 'https://merchant.wish.com/api/v1/product/update'
WISH_KEY = wish_settings.WISH_KEY


with open('already_updated_skus.pickle', 'rb') as f:
    already_updated_skus = pickle.load(f)


sql = "SELECT p.sku, p.altimagecount FROM producttable p JOIN product_tracking_wish w on w.sku = p.sku WHERE altimagecount > 0 and w.on_wish > 0;"

wishdb = wishdb.WishDB()
conn = wishdb.connection

cursor = conn.cursor()
cursor.execute(sql)

results = cursor.fetchall()

alt_image_url = 'http://images.oldglory.com/product/'

skus_altcount = [(result[0], result[1]) for result in results]

TOTAL = []
for tup in skus_altcount:
    sku, altcount = tup
    if sku not in already_updated_skus:
        print sku, altcount
    sys.exit()
    images = []

    if sku in already_updated_skus or True:
        for i in range(1, altcount + 1):
            url = alt_image_url + sku + '.' + str(i) + 'f.jpg'
            images.append(url)
    extra_images = '|'.join(images)
    TOTAL.append(extra_images)

# print TOTAL[:10]
# print len(TOTAL)
# print len(already_updated_skus)
