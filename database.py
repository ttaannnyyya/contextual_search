# database.py
# ----------------
# This file is responsible for creating the database connection.
# We use SQLite because it is lightweight and easy to integrate
# for a backend system demo.

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# # SQLite database stored as a file inside the project

DATABASE_URL = "sqlite:///./productsv0.db"

# Create database engine
# check_same_thread=False is required for FastAPI + SQLite
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

# SessionLocal will be used to interact with the DB in APIs
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()
