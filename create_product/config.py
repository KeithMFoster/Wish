from sqlalchemy import create_engine
import os


username = os.getenv("MYSQLDB_USER")
password = os.getenv("MYSQLDB_PASSWD")
host = os.getenv("MYSQLDB_HOST")

engine = create_engine("mysql://{username}:{password}@{host}/feedersettings?charset=utf8".format(
                        username=username, host=host, password=password))
connection = engine.connect()

sql = "select * from feedersettings.threshold_settings where channel = 'Wish' and storefront = 'old_glory';"
results = connection.execute(sql)
row = results.fetchone()

C1_ENABLED = row['C1_Enabled']
C1_LIMIT = row['C1_Limit']
R1_ENABLED = row['R1_Enabled']
R1_LIMIT = row['R1_Limit']

connection.close()

WISH_SHIPPING = 5.95
OG_WISH_KEY = os.getenv("OG_WISH_KEY")
AW_WISH_KEY = os.getenv("AW_WISH_KEY")

EMAILS = ['mouzaspg@gmail.com']
