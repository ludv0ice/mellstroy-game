from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlalchemy import select

from app.models.entities import Client, Tarif
from app.models.schemas import ClientCreate


def fields(entity):
    return {column.name: getattr(entity, column.name) for column in entity.__table__.columns}


def tarif_out(tarif):
    return fields(tarif) | {'salary': tarif.salary / 100}


def client_out(client):
    return fields(client) | {'tarif': tarif_out(client.tarif) if client.tarif else None}


def get_tarif(db, tarif_id):
    tarif = db.get(Tarif, tarif_id)
    if tarif is None:
        raise HTTPException(404, 'Тариф не найден')
    return tarif


def get_client(db, phone):
    client = db.get(Client, phone)
    if client is None:
        raise HTTPException(404, 'Клиент с таким номером телефона не найден')
    return client


def clients(db, *conditions):
    query = select(Client).where(*conditions).order_by(Client.number_phone)
    return [client_out(client) for client in db.scalars(query)]


def ensure_tarif(db, tarif_id):
    if tarif_id is not None and db.get(Tarif, tarif_id) is None:
        raise HTTPException(422, [{'loc': ['body', 'id_tarif'], 'msg': 'Тариф должен существовать', 'type': 'value_error.tarif_not_found'}])


def values(model):
    result = model.model_dump(exclude_unset=True)
    if 'salary' in result:
        result['salary'] = int(result['salary'] * 100)
    return result


def save(db, entity, data=None):
    if data is not None:
        if not data:
            raise HTTPException(422, 'Передайте хотя бы одно поле для обновления')
        for key, value in data.items():
            setattr(entity, key, value)
    db.add(entity)
    db.commit()
    db.refresh(entity)
    return entity


def update_client(db, phone, patch):
    client = get_client(db, phone)
    data = patch.model_dump(mode='json', exclude_unset=True)
    try:
        ClientCreate.model_validate(fields(client) | data)
    except ValidationError as error:
        raise RequestValidationError([{**item, 'loc': ('body', *item['loc'])} for item in error.errors()])
    ensure_tarif(db, data.get('id_tarif'))
    return client_out(save(db, client, data))
