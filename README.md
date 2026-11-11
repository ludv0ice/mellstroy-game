# Учебные проекты

Новое задание по проверке банковской карты: **[card_project](card_project/README.md)**.
Внутри находятся структура из PDF, класс `Card`, JSON-данные, фикстуры,
параметризованные тесты и исследование тест-дизайна. Запускать команды этого
задания нужно из `card_project/`.

---

# REST API клиентов и тарифов

Учебный REST API по заданию: Python 3.12+, FastAPI, SQLite. Код без комментариев, модули распределены по папкам `app/controllers`, `app/core`, `app/db` и `app/models`. База создаётся автоматически при запуске и сохраняется в `telecom.db`.

## Запуск

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

В Windows вместо `source .venv/bin/activate` выполнить `.venv\Scripts\activate`.

Swagger: http://localhost:8000/api/v1/docs

Базовый URL: http://localhost:8000/api/v1

Путь к базе задаётся в `app/core/config.py`, в поле `database_path`. Переменные окружения и `import os` не используются.

## Структура

| Папка | Содержимое |
| --- | --- |
| `app` | Точка входа `main.py` и подключение маршрутов |
| `app/controllers` | Маршруты клиентов и тарифов |
| `app/core` | Настройки и обработка ошибок |
| `app/db` | Подключение SQLite, создание таблиц и общие запросы |
| `app/models` | Pydantic-модели запросов и ответов |

Внешние библиотеки импортируются только из `requirements.txt`. Для SQLite, дат, точных денежных значений, аннотаций типов и тестов используются стандартные модули Python; отдельно устанавливать их не нужно.

## Маршруты

Все пути ниже указаны относительно `/api/v1`.

| Метод | Путь | Назначение |
| --- | --- | --- |
| GET | `/tarifs` | Список тарифов |
| GET | `/tarifs/by-client/{phone}` | Тариф клиента по телефону |
| GET | `/tarifs/stats/client-count` | Названия тарифов и количество клиентов |
| GET | `/tarifs/{id_tarif}/client-count` | Количество клиентов на заданном тарифе |
| GET | `/tarifs/with-client-count` | Все поля тарифов и количество клиентов |
| POST | `/tarifs` | Создать тариф |
| PUT | `/tarifs/{id_tarif}` | Обновить переданные поля тарифа |
| DELETE | `/tarifs/{id_tarif}` | Удалить тариф |
| POST | `/clients` | Создать клиента для наполнения базы |
| GET | `/clients/search/phone?phone=%2B7` | Найти клиентов по префиксу телефона |
| GET | `/clients/sorted-by-birthday` | ФИО и дата рождения по возрастанию даты |
| GET | `/clients/search/passport-year?year=2015` | Паспорта, выданные начиная с 01.01.2016 |
| GET | `/clients/search/tarif-cost?minSalary=500` | Клиенты со стоимостью тарифа строго выше 500 |
| GET | `/clients/with-tarif` | Клиенты с тарифом через LEFT JOIN |
| PUT | `/clients/{phone}` | Обновить переданные поля клиента |
| DELETE | `/clients/{phone}` | Удалить клиента по телефону |
| PATCH | `/clients/tarif?phone=%2B79001234567&id_tarif=1` | Подключить или сменить тариф |

## Примеры

Создать тариф:

```bash
curl -X POST http://localhost:8000/api/v1/tarifs \
  -H 'Content-Type: application/json' \
  -d '{"tarif_name":"Основной","internet":50,"count_minutes":500,"count_sms":100,"salary":600}'
```

Создать клиента:

```bash
curl -X POST http://localhost:8000/api/v1/clients \
  -H 'Content-Type: application/json' \
  -d '{"number_phone":"+79001234567","id_tarif":1,"lastname":"Иванов","firstname":"Иван","patronymic_name":"Иванович","date_birthday":"1995-10-20","pasport_serial":"0012","pasport_number":"003456","date_issue":"2016-01-01"}'
```

Найти клиентов по коду страны:

```bash
curl -G http://localhost:8000/api/v1/clients/search/phone --data-urlencode 'phone=+7'
```

Изменить фамилию:

```bash
curl -X PUT http://localhost:8000/api/v1/clients/%2B79001234567 \
  -H 'Content-Type: application/json' \
  -d '{"lastname":"Петров"}'
```

## Правила

- `firstname`, `pasport_serial`, `pasport_number` и `salary` названы как в PDF.
- Телефон является первичным ключом: от 7 до 15 цифр с необязательным `+`. Запись с `8` и запись с `+7` считаются разными номерами.
- В query-параметрах `+` нужно кодировать как `%2B` или передавать через `--data-urlencode`.
- Серия и номер паспорта передаются строками, чтобы сохранялись начальные нули: 4 и 6 цифр соответственно.
- Даты имеют формат `YYYY-MM-DD`. Даты в будущем и выдача паспорта до рождения отклоняются.
- `salary` — стоимость тарифа в рублях с точностью до двух знаков. В SQLite она хранится целым числом копеек; в JSON возвращается десятичной строкой, например `"600.25"`.
- Клиент может быть без тарифа (`id_tarif: null`). Снять тариф можно через `PUT /clients/{phone}` с `{"id_tarif":null}`.
- `PUT` обновляет только переданные поля, как указано в задании. Номер телефона также можно изменить, если новый номер свободен.
- Удалить тариф с подключёнными клиентами нельзя: сначала сменить или снять их тариф.
- Статистика включает тарифы без клиентов с количеством `0`.
- JOIN возвращает вложенный объект `tarif`; для клиента без тарифа это `null`.
- Исправлена опечатка `PATCH / /clients/tarif` из PDF: фактический путь `/clients/tarif`.

Коды ответов: `200` — чтение и обновление, `201` — создание, `204` — удаление без тела, `404` — клиент или тариф не найден, `409` — занятый номер или удаление используемого тарифа, `422` — некорректные данные.

## Проверка

```bash
python -m unittest -v
```

10 интеграционных тестов используют временные базы SQLite. Проверяются все операции задания, строгие границы фильтров, JOIN, тарифы без клиентов, сохранение данных, конфликты, валидация и документация.
