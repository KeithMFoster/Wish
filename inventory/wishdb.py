import MySQLdb
from secret import DATABASE

class WishDB(object):
    def __init__(self):
        self.connection = MySQLdb.Connect(host=DATABASE['host'], user=DATABASE['username'],
                passwd=DATABASE['password'], db='redrocket')
