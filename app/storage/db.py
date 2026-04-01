from sqlalchemy import MetaData, Table, Column, Integer, String, Text, Float, ForeignKey, DateTime
from app.config import engine

metadata = MetaData()

raw_jobs = Table(
    "raw_jobs",
    metadata,
    Column("id", Integer, primary_key=True, unique=True),
    Column("title", String),
    Column("company", String),
    Column("url", String, unique=True, nullable=False),
    Column("location", String),
    Column("status", String, default="pending"),
    Column("processed_at", DateTime)
)

parsed_jobs = Table(
    "parsed_jobs",
    metadata,
    Column("id", Integer, ForeignKey("raw_jobs.id"), primary_key=True),
    Column("reasoning", Text),
    Column("score", Float),
    Column("created_at", DateTime)
)


if __name__ == "__main__":
    metadata.create_all(engine)