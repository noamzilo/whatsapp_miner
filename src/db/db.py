from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from contextlib import contextmanager
from src.env_var_injection import database_url

engine = create_engine(database_url)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

@contextmanager
def get_db_session():
    """Context manager for database sessions."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()