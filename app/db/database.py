import sqlite3
from pathlib import Path

from fastapi import Request


def connect(path):
    db = sqlite3.connect(path, timeout=10, check_same_thread=False)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys = ON')
    return db


def initialize(path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with connect(path) as db:
        db.executescript('''
            CREATE TABLE IF NOT EXISTS tarif (
                id_tarif INTEGER PRIMARY KEY AUTOINCREMENT,
                tarif_name TEXT NOT NULL UNIQUE,
                internet INTEGER NOT NULL CHECK(internet BETWEEN 0 AND 100000),
                count_minutes INTEGER NOT NULL CHECK(count_minutes BETWEEN 0 AND 10000),
                count_sms INTEGER NOT NULL CHECK(count_sms BETWEEN 0 AND 10000),
                salary INTEGER NOT NULL CHECK(salary BETWEEN 0 AND 100000000)
            );
            CREATE TABLE IF NOT EXISTS client (
                number_phone TEXT PRIMARY KEY,
                id_tarif INTEGER REFERENCES tarif(id_tarif) ON DELETE RESTRICT,
                lastname TEXT NOT NULL,
                firstname TEXT NOT NULL,
                patronymic_name TEXT NOT NULL,
                date_birthday TEXT NOT NULL,
                pasport_serial TEXT NOT NULL,
                pasport_number TEXT NOT NULL,
                date_issue TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS client_tarif_idx ON client(id_tarif);
            CREATE TABLE IF NOT EXISTS employee (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('manager', 'admin')),
                full_name TEXT NOT NULL
            );
        ''')


def get_db(request: Request):
    db = connect(request.app.state.database_path)
    try:
        yield db
    finally:
        db.close()
