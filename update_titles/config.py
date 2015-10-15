from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, String, Integer, Float, Column
from secret import DATABASE


engine = create_engine('mysql://{username}:{password}@{host}/feedersettings', echo=False)
Base = declarative_base()
Session = sessionmaker(bind=engine)

class Wish(Base):
    __tablename__ = 'wish'
    recnum = Column(Integer, primary_key=True)
    storefront = Column(String)
    standard_shipping = Column(Float)
    api_key = Column(String)

session = Session()
settings = session.query(Wish).filter_by(storefront='old_glory').one()
session.close()






API = {
    'key': settings.api_key,
    }
