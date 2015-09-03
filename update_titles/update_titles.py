import datetime
import pickle
import requests
from models import Product, WishTracking, Session
from config import API


def get_last_update():
    """Get the last update datetime object from the serialized file"""

    with open('last_update.pickle', 'r') as f:
        last_update = pickle.load(f)
    set_last_update()
    return last_update

def set_last_update():
    """Sets the last update date to current datetime"""

    with open('last_update.pickle', 'w') as f:
        pickle.dump(datetime.datetime.now(), f)

def update_title_on_wish(product_sku, title):
    """Updates the product title on wish"""
    key = API['key']
    url = 'https://merchant.wish.com/api/v1/product/update'
    r = requests.post(url)

def main():
    last_update = get_last_update()
    session = Session()
    products_to_update = session.query(Product).\
            filter(Product.description_moddatetime < last_update & Product.wish_tracking.on_wish > 0)
    
    for product in products_to_update.all():
        wishid, title = product.wish_tracking.wishid, product.productname
        print wishid, title
        # update_title_on_wish(sku, title)

if __name__ == '__main__':
    main()
