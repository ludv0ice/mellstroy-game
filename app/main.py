import sqlite3
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.controllers import clients, tarifs
from app.core.config import settings
from app.core.errors import integrity_error
from app.db.database import initialize


@asynccontextmanager
async def lifespan(app):
    initialize()
    yield


app = FastAPI(
    title="Клиенты и тарифы",
    version="1.0",
    description="Управление клиентами и тарифами телекоммуникационной компании.",
    openapi_tags=[
        {"name": "Клиенты", "description": "Список клиентов, поиск и управление данными клиентов."},
        {"name": "Тарифы", "description": "Список тарифов, управление тарифами и статистика подключений."},
    ],
    docs_url=f"{settings.api_prefix}/docs",
    redoc_url=None,
    openapi_url=f"{settings.api_prefix}/openapi.json",
    lifespan=lifespan,
)
app.add_exception_handler(sqlite3.IntegrityError, integrity_error)
app.include_router(tarifs.router, prefix=settings.api_prefix)
app.include_router(clients.router, prefix=settings.api_prefix)
