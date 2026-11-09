from datetime import date
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator


Name = Annotated[str, Field(min_length=1, max_length=100, pattern=r"\S")]
Phone = Annotated[str, Field(pattern=r"^\+?[0-9]{7,15}$")]
Amount = Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=2)]
Quantity = Annotated[int, Field(ge=0, le=2147483647)]


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class TarifCreate(Model):
    tarif_name: Name
    internet: Quantity
    count_minutes: Quantity
    count_sms: Quantity
    salary: Amount


class TarifUpdate(Model):
    tarif_name: Name | None = None
    internet: Quantity | None = None
    count_minutes: Quantity | None = None
    count_sms: Quantity | None = None
    salary: Amount | None = None

    @model_validator(mode="after")
    def check_values(self):
        if any(getattr(self, key) is None for key in self.model_fields_set):
            raise ValueError("Поля тарифа не могут быть null")
        return self


class Tarif(TarifCreate):
    id_tarif: int


class TarifWithCount(Tarif):
    client_count: int


class ClientCreate(Model):
    number_phone: Phone
    id_tarif: Annotated[int, Field(gt=0)] | None = None
    lastname: Name
    firstname: Name
    patronymic_name: Annotated[str, Field(max_length=100)] = ""
    date_birthday: date
    pasport_serial: Annotated[str, Field(pattern=r"^[0-9]{4}$")]
    pasport_number: Annotated[str, Field(pattern=r"^[0-9]{6}$")]
    date_issue: date

    @model_validator(mode="after")
    def check_dates(self):
        if self.date_birthday > date.today() or self.date_issue > date.today():
            raise ValueError("Дата не может быть в будущем")
        if self.date_issue < self.date_birthday:
            raise ValueError("Паспорт не может быть выдан до рождения")
        return self


class ClientUpdate(Model):
    number_phone: Phone | None = None
    id_tarif: Annotated[int, Field(gt=0)] | None = None
    lastname: Name | None = None
    firstname: Name | None = None
    patronymic_name: Annotated[str, Field(max_length=100)] | None = None
    date_birthday: date | None = None
    pasport_serial: Annotated[str, Field(pattern=r"^[0-9]{4}$")] | None = None
    pasport_number: Annotated[str, Field(pattern=r"^[0-9]{6}$")] | None = None
    date_issue: date | None = None

    @model_validator(mode="after")
    def check_values(self):
        if any(getattr(self, key) is None for key in self.model_fields_set - {"id_tarif"}):
            raise ValueError("Только id_tarif может быть null")
        return self


class ClientWithTarif(ClientCreate):
    tarif: Tarif | None


class Birthday(Model):
    full_name: str
    date_birthday: date


class TarifStats(Model):
    tarif_name: str
    client_count: int


class ClientCount(Model):
    tarif_id: int
    count: int


class Message(Model):
    message: str
