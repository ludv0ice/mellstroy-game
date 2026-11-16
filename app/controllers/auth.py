from fastapi import APIRouter, Depends, HTTPException, Request

from app.core.security import current_user, issue_token, verify_password
from app.db.database import get_db
from app.models.schemas import Login, TokenOut, UserOut

router = APIRouter(prefix='/auth', tags=['Авторизация'])


@router.post('/login', response_model=TokenOut)
def login(body: Login, request: Request, db=Depends(get_db)):
    user = db.execute('SELECT * FROM employee WHERE username = ?', (body.username,)).fetchone()
    encoded = user['password_hash'] if user else request.app.state.dummy_password
    valid = verify_password(body.password, encoded)
    if user is None or not valid:
        raise HTTPException(401, 'Неверный логин или пароль', headers={'WWW-Authenticate': 'Bearer'})
    return {'access_token': issue_token(user['id'], request.app.state.secret), 'role': user['role']}


@router.get('/me', response_model=UserOut)
def me(user=Depends(current_user)):
    return user
