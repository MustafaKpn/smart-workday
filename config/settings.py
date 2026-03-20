# app/config/settings.py
import os

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://jobuser:jobpass@localhost:5432/jobsdb"
)