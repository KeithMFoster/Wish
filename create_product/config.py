from sqlalchemy import create_engine
from secret import DATABASE

engine = create_engine("mysql://{username}:{password}@{host}/feedersettings?charset=utf8".format(
                        username=DATABASE['username'], host=DATABASE['host'], password=DATABASE['password']))
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
WISH_KEY = "JHBia2RmMiQxMDAkTjRid1BrY0lvYlQydnRkNnI1VlNTZyRwWWFqVlk3Qy9TRFpURlUwTHpHWGt1eEtZZTg="