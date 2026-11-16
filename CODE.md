# Исходный код по структуре проекта

## `app/controllers/auth.py`

```python
from fastapi import APIRouter, Depends, HTTPException, Request

from app.core.security import current_user, issue_token, verify_password
from app.db.database import get_db
from app.models.schemas import Login, TokenOut, UserOut

router = APIRouter(prefix='/auth', tags=['Авторизация'])


@router.post('/login', response_model=TokenOut)
def login(body: Login, request: Request, db=Depends(get_db)):
    user = db.execute('SELECT * FROM employee WHERE username = ?', (body.username,)).fetchone()
    encoded = user['password_hash'] if user else request.app.state.dummy_password
    valid = verify_password(body.password, encoded)
    if user is None or not valid:
        raise HTTPException(401, 'Неверный логин или пароль', headers={'WWW-Authenticate': 'Bearer'})
    return {'access_token': issue_token(user['id'], request.app.state.secret), 'role': user['role']}


@router.get('/me', response_model=UserOut)
def me(user=Depends(current_user)):
    return user
```

## `app/controllers/clients.py`

```python
from datetime import date
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response

from app.core.security import admin, staff
from app.db.database import get_db
from app.models.schemas import ClientCreate, ClientOut, ClientPage, ClientPatch, Phone, PositiveId
from app.services.telecom import clients, ensure_tarif, get_client, insert, update_client

router = APIRouter(prefix='/clients', tags=['Клиенты'], dependencies=[Depends(staff)])


@router.get('', response_model=ClientPage)
def list_clients(limit: Annotated[int, Query(ge=1, le=100)] = 20, offset: Annotated[int, Query(ge=0)] = 0, tarif_id: PositiveId | None = None, db=Depends(get_db)):
    where = 'WHERE id_tarif = ?' if tarif_id is not None else ''
    params = (tarif_id,) if tarif_id is not None else ()
    total = db.execute(f'SELECT COUNT(*) FROM client {where}', params).fetchone()[0]
    items = clients(db, where, (*params, limit, offset), 'ORDER BY number_phone LIMIT ? OFFSET ?')
    return {'total': total, 'limit': limit, 'offset': offset, 'items': items}


@router.post('', status_code=201, response_model=ClientOut)
def create_client(body: ClientCreate, db=Depends(get_db)):
    ensure_tarif(db, body.id_tarif)
    insert(db, 'client', body.model_dump(mode='json'))
    return get_client(db, body.number_phone)


@router.get('/search/phone', response_model=list[ClientOut])
def search_phone(phone: Annotated[str, Query(pattern=r'^(\+7|8)[0-9]{0,10}$')], db=Depends(get_db)):
    return clients(db, 'WHERE number_phone LIKE ?', (phone + '%',))


@router.get('/sorted-by-birthday')
def sorted_birthday(db=Depends(get_db)):
    rows = db.execute('SELECT lastname, firstname, patronymic_name, date_birthday FROM client ORDER BY date_birthday, number_phone')
    return [{'full_name': ' '.join(filter(None, [r['lastname'], r['firstname'], r['patronymic_name']])), 'date_birthday': r['date_birthday']} for r in rows]


@router.get('/search/passport-year', response_model=list[ClientOut])
def passport_year(year: Annotated[int, Query(ge=1900, le=date.today().year)], db=Depends(get_db)):
    return clients(db, 'WHERE date_issue > ?', (f'{year:04d}-12-31',))


@router.get('/search/tarif-cost', response_model=list[ClientOut])
def tarif_cost(minSalary: Annotated[Decimal, Query(ge=0)], db=Depends(get_db)):
    return clients(db, 'WHERE id_tarif IN (SELECT id_tarif FROM tarif WHERE salary > ?)', (str(minSalary * 100),))


@router.patch('/tarif', response_model=ClientOut)
def change_tarif(phone: Phone, id_tarif: PositiveId, db=Depends(get_db)):
    return update_client(db, phone, ClientPatch(id_tarif=id_tarif))


@router.get('/{phone}', response_model=ClientOut)
def client_card(phone: Phone, db=Depends(get_db)):
    return get_client(db, phone)


@router.patch('/{phone}', response_model=ClientOut)
def patch_client(phone: Phone, body: ClientPatch, db=Depends(get_db)):
    return update_client(db, phone, body)


@router.delete('/{phone}', status_code=204, dependencies=[Depends(admin)])
def delete_client(phone: Phone, db=Depends(get_db)):
    get_client(db, phone)
    with db:
        db.execute('DELETE FROM client WHERE number_phone = ?', (phone,))
    return Response(status_code=204)
```

## `app/controllers/tarifs.py`

```python
from fastapi import APIRouter, Depends, HTTPException, Response

from app.core.security import admin, staff
from app.db.database import get_db
from app.models.schemas import Phone, PositiveId, TarifCount, TarifCreate, TarifOut, TarifPatch
from app.services.telecom import get_client, get_tarif, insert, tarif_out, update, values

router = APIRouter(prefix='/tarifs', tags=['Тарифы'])


def counts(db):
    return db.execute('SELECT t.*, COUNT(c.number_phone) AS client_count FROM tarif t LEFT JOIN client c ON c.id_tarif = t.id_tarif GROUP BY t.id_tarif ORDER BY t.id_tarif').fetchall()


@router.get('', response_model=list[TarifOut])
def list_tarifs(db=Depends(get_db)):
    return [tarif_out(row) for row in db.execute('SELECT * FROM tarif ORDER BY id_tarif')]


@router.get('/by-client/{phone}', response_model=TarifOut, dependencies=[Depends(staff)])
def by_client(phone: Phone, db=Depends(get_db)):
    tarif = get_client(db, phone)['tarif']
    if tarif is None:
        raise HTTPException(404, 'У клиента не подключен тариф')
    return tarif


@router.get('/stats/client-count')
def stats(db=Depends(get_db)):
    return [{'tarif_name': row['tarif_name'], 'client_count': row['client_count']} for row in counts(db)]


@router.get('/with-client-count', response_model=list[TarifCount], dependencies=[Depends(staff)])
def with_counts(db=Depends(get_db)):
    return [tarif_out(row) for row in counts(db)]


@router.get('/{id_tarif}/client-count', dependencies=[Depends(staff)])
def client_count(id_tarif: PositiveId, db=Depends(get_db)):
    get_tarif(db, id_tarif)
    count = db.execute('SELECT COUNT(*) FROM client WHERE id_tarif = ?', (id_tarif,)).fetchone()[0]
    return {'tarif_id': id_tarif, 'count': count}


@router.post('', status_code=201, response_model=TarifOut, dependencies=[Depends(admin)])
def create_tarif(body: TarifCreate, db=Depends(get_db)):
    return get_tarif(db, insert(db, 'tarif', values(body)))


@router.patch('/{id_tarif}', response_model=TarifOut, dependencies=[Depends(admin)])
def patch_tarif(id_tarif: PositiveId, body: TarifPatch, db=Depends(get_db)):
    get_tarif(db, id_tarif)
    update(db, 'tarif', 'id_tarif', id_tarif, values(body))
    return get_tarif(db, id_tarif)


@router.delete('/{id_tarif}', status_code=204, dependencies=[Depends(admin)])
def delete_tarif(id_tarif: PositiveId, db=Depends(get_db)):
    get_tarif(db, id_tarif)
    if db.execute('SELECT 1 FROM client WHERE id_tarif = ?', (id_tarif,)).fetchone():
        raise HTTPException(409, 'Тариф подключен клиентам: сначала смените или снимите тариф')
    with db:
        db.execute('DELETE FROM tarif WHERE id_tarif = ?', (id_tarif,))
    return Response(status_code=204)
```

## `app/core/security.py`

```python
import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.db.database import get_db

bearer = HTTPBearer(auto_error=False)


def hash_password(password):
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 600000).hex()
    return f'{salt}${digest}'


def verify_password(password, encoded):
    salt, expected = encoded.split('$')
    actual = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 600000).hex()
    return hmac.compare_digest(actual, expected)


def encode(data):
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode()


def issue_token(user_id, secret):
    header = encode(b'{"alg":"HS256","typ":"JWT"}')
    payload = encode(json.dumps({'sub': str(user_id), 'exp': int(time.time()) + 3600}).encode())
    message = f'{header}.{payload}'
    signature = encode(hmac.digest(secret.encode(), message.encode(), 'sha256'))
    return f'{message}.{signature}'


def current_user(request: Request, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)], db=Depends(get_db)):
    error = HTTPException(401, 'Учетные данные не были предоставлены', headers={'WWW-Authenticate': 'Bearer'})
    if credentials is None:
        raise error
    try:
        header, payload, signature = credentials.credentials.split('.')
        expected = encode(hmac.digest(request.app.state.secret.encode(), f'{header}.{payload}'.encode(), 'sha256'))
        if not hmac.compare_digest(signature, expected):
            raise ValueError
        if json.loads(base64.urlsafe_b64decode(header + '=' * (-len(header) % 4))) != {'alg': 'HS256', 'typ': 'JWT'}:
            raise ValueError
        claims = json.loads(base64.urlsafe_b64decode(payload + '=' * (-len(payload) % 4)))
        if claims['exp'] <= time.time():
            raise ValueError
        user = db.execute('SELECT id, username, role, full_name FROM employee WHERE id = ?', (int(claims['sub']),)).fetchone()
        if user is None:
            raise ValueError
        return dict(user)
    except (ValueError, KeyError, TypeError, OverflowError):
        raise error


def require_roles(*roles):
    def dependency(user=Depends(current_user)):
        if user['role'] not in roles:
            raise HTTPException(403, 'У вас недостаточно прав для выполнения операции')
        return user
    return dependency


staff = require_roles('manager', 'admin')
admin = require_roles('admin')
```

## `app/db/database.py`

```python
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
```

## `app/main.py`

```python
import os
import secrets
import sqlite3
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.controllers import auth, clients, tarifs
from app.core.security import hash_password
from app.db.database import initialize


def create_app(database_path=None, secret=None):
    @asynccontextmanager
    async def lifespan(app):
        initialize(app.state.database_path)
        yield

    app = FastAPI(title='Управление клиентами и тарифами', version='2.0', docs_url='/api/v1/docs', redoc_url='/api/v1/redoc', openapi_url='/api/v1/openapi.json', lifespan=lifespan)
    app.state.database_path = database_path or os.getenv('DATABASE_PATH', 'telecom.db')
    app.state.secret = secret or os.getenv('JWT_SECRET') or secrets.token_urlsafe(48)
    app.state.dummy_password = hash_password(secrets.token_urlsafe(32))

    @app.exception_handler(sqlite3.IntegrityError)
    async def integrity_error(request: Request, error):
        message = str(error)
        if 'client.number_phone' in message:
            detail = 'Клиент с таким номером телефона уже существует'
        elif 'tarif.tarif_name' in message:
            detail = 'Тариф с таким названием уже существует'
        elif 'FOREIGN KEY' in message:
            detail = 'Операция нарушает связь клиента с тарифом'
        else:
            detail = 'Данные конфликтуют с существующей записью'
        return JSONResponse(status_code=409, content={'detail': detail})

    for router in (auth.router, tarifs.router, clients.router):
        app.include_router(router, prefix='/api/v1')
    return app


app = create_app()
```

## `app/manage.py`

```python
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
```

## `app/models/schemas.py`

```python
from datetime import date
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_core import PydanticCustomError

Phone = Annotated[str, Field(pattern=r'^(\+7|8)[0-9]{10}$')]
PositiveId = Annotated[int, Field(gt=0)]
Money = Annotated[Decimal, Field(ge=0, le=1000000, max_digits=9, decimal_places=2)]


class Schema(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)


class TarifCreate(Schema):
    tarif_name: str = Field(min_length=2, max_length=100)
    internet: int = Field(ge=0, le=100000, strict=True)
    count_minutes: int = Field(ge=0, le=10000, strict=True)
    count_sms: int = Field(ge=0, le=10000, strict=True)
    salary: Money


class TarifPatch(TarifCreate):
    tarif_name: str = Field(default=None, min_length=2, max_length=100)
    internet: int = Field(default=None, ge=0, le=100000, strict=True)
    count_minutes: int = Field(default=None, ge=0, le=10000, strict=True)
    count_sms: int = Field(default=None, ge=0, le=10000, strict=True)
    salary: Money = None


class TarifOut(TarifCreate):
    id_tarif: int
    salary: float


class TarifCount(TarifOut):
    client_count: int


class ClientCreate(Schema):
    number_phone: Phone
    id_tarif: PositiveId | None = None
    lastname: str
    firstname: str
    patronymic_name: str = ''
    date_birthday: date
    pasport_serial: str = Field(pattern=r'^[0-9]{4}$')
    pasport_number: str = Field(pattern=r'^[0-9]{6}$')
    date_issue: date

    @field_validator('lastname', 'firstname', 'patronymic_name')
    @classmethod
    def validate_name(cls, value, info):
        if info.field_name == 'patronymic_name' and value == '':
            return value
        if not 2 <= len(value) <= 50 or not all(c.isalpha() or c == '-' for c in value) or not any(c.isalpha() for c in value):
            raise PydanticCustomError('value_error.name_format', 'Имя должно содержать от 2 до 50 символов: буквы и дефис')
        return value

    @field_validator('date_birthday')
    @classmethod
    def validate_birthday(cls, value):
        today = date.today()
        age = today.year - value.year - ((today.month, today.day) < (value.month, value.day))
        if value > today or not 18 <= age <= 120:
            raise PydanticCustomError('value_error.age_range', 'Возраст клиента должен быть от 18 до 120 лет')
        return value

    @field_validator('date_issue')
    @classmethod
    def validate_issue(cls, value):
        if value > date.today():
            raise PydanticCustomError('value_error.date_future', 'Дата выдачи паспорта не может быть в будущем')
        return value

    @model_validator(mode='after')
    def validate_dates(self):
        if self.date_issue is not None and self.date_birthday is not None and self.date_issue < self.date_birthday:
            raise PydanticCustomError('value_error.date_order', 'Дата выдачи паспорта не может быть раньше даты рождения')
        return self


class ClientPatch(ClientCreate):
    number_phone: Phone = None
    lastname: str = None
    firstname: str = None
    date_birthday: date = None
    pasport_serial: str = Field(default=None, pattern=r'^[0-9]{4}$')
    pasport_number: str = Field(default=None, pattern=r'^[0-9]{6}$')
    date_issue: date = None


class ClientOut(ClientCreate):
    tarif: TarifOut | None


class ClientPage(Schema):
    total: int
    limit: int
    offset: int
    items: list[ClientOut]


class Login(Schema):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=200)


class UserOut(Schema):
    id: int
    username: str
    role: str
    full_name: str


class TokenOut(Schema):
    access_token: str
    token_type: str = 'bearer'
    role: str
```

## `app/services/telecom.py`

```python
from decimal import Decimal

from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from app.models.schemas import ClientCreate


def tarif_out(row):
    result = dict(row)
    result['salary'] = result['salary'] / 100
    return result


def get_tarif(db, tarif_id):
    row = db.execute('SELECT * FROM tarif WHERE id_tarif = ?', (tarif_id,)).fetchone()
    if row is None:
        raise HTTPException(404, 'Тариф не найден')
    return tarif_out(row)


def get_client(db, phone):
    row = db.execute('SELECT * FROM client WHERE number_phone = ?', (phone,)).fetchone()
    if row is None:
        raise HTTPException(404, 'Клиент с таким номером телефона не найден')
    result = dict(row)
    result['tarif'] = get_tarif(db, result['id_tarif']) if result['id_tarif'] is not None else None
    return result


def clients(db, where='', params=(), suffix='ORDER BY number_phone'):
    rows = db.execute(f'SELECT number_phone FROM client {where} {suffix}', params).fetchall()
    return [get_client(db, row['number_phone']) for row in rows]


def ensure_tarif(db, tarif_id):
    if tarif_id is not None and db.execute('SELECT 1 FROM tarif WHERE id_tarif = ?', (tarif_id,)).fetchone() is None:
        raise HTTPException(422, [{'loc': ['body', 'id_tarif'], 'msg': 'Тариф должен существовать', 'type': 'value_error.tarif_not_found'}])


def values(model):
    result = model.model_dump(mode='json', exclude_unset=True)
    if 'salary' in result:
        result['salary'] = int(Decimal(str(result['salary'])) * 100)
    return result


def insert(db, table, data):
    columns = ', '.join(data)
    marks = ', '.join('?' for _ in data)
    with db:
        cursor = db.execute(f'INSERT INTO {table} ({columns}) VALUES ({marks})', tuple(data.values()))
    return cursor.lastrowid


def update(db, table, key, identifier, data):
    if not data:
        raise HTTPException(422, 'Передайте хотя бы одно поле для обновления')
    assignments = ', '.join(f'{name} = ?' for name in data)
    with db:
        db.execute(f'UPDATE {table} SET {assignments} WHERE {key} = ?', (*data.values(), identifier))


def update_client(db, phone, patch):
    existing = get_client(db, phone)
    existing.pop('tarif')
    data = patch.model_dump(mode='json', exclude_unset=True)
    try:
        ClientCreate.model_validate(existing | data)
    except ValidationError as error:
        raise RequestValidationError([{**item, 'loc': ('body', *item['loc'])} for item in error.errors()])
    ensure_tarif(db, data.get('id_tarif'))
    update(db, 'client', 'number_phone', phone, data)
    return get_client(db, data.get('number_phone', phone))
```

## `tests/test_api.py`

```python
import tempfile
import unittest
from datetime import date
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.security import hash_password
from app.db.database import connect
from app.main import create_app


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.password_hash = hash_password('test-password')

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = str(Path(self.temp.name) / 'test.db')
        self.client = TestClient(create_app(self.path, 'test-secret'))
        self.client.__enter__()
        with connect(self.path) as db:
            for role in ('admin', 'manager'):
                db.execute('INSERT INTO employee (username, password_hash, role, full_name) VALUES (?, ?, ?, ?)', (role, self.password_hash, role, 'Тестовый Сотрудник'))
        self.tokens = {}
        for role in ('admin', 'manager'):
            response = self.client.post('/api/v1/auth/login', json={'username': role, 'password': 'test-password'})
            self.assertEqual(response.status_code, 200, response.text)
            self.tokens[role] = {'Authorization': 'Bearer ' + response.json()['access_token']}
        self.tarif = {'tarif_name': 'Основной', 'internet': 50, 'count_minutes': 500, 'count_sms': 100, 'salary': 600.25}
        self.person = {'number_phone': '+79001234567', 'lastname': 'Иванов', 'firstname': 'Иван', 'patronymic_name': 'Иванович', 'date_birthday': '1990-05-15', 'pasport_serial': '0012', 'pasport_number': '003456', 'date_issue': '2015-08-20'}

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self.temp.cleanup()

    def call(self, method, path, expected=200, role='manager', **kwargs):
        r = self.client.request(method, '/api/v1' + path, headers=self.tokens.get(role, {}), **kwargs)
        self.assertEqual(r.status_code, expected, r.text)
        return r.json() if r.content else None

    def seed(self):
        self.call('POST', '/tarifs', 201, 'admin', json=self.tarif)
        self.call('POST', '/clients', 201, json=self.person | {'id_tarif': 1})

    def test_auth(self):
        self.call('GET', '/auth/me', 401, None)
        self.assertEqual(self.call('GET', '/auth/me')['role'], 'manager')
        self.call('POST', '/auth/login', 401, None, json={'username': 'admin', 'password': 'bad'})
        self.call('POST', '/auth/login', 401, None, json={'username': 'unknown', 'password': 'bad'})
        for token in ('garbage', 'a.b.c', self.tokens['admin']['Authorization'][7:-1] + '!'):
            self.assertEqual(self.client.get('/api/v1/auth/me', headers={'Authorization': 'Bearer ' + token}).status_code, 401)

    def test_roles(self):
        self.seed()
        for url in ('/tarifs', '/tarifs/stats/client-count'):
            self.call('GET', url, role=None)
        for url in ('/clients', '/clients/sorted-by-birthday', '/tarifs/with-client-count', '/tarifs/1/client-count', '/tarifs/by-client/%2B79001234567'):
            self.call('GET', url, 401, None)
        self.call('POST', '/tarifs', 403, json=self.tarif)
        self.call('PATCH', '/tarifs/1', 403, json={'salary': 1})
        self.call('DELETE', '/tarifs/1', 403)
        self.call('DELETE', '/clients/%2B79001234567', 403)

    def test_tarif_lifecycle(self):
        self.call('POST', '/tarifs', 201, 'admin', json=self.tarif)
        updated = self.call('PATCH', '/tarifs/1', role='admin', json={'salary': 700.1})
        self.assertEqual(updated['salary'], 700.1)
        self.call('DELETE', '/tarifs/1', 204, 'admin')
        self.call('DELETE', '/tarifs/1', 404, 'admin')

    def test_tarif_validation(self):
        self.seed()
        self.call('POST', '/tarifs', 409, 'admin', json=self.tarif)
        for change in ({'tarif_name': '  '}, {'internet': -1}, {'internet': 100001}, {'internet': 1.5}, {'count_minutes': 10001}, {'count_sms': -1}, {'salary': '1.001'}, {'salary': -1}, {'salary': 1000001}, {'tarif_name': None}, {'extra': 1}, {}):
            with self.subTest(change=change):
                self.call('PATCH', '/tarifs/1', 422, 'admin', json=change)

    def test_client_lifecycle(self):
        self.call('POST', '/clients', 201, json=self.person)
        self.call('POST', '/clients', 409, json=self.person)
        url = '/clients/%2B79001234567'
        self.assertIsNone(self.call('GET', url)['tarif'])
        self.assertEqual(self.call('GET', url)['pasport_serial'], '0012')
        self.assertEqual(self.call('PATCH', url, json={'lastname': 'Петров'})['lastname'], 'Петров')
        self.call('DELETE', url, 204, 'admin')
        self.call('GET', url, 404)

    def test_client_validation(self):
        for change in ({'number_phone': '+18001234567'}, {'lastname': 'А1'}, {'firstname': '--'}, {'patronymic_name': 'X'}, {'date_birthday': date.today().isoformat()}, {'date_birthday': '1800-01-01'}, {'pasport_serial': '123'}, {'pasport_number': '12345a'}, {'date_issue': '1980-01-01'}, {'date_issue': '2999-01-01'}, {'id_tarif': 999}, {'id_tarif': -1}, {'role': 'admin'}):
            with self.subTest(change=change):
                self.call('POST', '/clients', 422, json=self.person | change)

    def test_patch_validation(self):
        self.seed()
        url = '/clients/%2B79001234567'
        for patch in ({'date_issue': '1980-01-01'}, {'date_birthday': '2000-01-01', 'date_issue': '1999-01-01'}, {'date_issue': None}, {'lastname': None}, {}):
            self.call('PATCH', url, 422, json=patch)
        self.assertEqual(self.call('GET', url)['date_birthday'], '1990-05-15')

    def test_assignment_and_deletion(self):
        self.seed()
        self.call('DELETE', '/tarifs/1', 409, 'admin')
        self.call('PATCH', '/clients/%2B79001234567', json={'id_tarif': None})
        self.call('GET', '/tarifs/by-client/%2B79001234567', 404)
        r = self.call('PATCH', '/clients/tarif', params={'phone': self.person['number_phone'], 'id_tarif': 1})
        self.assertEqual(r['tarif']['salary'], 600.25)
        self.call('PATCH', '/clients/tarif', 422, params={'phone': self.person['number_phone'], 'id_tarif': 999})
        self.call('PATCH', '/clients/%2B79001234567', json={'id_tarif': None})
        self.call('DELETE', '/tarifs/1', 204, 'admin')

    def test_pagination_and_statistics(self):
        self.seed()
        self.call('POST', '/tarifs', 201, 'admin', json=self.tarif | {'tarif_name': 'Пустой'})
        self.call('POST', '/clients', 201, json=self.person | {'number_phone': '89001234568'})
        page = self.call('GET', '/clients', params={'limit': 1, 'offset': 1})
        self.assertEqual((page['total'], len(page['items'])), (2, 1))
        self.assertEqual(self.call('GET', '/clients', params={'tarif_id': 1})['total'], 1)
        self.assertEqual([r['client_count'] for r in self.call('GET', '/tarifs/stats/client-count', role=None)], [1, 0])
        self.assertEqual(self.call('GET', '/tarifs/1/client-count')['count'], 1)
        self.assertEqual(self.call('GET', '/tarifs/with-client-count')[1]['client_count'], 0)
        for params in ({'limit': 101}, {'limit': 0}, {'offset': -1}):
            self.call('GET', '/clients', 422, params=params)

    def test_search_and_sort(self):
        self.seed()
        self.call('POST', '/clients', 201, json=self.person | {'number_phone': '89001234568', 'date_birthday': '1980-01-01', 'date_issue': '2016-01-01'})
        self.assertEqual(len(self.call('GET', '/clients/search/phone', params={'phone': '+7'})), 1)
        self.assertEqual(self.call('GET', '/clients/sorted-by-birthday')[0]['date_birthday'], '1980-01-01')
        for year, expected in ((2014, 2), (2015, 1), (2016, 0)):
            self.assertEqual(len(self.call('GET', '/clients/search/passport-year', params={'year': year})), expected)
        for salary, expected in ((600.24, 1), (600.25, 0), (600.26, 0)):
            self.assertEqual(len(self.call('GET', '/clients/search/tarif-cost', params={'minSalary': salary})), expected)
        for url in ('/clients/search/passport-year?year=1899', '/clients/search/passport-year?year=2999', '/clients/search/tarif-cost?minSalary=-1', '/clients/bad', '/tarifs/0/client-count'):
            self.call('GET', url, 422)

    def test_persistence_and_docs(self):
        self.seed()
        with TestClient(create_app(self.path, 'test-secret')) as other:
            self.assertEqual(other.get('/api/v1/clients', headers=self.tokens['manager']).json()['total'], 1)
        self.assertEqual(self.client.get('/api/v1/docs').status_code, 200)
        schema = self.call('GET', '/openapi.json', role=None)
        self.assertIn('patch', schema['paths']['/api/v1/tarifs/{id_tarif}'])
        self.assertIn('HTTPBearer', schema['components']['securitySchemes'])


if __name__ == '__main__':
    unittest.main()
```

