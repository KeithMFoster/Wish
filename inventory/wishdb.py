import os
import MySQLdb

host = os.get("MYSQLDB_HOST")
user = os.get("MYSQLDB_USER")
passwd = os.get("MYSQLDB_PASSWD")

class WishDB(object):
    def __init__(self):
        self.connection = MySQLdb.Connect(host=host, user=user,
                passwd=passwd, db='redrocket')
