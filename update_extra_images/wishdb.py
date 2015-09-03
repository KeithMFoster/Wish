import MySQLdb
from secret import DATABASE


class WishDB(object):
    def __init__(self):
        self.connection = MySQLdb.Connect(db='redrocket', host=DATABASE['host'], user=DATABASE['username'], passwd=DATABASE['password'])
