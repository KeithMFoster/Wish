from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine, Integer, Column, String, ForeignKey, DateTime, Boolean, Float
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from secret import DATABASE


engine = create_engine("mysql://{username}:{password}@{host}/redrocket?charset=utf8".format(
                        username=DATABASE['username'], host=DATABASE['host'], password=DATABASE['password']))
Base = declarative_base()
Session = sessionmaker(bind=engine)

class WishTracking(Base):
    __tablename__ = 'product_tracking_wish'

    sku = Column(String, ForeignKey('producttable.sku'), primary_key=True )
    wish_quantity = Column(Integer)
    wishsku = Column(String)
    wishid = Column(String)
    wishparentsku = Column(String)
    wishtitle = Column(String)
    on_wish = Column(Integer)

class Product(Base):
    __tablename__ = 'producttable'

    sku = Column(String, primary_key=True)
    parentsku = Column(String)
    quantity = Column(Integer)
    productname = Column(String)
    productstatus = Column(String)
    producttype = Column(String)
    parentchild = Column(String)
    longdescription = Column(String)
    altimagecount = Column(Integer)
    brand = Column(String)
    primaryproductcategory = Column(String)

    wish_tracking = relationship("WishTracking", uselist=False, backref="producttable")
    pricing_table = relationship("Pricing", uselist=False, backref="producttable")

class Pricing(Base):
    __tablename__ = 'pricingtable'
    sku = Column(String, ForeignKey('producttable.sku'), primary_key=True )
    itemprice = Column(Float)

class WishTag(Base):
    __tablename__ = 'wishtagtable'
    primarycategory = Column(String, ForeignKey('producttable.primaryproductcategory'), primary_key=True)
    tag_2 = Column(String)
    tag_3 = Column(String)
    tag_4 = Column(String)
    tag_5 = Column(String)
    tag_6 = Column(String)
    tag_7 = Column(String)
    tag_8 = Column(String)
    tag_9 = Column(String)



    def get_tags(self):
        tags = [self.tag_2, self.tag_3, self.tag_4, self.tag_5,
                self.tag_6, self.tag_7, self.tag_8, self.tag_9]
        if not all(tags):
            return None
        return tags

class Exempt(Base):
    __tablename__ = 'exempttable'
    recnum = Column(Integer, primary_key=True)
    sku = Column(String)
    wish = Column(Integer)

if __name__ == '__main__':
    s = Session()
    q = s.query(Product).with_entities(Product.sku, HippieTracking.qty).join(HippieTracking).filter(Product.quantity == HippieTracking.qty )
    results = q.all()
    result = results[0].qty

    print 'results -------------------------------------->>>', result
