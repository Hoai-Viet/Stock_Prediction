import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from pathlib import Path

# Shared configuration for projects under D:\antigravity\stock_project.
load_dotenv(Path(__file__).parents[3] / ".env")

DB_URL = (
    f"postgresql+psycopg2://"
    f"{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
    f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}"
    f"/{os.getenv('DB_NAME')}"
)

engine = create_engine(DB_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

DWH = os.getenv("DB_SCHEMA_DWH", "dwh")
STAGING = os.getenv("DB_SCHEMA_STAGING", "staging")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
