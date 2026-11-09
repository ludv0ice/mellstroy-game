from fastapi import APIRouter, HTTPException, Response

from app.db.database import connect
from app.db.queries import get_client, get_tarif, tarif_data, update
from app.models.schemas import ClientCount, Tarif, TarifCreate, TarifStats, TarifUpdate, TarifWithCount


router = APIRouter(prefix="/tarifs", tags=["Tarif"])


@router.get("", response_model=list[Tarif])
def list_tarifs():
    with connect() as db:
        return [tarif_data(row) for row in db.execute("SELECT * FROM tarif ORDER BY id_tarif")]


@router.get("/by-client/{phone}", response_model=Tarif)
def tarif_by_client(phone: str):
    with connect() as db:
        client = get_client(db, phone)
        return get_tarif(db, client["id_tarif"])


@router.get("/stats/client-count", response_model=list[TarifStats])
def tarif_stats():
    with connect() as db:
        return [dict(row) for row in db.execute("""SELECT t.tarif_name, COUNT(c.number_phone) AS client_count
            FROM tarif t LEFT JOIN client c ON t.id_tarif = c.id_tarif
            GROUP BY t.id_tarif ORDER BY t.id_tarif""")]


@router.get("/with-client-count", response_model=list[TarifWithCount])
def tarifs_with_count():
    with connect() as db:
        return [tarif_data(row) for row in db.execute("""SELECT t.*, COUNT(c.number_phone) AS client_count
            FROM tarif t LEFT JOIN client c ON t.id_tarif = c.id_tarif
            GROUP BY t.id_tarif ORDER BY t.id_tarif""")]


@router.get("/{id_tarif}/client-count", response_model=ClientCount)
def tarif_client_count(id_tarif: int):
    with connect() as db:
        get_tarif(db, id_tarif)
        count = db.execute("SELECT COUNT(*) FROM client WHERE id_tarif = ?", (id_tarif,)).fetchone()[0]
        return {"tarif_id": id_tarif, "count": count}


@router.post("", response_model=Tarif, status_code=201)
def create_tarif(body: TarifCreate):
    data = body.model_dump()
    data["salary"] = int(data["salary"] * 100)
    with connect() as db:
        cursor = db.execute("INSERT INTO tarif (tarif_name, internet, count_minutes, count_sms, salary) VALUES (?, ?, ?, ?, ?)", tuple(data.values()))
        return get_tarif(db, cursor.lastrowid)


@router.put("/{id_tarif}", response_model=Tarif)
def update_tarif(id_tarif: int, body: TarifUpdate):
    data = body.model_dump(exclude_unset=True)
    if "salary" in data:
        data["salary"] = int(data["salary"] * 100)
    with connect() as db:
        get_tarif(db, id_tarif)
        update(db, "tarif", "id_tarif", id_tarif, data)
        return get_tarif(db, id_tarif)


@router.delete("/{id_tarif}", status_code=204)
def delete_tarif(id_tarif: int):
    with connect() as db:
        get_tarif(db, id_tarif)
        if db.execute("SELECT 1 FROM client WHERE id_tarif = ? LIMIT 1", (id_tarif,)).fetchone():
            raise HTTPException(409, "К тарифу подключены клиенты")
        db.execute("DELETE FROM tarif WHERE id_tarif = ?", (id_tarif,))
    return Response(status_code=204)
