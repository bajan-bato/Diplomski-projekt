"""Tanki sloj nad bazom: isti kod radi na SQLite (lokalno) i Postgresu (server).

Napomena: u SQL-u uvijek koristimo aliase malim slovima (npr. `packageId AS package_id`),
jer Postgres imena bez navodnika pretvara u mala slova, a SQLite ih vraca kako su napisana.
"""
from contextlib import contextmanager

from sqlalchemy import create_engine, text

from . import config

_engine = None


def engine():
    global _engine
    if _engine is None:
        _engine = create_engine(config.DATABASE_URL, future=True)
    return _engine


def rows(sql: str, **params) -> list[dict]:
    with engine().connect() as conn:
        return [dict(r._mapping) for r in conn.execute(text(sql), params)]


def scalar(sql: str, **params):
    with engine().connect() as conn:
        return conn.execute(text(sql), params).scalar()


@contextmanager
def transaction():
    """Sve unutar bloka se commita zajedno ili nista."""
    with engine().begin() as conn:
        yield conn


def execute(conn, sql: str, **params):
    return conn.execute(text(sql), params)


def next_id(conn, table: str, column: str) -> int:
    """ID tablice nisu autoincrement, pa sljedeci racunamo sami (pipeline je jedini pisac)."""
    return (conn.execute(text(f"SELECT COALESCE(MAX({column}), 0) + 1 FROM {table}")).scalar())
