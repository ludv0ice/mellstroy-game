from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import func, select

from app.core.security import admin, staff
from app.db.database import get_db
from app.models.entities import Client, Tarif
from app.models.schemas import Phone, PositiveId, TarifCount, TarifCreate, TarifOut, TarifPatch
from app.services.telecom import get_client, get_tarif, save, tarif_out, values

router = APIRouter(prefix='/tarifs', tags=['Тарифы'])


def counts(db):
    query = select(Tarif, func.count(Client.number_phone)).outerjoin(Client, Client.id_tarif == Tarif.id_tarif).group_by(*Tarif.__table__.columns).order_by(Tarif.id_tarif)
    return db.execute(query).all()


@router.get('', response_model=list[TarifOut])
def list_tarifs(db=Depends(get_db)):
    return [tarif_out(tarif) for tarif in db.scalars(select(Tarif).order_by(Tarif.id_tarif))]


@router.get('/by-client/{phone}', response_model=TarifOut, dependencies=[Depends(staff)])
def by_client(phone: Phone, db=Depends(get_db)):
    tarif = get_client(db, phone).tarif
    if tarif is None:
        raise HTTPException(404, 'У клиента не подключен тариф')
    return tarif_out(tarif)


@router.get('/stats/client-count')
def stats(db=Depends(get_db)):
    return [{'tarif_name': tarif.tarif_name, 'client_count': count} for tarif, count in counts(db)]


@router.get('/with-client-count', response_model=list[TarifCount], dependencies=[Depends(staff)])
def with_counts(db=Depends(get_db)):
    return [tarif_out(tarif) | {'client_count': count} for tarif, count in counts(db)]


@router.get('/{id_tarif}/client-count', dependencies=[Depends(staff)])
def client_count(id_tarif: PositiveId, db=Depends(get_db)):
    get_tarif(db, id_tarif)
    count = db.scalar(select(func.count()).select_from(Client).where(Client.id_tarif == id_tarif))
    return {'tarif_id': id_tarif, 'count': count}


@router.post('', status_code=201, response_model=TarifOut, dependencies=[Depends(admin)])
def create_tarif(body: TarifCreate, db=Depends(get_db)):
    return tarif_out(save(db, Tarif(**values(body))))


@router.patch('/{id_tarif}', response_model=TarifOut, dependencies=[Depends(admin)])
def patch_tarif(id_tarif: PositiveId, body: TarifPatch, db=Depends(get_db)):
    return tarif_out(save(db, get_tarif(db, id_tarif), values(body)))


@router.delete('/{id_tarif}', status_code=204, dependencies=[Depends(admin)])
def delete_tarif(id_tarif: PositiveId, db=Depends(get_db)):
    tarif = get_tarif(db, id_tarif)
    if db.scalar(select(Client.number_phone).where(Client.id_tarif == id_tarif).limit(1)):
        raise HTTPException(409, 'Тариф подключен клиентам: сначала смените или снимите тариф')
    db.delete(tarif)
    db.commit()
    return Response(status_code=204)
