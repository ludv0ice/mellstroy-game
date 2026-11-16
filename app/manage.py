import argparse
import getpass
from sqlalchemy.exc import IntegrityError

from app.core import config
from app.core.security import hash_password
from app.db.database import connect, initialize
from app.models.entities import Employee


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
    initialize(config.DATABASE_PATH)
    try:
        with connect(config.DATABASE_PATH) as db, db.begin():
            db.add(Employee(username=args.username, password_hash=hash_password(password), role=args.role, full_name=args.full_name))
    except IntegrityError:
        parser.error('Такой сотрудник уже существует')
    print('Сотрудник создан')


if __name__ == '__main__':
    main()
