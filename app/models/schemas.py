from datetime import date
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_core import PydanticCustomError

Phone = Annotated[str, Field(pattern=r'^(\+7|8)[0-9]{10}$')]
PositiveId = Annotated[int, Field(gt=0)]
Money = Annotated[Decimal, Field(ge=0, le=1000000, max_digits=9, decimal_places=2)]


class Schema(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)


class TarifCreate(Schema):
    tarif_name: str = Field(min_length=2, max_length=100)
    internet: int = Field(ge=0, le=100000, strict=True)
    count_minutes: int = Field(ge=0, le=10000, strict=True)
    count_sms: int = Field(ge=0, le=10000, strict=True)
    salary: Money


class TarifPatch(TarifCreate):
    tarif_name: str = Field(default=None, min_length=2, max_length=100)
    internet: int = Field(default=None, ge=0, le=100000, strict=True)
    count_minutes: int = Field(default=None, ge=0, le=10000, strict=True)
    count_sms: int = Field(default=None, ge=0, le=10000, strict=True)
    salary: Money = None


class TarifOut(TarifCreate):
    id_tarif: int
    salary: float


class TarifCount(TarifOut):
    client_count: int


class ClientCreate(Schema):
    number_phone: Phone
    id_tarif: PositiveId | None = None
    lastname: str
    firstname: str
    patronymic_name: str = ''
    date_birthday: date
    pasport_serial: str = Field(pattern=r'^[0-9]{4}$')
    pasport_number: str = Field(pattern=r'^[0-9]{6}$')
    date_issue: date

    @field_validator('lastname', 'firstname', 'patronymic_name')
    @classmethod
    def validate_name(cls, value, info):
        if info.field_name == 'patronymic_name' and value == '':
            return value
        if not 2 <= len(value) <= 50 or not all(c.isalpha() or c == '-' for c in value) or not any(c.isalpha() for c in value):
            raise PydanticCustomError('value_error.name_format', 'Имя должно содержать от 2 до 50 символов: буквы и дефис')
        return value

    @field_validator('date_birthday')
    @classmethod
    def validate_birthday(cls, value):
        today = date.today()
        age = today.year - value.year - ((today.month, today.day) < (value.month, value.day))
        if value > today or not 18 <= age <= 120:
            raise PydanticCustomError('value_error.age_range', 'Возраст клиента должен быть от 18 до 120 лет')
        return value

    @field_validator('date_issue')
    @classmethod
    def validate_issue(cls, value):
        if value > date.today():
            raise PydanticCustomError('value_error.date_future', 'Дата выдачи паспорта не может быть в будущем')
        return value

    @model_validator(mode='after')
    def validate_dates(self):
        if self.date_issue is not None and self.date_birthday is not None and self.date_issue < self.date_birthday:
            raise PydanticCustomError('value_error.date_order', 'Дата выдачи паспорта не может быть раньше даты рождения')
        return self


class ClientPatch(ClientCreate):
    number_phone: Phone = None
    lastname: str = None
    firstname: str = None
    date_birthday: date = None
    pasport_serial: str = Field(default=None, pattern=r'^[0-9]{4}$')
    pasport_number: str = Field(default=None, pattern=r'^[0-9]{6}$')
    date_issue: date = None


class ClientOut(ClientCreate):
    tarif: TarifOut | None


class ClientPage(Schema):
    total: int
    limit: int
    offset: int
    items: list[ClientOut]


class Login(Schema):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=200)


class UserOut(Schema):
    id: int
    username: str
    role: str
    full_name: str


class TokenOut(Schema):
    access_token: str
    token_type: str = 'bearer'
    role: str
