import MySQLdb
from database_settings import MYSQL_DATABASE, MYSQL_PASSWORD, MYSQL_USERNAME, DATABASE_NAME
from secret import DATABASE

class WishDB(object):
    def __init__(self):
        self.connection = MySQLdb.Connect(host=DATABASE['host'], user=DATABASE['username'],
                        passwd=DATABASE['password'], db='redrocket')
