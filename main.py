import sqlite3
from contextlib import asynccontextmanager
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, FastAPI, HTTPException, Query, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from database import connect, initialize
from models import Amount, Birthday, ClientCount, ClientCreate, ClientUpdate, ClientWithTarif, Message, Tarif, TarifCreate, TarifStats, TarifUpdate, TarifWithCount


@asynccontextmanager
async def lifespan(app):
    initialize()
    yield


app = FastAPI(title="Клиенты и тарифы", version="1.0", docs_url="/api/v1/docs", redoc_url=None, openapi_url="/api/v1/openapi.json", lifespan=lifespan)
api = APIRouter(prefix="/api/v1")


@app.exception_handler(sqlite3.IntegrityError)
async def integrity_error(request, error):
    return JSONResponse(status_code=409, content={"detail": "Нарушение связи с тарифом или номер телефона уже занят"})


def get_tarif(db, tarif_id):
    row = db.execute("SELECT * FROM tarif WHERE id_tarif = ?", (tarif_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "Тариф не найден")
    return tarif_data(row)


def tarif_data(row):
    result = dict(row)
    result["salary"] = Decimal(result["salary"]) / 100
    return result


def get_client(db, phone):
    row = db.execute("SELECT * FROM client WHERE number_phone = ?", (phone,)).fetchone()
    if row is None:
        raise HTTPException(404, "Клиент не найден")
    return dict(row)


def require_tarif(db, tarif_id):
    if tarif_id is not None:
        get_tarif(db, tarif_id)


def update(db, table, key, value, data):
    if data:
        fields = ", ".join(f"{field} = ?" for field in data)
        db.execute(f"UPDATE {table} SET {fields} WHERE {key} = ?", (*data.values(), value))


def joined_clients(db, min_salary=None):
    sql = """SELECT c.*, t.tarif_name, t.internet, t.count_minutes, t.count_sms, t.salary
             FROM client c LEFT JOIN tarif t ON c.id_tarif = t.id_tarif"""
    params = ()
    if min_salary is not None:
        sql += " WHERE t.salary > ?"
        params = (int(min_salary * 100),)
    result = []
    for row in db.execute(sql + " ORDER BY c.number_phone", params):
        data = dict(row)
        tarif = {key: data.pop(key) for key in ("tarif_name", "internet", "count_minutes", "count_sms", "salary")}
        data["tarif"] = tarif_data({"id_tarif": data["id_tarif"], **tarif}) if data["id_tarif"] is not None else None
        result.append(data)
    return result


@api.get("/tarifs", response_model=list[Tarif], tags=["Tarif"])
def list_tarifs():
    with connect() as db:
        return [tarif_data(row) for row in db.execute("SELECT * FROM tarif ORDER BY id_tarif")]


@api.get("/tarifs/by-client/{phone}", response_model=Tarif, tags=["Tarif"])
def tarif_by_client(phone: str):
    with connect() as db:
        client = get_client(db, phone)
        return get_tarif(db, client["id_tarif"])


@api.get("/tarifs/stats/client-count", response_model=list[TarifStats], tags=["Tarif"])
def tarif_stats():
    with connect() as db:
        return [dict(row) for row in db.execute("""SELECT t.tarif_name, COUNT(c.number_phone) AS client_count
            FROM tarif t LEFT JOIN client c ON t.id_tarif = c.id_tarif
            GROUP BY t.id_tarif ORDER BY t.id_tarif""")]


@api.get("/tarifs/with-client-count", response_model=list[TarifWithCount], tags=["Tarif"])
def tarifs_with_count():
    with connect() as db:
        return [tarif_data(row) for row in db.execute("""SELECT t.*, COUNT(c.number_phone) AS client_count
            FROM tarif t LEFT JOIN client c ON t.id_tarif = c.id_tarif
            GROUP BY t.id_tarif ORDER BY t.id_tarif""")]


@api.get("/tarifs/{id_tarif}/client-count", response_model=ClientCount, tags=["Tarif"])
def tarif_client_count(id_tarif: int):
    with connect() as db:
        get_tarif(db, id_tarif)
        count = db.execute("SELECT COUNT(*) FROM client WHERE id_tarif = ?", (id_tarif,)).fetchone()[0]
        return {"tarif_id": id_tarif, "count": count}


@api.post("/tarifs", response_model=Tarif, status_code=201, tags=["Tarif"])
def create_tarif(body: TarifCreate):
    data = body.model_dump()
    data["salary"] = int(data["salary"] * 100)
    with connect() as db:
        cursor = db.execute("INSERT INTO tarif (tarif_name, internet, count_minutes, count_sms, salary) VALUES (?, ?, ?, ?, ?)", tuple(data.values()))
        return get_tarif(db, cursor.lastrowid)


@api.put("/tarifs/{id_tarif}", response_model=Tarif, tags=["Tarif"])
def update_tarif(id_tarif: int, body: TarifUpdate):
    data = body.model_dump(exclude_unset=True)
    if "salary" in data:
        data["salary"] = int(data["salary"] * 100)
    with connect() as db:
        get_tarif(db, id_tarif)
        update(db, "tarif", "id_tarif", id_tarif, data)
        return get_tarif(db, id_tarif)


@api.delete("/tarifs/{id_tarif}", status_code=204, tags=["Tarif"])
def delete_tarif(id_tarif: int):
    with connect() as db:
        get_tarif(db, id_tarif)
        if db.execute("SELECT 1 FROM client WHERE id_tarif = ? LIMIT 1", (id_tarif,)).fetchone():
            raise HTTPException(409, "К тарифу подключены клиенты")
        db.execute("DELETE FROM tarif WHERE id_tarif = ?", (id_tarif,))
    return Response(status_code=204)


@api.get("/clients/search/phone", response_model=list[ClientCreate], tags=["Client"])
def search_phone(phone: Annotated[str, Query(pattern=r"^\+?[0-9]{1,15}$")]):
    with connect() as db:
        return [dict(row) for row in db.execute("SELECT * FROM client WHERE number_phone LIKE ? ORDER BY number_phone", (phone + "%",))]


@api.get("/clients/sorted-by-birthday", response_model=list[Birthday], tags=["Client"])
def sorted_clients():
    with connect() as db:
        return [{"full_name": " ".join(filter(None, (row["lastname"], row["firstname"], row["patronymic_name"]))), "date_birthday": row["date_birthday"]} for row in db.execute("SELECT * FROM client ORDER BY date_birthday, number_phone")]


@api.get("/clients/search/passport-year", response_model=list[ClientCreate], tags=["Client"])
def search_passport(year: Annotated[int, Query(ge=1, le=9999)]):
    with connect() as db:
        return [dict(row) for row in db.execute("SELECT * FROM client WHERE date_issue > ? ORDER BY number_phone", (f"{year:04d}-12-31",))]


@api.get("/clients/search/tarif-cost", response_model=list[ClientWithTarif], tags=["Client"])
def search_tarif_cost(minSalary: Annotated[Amount, Query()]):
    with connect() as db:
        return joined_clients(db, minSalary)


@api.get("/clients/with-tarif", response_model=list[ClientWithTarif], tags=["Client"])
def clients_with_tarif():
    with connect() as db:
        return joined_clients(db)


@api.post("/clients", response_model=ClientCreate, status_code=201, tags=["Client"])
def create_client(body: ClientCreate):
    data = body.model_dump(mode="json")
    with connect() as db:
        require_tarif(db, body.id_tarif)
        db.execute("""INSERT INTO client (number_phone, id_tarif, lastname, firstname, patronymic_name,
            date_birthday, pasport_serial, pasport_number, date_issue) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""", tuple(data.values()))
        return get_client(db, body.number_phone)


@api.patch("/clients/tarif", response_model=Message, tags=["Client"])
def assign_tarif(phone: str, id_tarif: Annotated[int, Query(gt=0)]):
    with connect() as db:
        get_client(db, phone)
        require_tarif(db, id_tarif)
        db.execute("UPDATE client SET id_tarif = ? WHERE number_phone = ?", (id_tarif, phone))
    return {"message": "Тариф клиента обновлён"}


@api.put("/clients/{phone}", response_model=ClientCreate, tags=["Client"])
def update_client(phone: str, body: ClientUpdate):
    data = body.model_dump(mode="json", exclude_unset=True)
    with connect() as db:
        current = get_client(db, phone)
        try:
            ClientCreate.model_validate({**current, **data})
        except ValidationError as error:
            raise RequestValidationError(error.errors()) from error
        if "id_tarif" in data:
            require_tarif(db, data["id_tarif"])
        update(db, "client", "number_phone", phone, data)
        return get_client(db, data.get("number_phone", phone))


@api.delete("/clients/{phone}", status_code=204, tags=["Client"])
def delete_client(phone: str):
    with connect() as db:
        get_client(db, phone)
        db.execute("DELETE FROM client WHERE number_phone = ?", (phone,))
    return Response(status_code=204)


app.include_router(api)
