# Models Directory

## Purpose
SQLAlchemy ORM declarative models. Each class maps to one database table and is used for ORM operations.

## What lives here
- `base.py` – `Base = declarative_base()` import point  
- `user.py` – `User` table definition  
- `post.py` – `Post` table definition  
- `category.py` – `Category` table definition  
- Database entity definitions, relationships, constraints, and indexes

## Usage
```python
from models.user import User
from database import SessionLocal

db = SessionLocal()
users = db.query(User).all()
```

## Rules / Best practices
- Each model class should inherit from `Base` (SQLAlchemy declarative base).  
- Use `__tablename__` to specify the actual table name.  
- Define columns using SQLAlchemy types (Column, Integer, String, etc.).  
- Include relationships for foreign key connections and add indexes for frequently queried columns.  
- Never expose model objects directly in API responses — use `schemas/` (Pydantic/serializers) to shape client-facing data.  
- Keep sensitive columns (`hashed_password`, `api_key`, etc.) only in models and never return them in responses.

## Example model
```python
# models/user.py
from sqlalchemy import Column, Integer, String
from .base import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
```
