import sqlite3
from contextlib import contextmanager

from app.core.config import settings


@contextmanager
def connect():
    db = sqlite3.connect(settings.database_path)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    try:
        with db:
            yield db
    finally:
        db.close()


def initialize():
    with connect() as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS tarif (
                id_tarif INTEGER PRIMARY KEY AUTOINCREMENT,
                tarif_name TEXT NOT NULL,
                internet INTEGER NOT NULL CHECK (internet >= 0),
                count_minutes INTEGER NOT NULL CHECK (count_minutes >= 0),
                count_sms INTEGER NOT NULL CHECK (count_sms >= 0),
                salary INTEGER NOT NULL CHECK (salary >= 0)
            );
            CREATE TABLE IF NOT EXISTS client (
                number_phone TEXT PRIMARY KEY,
                id_tarif INTEGER REFERENCES tarif(id_tarif) ON DELETE RESTRICT,
                lastname TEXT NOT NULL,
                firstname TEXT NOT NULL,
                patronymic_name TEXT NOT NULL DEFAULT '',
                date_birthday TEXT NOT NULL,
                pasport_serial TEXT NOT NULL,
                pasport_number TEXT NOT NULL,
                date_issue TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS client_tarif ON client(id_tarif);
        """)
