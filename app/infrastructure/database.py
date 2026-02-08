from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 1. Database URL (Replace with your actual path)
# For SQLite (local file):
SQLALCHEMY_DATABASE_URL = "sqlite:///./sql_app.db"
# For PostgreSQL:
# SQLALCHEMY_DATABASE_URL = "postgresql://user:password@postgresserver/db"

# 2. Create the Engine
# check_same_thread=False is ONLY needed for SQLite
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

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