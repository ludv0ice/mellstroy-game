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
