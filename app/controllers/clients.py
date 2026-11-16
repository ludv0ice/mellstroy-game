from datetime import date
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import func, select

from app.core.security import admin, staff
from app.db.database import get_db
from app.models.entities import Client, Tarif
from app.models.schemas import ClientCreate, ClientOut, ClientPage, ClientPatch, Phone, PositiveId
from app.services.telecom import client_out, clients, ensure_tarif, get_client, save, update_client

router = APIRouter(prefix='/clients', tags=['Клиенты'], dependencies=[Depends(staff)])


@router.get('', response_model=ClientPage)
def list_clients(limit: Annotated[int, Query(ge=1, le=100)] = 20, offset: Annotated[int, Query(ge=0)] = 0, tarif_id: PositiveId | None = None, db=Depends(get_db)):
    conditions = [Client.id_tarif == tarif_id] if tarif_id is not None else []
    total = db.scalar(select(func.count()).select_from(Client).where(*conditions))
    query = select(Client).where(*conditions).order_by(Client.number_phone).limit(limit).offset(offset)
    return {'total': total, 'limit': limit, 'offset': offset, 'items': [client_out(client) for client in db.scalars(query)]}


@router.post('', status_code=201, response_model=ClientOut)
def create_client(body: ClientCreate, db=Depends(get_db)):
    ensure_tarif(db, body.id_tarif)
    return client_out(save(db, Client(**body.model_dump(mode='json'))))


@router.get('/search/phone', response_model=list[ClientOut])
def search_phone(phone: Annotated[str, Query(pattern=r'^(\+7|8)[0-9]{0,10}$')], db=Depends(get_db)):
    return clients(db, Client.number_phone.startswith(phone))


@router.get('/sorted-by-birthday')
def sorted_birthday(db=Depends(get_db)):
    rows = db.scalars(select(Client).order_by(Client.date_birthday, Client.number_phone))
    return [{'full_name': ' '.join(filter(None, [c.lastname, c.firstname, c.patronymic_name])), 'date_birthday': c.date_birthday} for c in rows]


@router.get('/search/passport-year', response_model=list[ClientOut])
def passport_year(year: Annotated[int, Query(ge=1900, le=date.today().year)], db=Depends(get_db)):
    return clients(db, Client.date_issue > f'{year:04d}-12-31')


@router.get('/search/tarif-cost', response_model=list[ClientOut])
def tarif_cost(minSalary: Annotated[Decimal, Query(ge=0)], db=Depends(get_db)):
    return clients(db, Client.id_tarif.in_(select(Tarif.id_tarif).where(Tarif.salary > minSalary * 100)))


@router.patch('/tarif', response_model=ClientOut)
def change_tarif(phone: Phone, id_tarif: PositiveId, db=Depends(get_db)):
    return update_client(db, phone, ClientPatch(id_tarif=id_tarif))


@router.get('/{phone}', response_model=ClientOut)
def client_card(phone: Phone, db=Depends(get_db)):
    return client_out(get_client(db, phone))


@router.patch('/{phone}', response_model=ClientOut)
def patch_client(phone: Phone, body: ClientPatch, db=Depends(get_db)):
    return update_client(db, phone, body)


@router.delete('/{phone}', status_code=204, dependencies=[Depends(admin)])
def delete_client(phone: Phone, db=Depends(get_db)):
    db.delete(get_client(db, phone))
    db.commit()
    return Response(status_code=204)
