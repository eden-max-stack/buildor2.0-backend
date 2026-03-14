from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from dotenv import load_dotenv

# 1. Database URL Configuration
# Use environment variable for production (Supabase PostgreSQL)
# Falls back to SQLite for local development
_base_dir = Path(__file__).resolve().parents[2]
load_dotenv(_base_dir / ".env.local")
load_dotenv(_base_dir / ".env")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./sql_app.db"  # Default for local development
)

# For Supabase PostgreSQL, set DATABASE_URL environment variable:
# DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@[YOUR-PROJECT-REF].supabase.co:5432/postgres

# 2. Create the Engine
# check_same_thread=False is ONLY needed for SQLite
connect_args = {}
engine_kwargs = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
elif DATABASE_URL.startswith("postgres"):
    # Supabase requires SSL for direct Postgres connections.
    # Add short timeouts so failures surface quickly.
    # statement_timeout prevents a single slow query from hanging forever.
    connect_args = {
        "sslmode": "require",
        "connect_timeout": 10,
        "options": "-c statement_timeout=15000",
    }
    engine_kwargs = {
        "pool_pre_ping": True,
        "pool_recycle": 1800,
        "pool_size": 5,
        "max_overflow": 10,
        "pool_timeout": 10,
    }

engine = create_engine(DATABASE_URL, connect_args=connect_args, **engine_kwargs)

def get_database_url_redacted() -> str:
    try:
        parts = urlsplit(DATABASE_URL)
        if not parts.scheme:
            return ""

        netloc = parts.netloc
        if "@" in netloc:
            userinfo, hostinfo = netloc.split("@", 1)
            if ":" in userinfo:
                user = userinfo.split(":", 1)[0]
                userinfo = f"{user}:***"
            netloc = f"{userinfo}@{hostinfo}"

        return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))
    except Exception:
        return ""

# 3. Create the SessionLocal class
# This is what you actually use to talk to the DB
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 4. Create the Base class
# This is the "Base" your Question model is importing!
Base = declarative_base()

# 5. Dependency (Helper function to get DB session)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()