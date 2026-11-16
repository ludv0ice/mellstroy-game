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
