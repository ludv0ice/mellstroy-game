import argparse
import getpass
import os
import sqlite3

from app.core.security import hash_password
from app.db.database import connect, initialize


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('username')
    parser.add_argument('--role', choices=['admin', 'manager'], required=True)
    parser.add_argument('--full-name', required=True)
    args = parser.parse_args()
    password = getpass.getpass('Пароль: ')
    if len(password) < 10:
        parser.error('Пароль должен содержать не менее 10 символов')
    if password != getpass.getpass('Повторите пароль: '):
        parser.error('Пароли не совпадают')
    path = os.getenv('DATABASE_PATH', 'telecom.db')
    initialize(path)
    try:
        with connect(path) as db:
            db.execute('INSERT INTO employee (username, password_hash, role, full_name) VALUES (?, ?, ?, ?)', (args.username, hash_password(password), args.role, args.full_name))
    except sqlite3.IntegrityError:
        parser.error('Такой сотрудник уже существует')
    print('Сотрудник создан')


if __name__ == '__main__':
    main()
