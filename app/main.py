import os
import secrets
import sqlite3
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.controllers import auth, clients, tarifs
from app.core.security import hash_password
from app.db.database import initialize


def create_app(database_path=None, secret=None):
    @asynccontextmanager
    async def lifespan(app):
        initialize(app.state.database_path)
        yield

    app = FastAPI(title='Управление клиентами и тарифами', version='2.0', docs_url='/api/v1/docs', redoc_url='/api/v1/redoc', openapi_url='/api/v1/openapi.json', lifespan=lifespan)
    app.state.database_path = database_path or os.getenv('DATABASE_PATH', 'telecom.db')
    app.state.secret = secret or os.getenv('JWT_SECRET') or secrets.token_urlsafe(48)
    app.state.dummy_password = hash_password(secrets.token_urlsafe(32))

    @app.exception_handler(sqlite3.IntegrityError)
    async def integrity_error(request: Request, error):
        message = str(error)
        if 'client.number_phone' in message:
            detail = 'Клиент с таким номером телефона уже существует'
        elif 'tarif.tarif_name' in message:
            detail = 'Тариф с таким названием уже существует'
        elif 'FOREIGN KEY' in message:
            detail = 'Операция нарушает связь клиента с тарифом'
        else:
            detail = 'Данные конфликтуют с существующей записью'
        return JSONResponse(status_code=409, content={'detail': detail})

    for router in (auth.router, tarifs.router, clients.router):
        app.include_router(router, prefix='/api/v1')
    return app


app = create_app()
