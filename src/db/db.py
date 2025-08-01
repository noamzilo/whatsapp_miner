from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from contextlib import contextmanager
from src.env_var_injection import database_url

# Lazy initialization to prevent real database connection during tests
_engine = None
_SessionLocal = None

def get_engine():
    """Get the database engine, creating it if necessary."""
    global _engine
    if _engine is None:
        _engine = create_engine(database_url)
    return _engine

def get_session_local():
    """Get the session factory, creating it if necessary."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine())
    return _SessionLocal

Base = declarative_base()

@contextmanager
def get_db_session():
    """Context manager for database sessions."""
    session = get_session_local()()
    try:
        yield session
    finally:
        session.close()