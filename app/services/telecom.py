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
    result = model.model_dump(exclude_unset=True)
    if 'salary' in result:
        result['salary'] = int(result['salary'] * 100)
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
