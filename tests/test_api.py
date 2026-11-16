import tempfile
import hashlib
import sqlite3
import time
import unittest
from datetime import date
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.security import hash_password, verify_password, session_hash
from app.db.database import connect, get_engine
from app.main import create_app
from app.models.entities import AuthSession, Employee
from sqlalchemy import select, update, func
from sqlalchemy.orm import Session


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.password_hash = hash_password('test-password')

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = str(Path(self.temp.name) / 'test.db')
        self.client = TestClient(create_app(self.path, 'test-secret'))
        self.client.__enter__()
        with connect(self.path) as db, db.begin():
            for role in ('admin', 'manager'):
                db.add(Employee(username=role, password_hash=self.password_hash, role=role, full_name='Тестовый Сотрудник'))
        self.tokens = {}
        for role in ('admin', 'manager'):
            response = self.client.post('/api/v1/auth/login', json={'username': role, 'password': 'test-password'})
            self.assertEqual(response.status_code, 200, response.text)
            self.tokens[role] = {'Authorization': 'Bearer ' + response.json()['access_token']}
        self.client.cookies.clear()
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


    def cookie_login(self, username='admin'):
        return self.call('POST', '/auth/login', role=None, json={'username': username, 'password': 'test-password'})

    def test_argon2_passwords(self):
        self.assertTrue(self.password_hash.startswith('$argon2id$'))
        self.assertTrue(verify_password('test-password', self.password_hash))
        self.assertFalse(verify_password('wrong-password', self.password_hash))
        self.assertFalse(verify_password('test-password', 'invalid-hash'))

    def test_cookie_login_and_logout(self):
        self.cookie_login()
        token = self.client.cookies.get('telecom_session')
        self.assertIsNotNone(token)
        self.assertEqual(self.call('GET', '/auth/me', role=None)['role'], 'admin')
        response = self.client.post('/api/v1/tarifs', json=self.tarif, headers={'Origin': 'http://testserver'})
        self.assertEqual(response.status_code, 201, response.text)
        with connect(self.path) as db:
            row = db.get(AuthSession, session_hash(token))
            self.assertIsNotNone(row)
            self.assertNotEqual(row.token_hash, token)
        response = self.client.post('/api/v1/auth/logout', headers={'Origin': 'http://testserver'})
        self.assertEqual(response.status_code, 204)
        self.assertIsNone(self.client.cookies.get('telecom_session'))
        self.client.cookies.set('telecom_session', token, path='/api/v1')
        self.call('GET', '/auth/me', 401, None)

    def test_cookie_csrf_protection(self):
        self.cookie_login()
        for headers in ({}, {'Origin': 'https://evil.example'}, {'Origin': 'http://testserver', 'Sec-Fetch-Site': 'cross-site'}):
            response = self.client.post('/api/v1/tarifs', json=self.tarif, headers=headers)
            self.assertEqual(response.status_code, 403, response.text)
        self.call('GET', '/auth/me', role=None)
        self.assertEqual(self.client.post('/api/v1/auth/login', json={'username': 'admin', 'password': 'test-password'}, headers={'Origin': 'https://evil.example'}).status_code, 403)

    def test_cookie_expiry_rotation_and_persistence(self):
        self.cookie_login()
        old = self.client.cookies.get('telecom_session')
        self.cookie_login()
        new = self.client.cookies.get('telecom_session')
        self.assertNotEqual(old, new)
        with connect(self.path) as db:
            self.assertIsNone(db.get(AuthSession, session_hash(old)))
        with TestClient(create_app(self.path, 'different-secret')) as other:
            other.cookies.set('telecom_session', new, path='/api/v1')
            self.assertEqual(other.get('/api/v1/auth/me').status_code, 200)
        with connect(self.path) as db, db.begin():
            db.execute(update(AuthSession).values(expires_at=int(time.time()) - 1))
        self.call('GET', '/auth/me', 401, None)
        self.client.cookies.clear()
        self.cookie_login()
        with connect(self.path) as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(AuthSession)), 1)

    def test_cookie_flags_and_bearer_priority(self):
        response = self.client.post('/api/v1/auth/login', json={'username': 'admin', 'password': 'test-password'})
        cookie = response.headers['set-cookie'].lower()
        for flag in ('httponly', 'samesite=strict', 'path=/api/v1', 'max-age=3600'):
            self.assertIn(flag, cookie)
        self.assertEqual(response.headers['cache-control'], 'no-store')
        self.assertEqual(self.call('GET', '/auth/me', role='manager')['role'], 'manager')
        self.assertEqual(self.client.get('/api/v1/auth/me', headers={'Authorization': 'Bearer bad'}).status_code, 401)

    def test_session_rollback_and_postgres_driver(self):
        with connect(self.path) as db:
            self.assertIsInstance(db, Session)
            db.add(Employee(username='uncommitted', password_hash=self.password_hash, role='manager', full_name='Тест'))
            db.flush()
        with connect(self.path) as db:
            self.assertIsNone(db.scalar(select(Employee).where(Employee.username == 'uncommitted')))
        engine = get_engine('postgresql+psycopg://user:password@localhost/telecom')
        self.assertEqual(engine.dialect.driver, 'psycopg')

    def test_legacy_database_and_password_upgrade(self):
        legacy_path = str(Path(self.temp.name) / 'legacy.db')
        salt = '0123456789abcdef0123456789abcdef'
        digest = hashlib.pbkdf2_hmac('sha256', b'legacy-password', salt.encode(), 600000).hex()
        encoded = salt + '$' + digest
        with sqlite3.connect(legacy_path) as db:
            db.execute('CREATE TABLE employee (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL, role TEXT NOT NULL, full_name TEXT NOT NULL)')
            db.execute('INSERT INTO employee (username, password_hash, role, full_name) VALUES (?, ?, ?, ?)', ('legacy', encoded, 'admin', 'Старый пользователь'))
        with TestClient(create_app(legacy_path, 'test-secret')) as client:
            r = client.post('/api/v1/auth/login', json={'username': 'legacy', 'password': 'legacy-password'})
            self.assertEqual(r.status_code, 200, r.text)
            self.assertEqual(client.get('/api/v1/auth/me').status_code, 200)
        with connect(legacy_path) as db:
            employee = db.scalar(select(Employee).where(Employee.username == 'legacy'))
            self.assertTrue(employee.password_hash.startswith('$argon2id$'))


if __name__ == '__main__':
    unittest.main()
