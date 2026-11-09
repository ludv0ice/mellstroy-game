from typing import Annotated

from fastapi import APIRouter, Query, Response
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from app.db.database import connect
from app.db.queries import get_client, joined_clients, require_tarif, update
from app.models.schemas import Amount, Birthday, ClientCreate, ClientUpdate, ClientWithTarif, Message


router = APIRouter(prefix="/clients", tags=["Клиенты"])


@router.get("/search/phone", response_model=list[ClientCreate], summary="Найти клиентов по коду страны")
def search_phone(phone: Annotated[str, Query(pattern=r"^\+?[0-9]{1,15}$")]):
    with connect() as db:
        return [dict(row) for row in db.execute("SELECT * FROM client WHERE number_phone LIKE ? ORDER BY number_phone", (phone + "%",))]


@router.get("/sorted-by-birthday", response_model=list[Birthday], summary="Список клиентов по дате рождения")
def sorted_clients():
    with connect() as db:
        return [{"full_name": " ".join(filter(None, (row["lastname"], row["firstname"], row["patronymic_name"]))), "date_birthday": row["date_birthday"]} for row in db.execute("SELECT * FROM client ORDER BY date_birthday, number_phone")]


@router.get("/search/passport-year", response_model=list[ClientCreate], summary="Найти клиентов по году выдачи паспорта")
def search_passport(year: Annotated[int, Query(ge=1, le=9999)]):
    with connect() as db:
        return [dict(row) for row in db.execute("SELECT * FROM client WHERE date_issue > ? ORDER BY number_phone", (f"{year:04d}-12-31",))]


@router.get("/search/tarif-cost", response_model=list[ClientWithTarif], summary="Найти клиентов по стоимости тарифа")
def search_tarif_cost(minSalary: Annotated[Amount, Query()]):
    with connect() as db:
        return joined_clients(db, minSalary)


@router.get("/with-tarif", response_model=list[ClientWithTarif], summary="Список клиентов с тарифами")
def clients_with_tarif():
    with connect() as db:
        return joined_clients(db)


@router.post("", response_model=ClientCreate, status_code=201, summary="Добавить клиента")
def create_client(body: ClientCreate):
    data = body.model_dump(mode="json")
    with connect() as db:
        require_tarif(db, body.id_tarif)
        db.execute("""INSERT INTO client (number_phone, id_tarif, lastname, firstname, patronymic_name,
            date_birthday, pasport_serial, pasport_number, date_issue) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""", tuple(data.values()))
        return get_client(db, body.number_phone)


@router.patch("/tarif", response_model=Message, summary="Изменить тариф клиента")
def assign_tarif(phone: str, id_tarif: Annotated[int, Query(gt=0)]):
    with connect() as db:
        get_client(db, phone)
        require_tarif(db, id_tarif)
        db.execute("UPDATE client SET id_tarif = ? WHERE number_phone = ?", (id_tarif, phone))
    return {"message": "Тариф клиента обновлён"}


@router.put("/{phone}", response_model=ClientCreate, summary="Изменить данные клиента")
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


@router.delete("/{phone}", status_code=204, summary="Удалить клиента")
def delete_client(phone: str):
    with connect() as db:
        get_client(db, phone)
        db.execute("DELETE FROM client WHERE number_phone = ?", (phone,))
    return Response(status_code=204)
