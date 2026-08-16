"""SQLAlchemy engine and session configuration."""

from collections.abc import Callable

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""


def create_db_engine(database_url: str) -> Engine:
    """Create an engine configured for local SQLite or another SQLAlchemy URL."""

    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    return create_engine(database_url, connect_args=connect_args, pool_pre_ping=True)


def create_session_factory(engine: Engine) -> Callable[[], Session]:
    """Create a session factory bound to an engine."""

    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)

