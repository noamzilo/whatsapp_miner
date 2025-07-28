from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from src.env_var_injection import database_url

engine = create_engine(database_url)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()