# models.py
# -----------
# This file defines database tables using SQLAlchemy ORM.
# These tables store product information and learning signals
# like clicks, add-to-cart, and purchases.

from sqlalchemy import Column, Integer, String, Float
from sqlalchemy.ext.declarative import declarative_base

# Base class for all database models
Base = declarative_base()

class Product(Base):
    """
    Product table:
    Stores structured product data + user interaction counters.
    This table is used for filtering, ranking, and learning.
    """

    __tablename__ = "products"

    # Internal primary key
    id = Column(Integer, primary_key=True, index=True)

    # Public product ID from CSV / JSON
    product_id = Column(String, unique=True, index=True)

   # Normalized product fields
    title = Column(String)
    description = Column(String)
    category = Column(String)
    brand = Column(String)

# Structured attributes used for filtering
    price = Column(Float)
    size = Column(String)
    color = Column(String)
    rating = Column(Float)

 
    # Behavioral signals (used for ranking improvement)
    click_count = Column(Integer, default=0)
    add_to_cart_count = Column(Integer, default=0)
    purchase_count = Column(Integer, default=0)



