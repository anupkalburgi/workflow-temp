from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime
from .database import Base
from datetime import datetime

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    age = Column(Integer)
    role = Column(String)
    is_active = Column(Boolean, default=True)
    salary = Column(Float)
    joined_at = Column(DateTime, default=datetime.utcnow)
    department = Column(String, default="Engineering")

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    category = Column(String)
    price = Column(Float)
    stock = Column(Integer)
