# app/storage/db.py
from sqlalchemy import MetaData, Table, Column, Integer, String, Text, Float, ForeignKey, BigInteger
from app.config import engine  # import the engine from config

metadata = MetaData()

# Raw jobs table
raw_jobs = Table(
    "raw_jobs",
    metadata,
    Column("id", BigInteger, primary_key=True, unique=True),
    Column("title", String),
    Column("source", String),
    Column("url", String, unique=True, nullable=False),
    Column("description", Text),
    Column("location", String),
    Column("status", String, default="pending"),  # pending, processing, done, failed
)

# Parsed jobs table
parsed_jobs = Table(
    "parsed_jobs",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("raw_job_id", Integer, ForeignKey("raw_jobs.id")),
    Column("title", String),
    Column("company", String),
    Column("location", String),
    Column("description", Text),
    Column("score", Float),
)

# Notifications table
notifications = Table(
    "notifications",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("parsed_job_id", Integer, ForeignKey("parsed_jobs.id")),
    Column("sent", Integer, default=0),
)

if __name__ == "__main__":
    metadata.create_all(engine)
    print("Tables created.")