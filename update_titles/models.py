from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine, Integer, Column, String, ForeignKey, DateTime, Boolean, Float
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime


engine = create_engine('mysql://{username}:{password}@{host}/redrocket?charset=utf8', echo=False)
Base = declarative_base()
Session = sessionmaker(bind=engine)

class WishTracking(Base):
    __tablename__ = 'product_tracking_wish'

    recnum = Column(Integer, primary_key=True)
    sku = Column(String, ForeignKey('producttable.sku') )
    wish_quantity = Column(Integer)
    wishsku = Column(String)
    wishid = Column(String)
    wishparentsku = Column(String)
    wishtitle = Column(String)
    on_wish = Column(Integer)

class Product(Base):
    __tablename__ = 'producttable'

    description_moddatetime = Column(DateTime)
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

if __name__ == '__main__':
    s = Session()
    q = s.query(Product).with_entities(Product.sku, HippieTracking.qty).join(HippieTracking).filter(Product.quantity == HippieTracking.qty )
    results = q.all()
    result = results[0].qty

    print 'results -------------------------------------->>>', result
