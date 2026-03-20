# app/config/__init__.py
from .settings import DATABASE_URL   # relative import
from sqlalchemy import create_engine

engine = create_engine(DATABASE_URL, pool_pre_ping=True)