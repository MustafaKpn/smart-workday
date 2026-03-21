# reset_db.py
from app.config import engine
from app.storage.db import metadata

# Drop all tables
metadata.drop_all(engine)

# Recreate tables
metadata.create_all(engine)

print("All tables dropped and recreated.")