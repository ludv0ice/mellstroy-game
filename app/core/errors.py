from fastapi.responses import JSONResponse


async def integrity_error(request, error):
    return JSONResponse(status_code=409, content={"detail": "Нарушение связи с тарифом или номер телефона уже занят"})
