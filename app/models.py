from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, ForeignKey
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

class Submission(Base):
    __tablename__ = "submissions"
    
    id = Column(Integer, primary_key=True, index=True)
    submission_number = Column(String, unique=True, index=True)
    customer_name = Column(String)
    submission_date = Column(DateTime, default=datetime.utcnow)
    status = Column(String)  # "pending", "approved", "rejected"
    total_amount = Column(Float)

class Claim(Base):
    __tablename__ = "claims"
    
    id = Column(Integer, primary_key=True, index=True)
    claim_number = Column(String, unique=True, index=True)
    submission_id = Column(Integer, ForeignKey("submissions.id"))
    claim_date = Column(DateTime, default=datetime.utcnow)
    claim_type = Column(String)  # "medical", "dental", "vision"
    amount = Column(Float)
    status = Column(String)  # "pending", "approved", "denied"
    description = Column(String)

