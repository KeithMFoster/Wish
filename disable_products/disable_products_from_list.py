import os
import sys
import requests


if __name__ == "__main__":
    storefront = sys.argv[1]
    fname = sys.argv[2]

    if storefront.lower() == 'old_glory':

        key = os.environ.get("OG_WISH_KEY")
    elif storefront.lower() == 'animalworld':
        key = os.environ.get("AW_WISH_KEY")

    with open(fname, "r") as f:
        skus = f.read().split("\n")

    url = "https://merchant.wish.com/api/v1/variant/disable"
    print key, url, fname
    for sku in skus:
        r = requests.post(url, data={'key': key, 'sku': sku})
        if r.status_code == 400:
            print r.text
        else:
            print r.status_code

