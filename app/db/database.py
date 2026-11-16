from functools import lru_cache
from pathlib import Path

from fastapi import Request
from sqlalchemy import create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.models.entities import Base


def database_url(value):
    if '://' in value:
        return value.replace('postgresql://', 'postgresql+psycopg://', 1)
    return 'sqlite:///' + value


@lru_cache(maxsize=16)
def get_engine(value):
    url = make_url(database_url(value))
    options = {'pool_pre_ping': True}
    if url.get_backend_name() == 'sqlite':
        options['connect_args'] = {'check_same_thread': False, 'timeout': 10}
        if url.database in (None, '', ':memory:'):
            options['poolclass'] = StaticPool
        else:
            Path(url.database).parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(url, **options)
    if url.get_backend_name() == 'sqlite':
        @event.listens_for(engine, 'connect')
        def enable_foreign_keys(connection, record):
            cursor = connection.cursor()
            cursor.execute('PRAGMA foreign_keys = ON')
            cursor.close()
    return engine


def connect(value):
    return Session(get_engine(value), expire_on_commit=False)


def initialize(value):
    Base.metadata.create_all(get_engine(value))


def get_db(request: Request):
    with connect(request.app.state.database_path) as session:
        try:
            yield session
        except Exception:
            session.rollback()
            raise
