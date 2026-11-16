from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import delete, select

from app.core import config
from app.core.security import check_origin, create_session, current_user, hash_password, issue_token, session_hash, verify_password, passwords
from app.db.database import get_db
from app.models.entities import AuthSession, Employee
from app.models.schemas import Login, TokenOut, UserOut

router = APIRouter(prefix='/auth', tags=['Авторизация'])


@router.post('/login', response_model=TokenOut)
def login(body: Login, request: Request, response: Response, db=Depends(get_db)):
    check_origin(request)
    user = db.scalar(select(Employee).where(Employee.username == body.username))
    encoded = user.password_hash if user else request.app.state.dummy_password
    valid = verify_password(body.password, encoded)
    if user is None or not valid:
        raise HTTPException(401, 'Неверный логин или пароль', headers={'WWW-Authenticate': 'Bearer'})
    if not encoded.startswith('$argon2') or passwords.needs_update(encoded):
        user.password_hash = hash_password(body.password)
    token = create_session(db, user.id, request.cookies.get(config.SESSION_COOKIE_NAME))
    response.set_cookie(config.SESSION_COOKIE_NAME, token, max_age=config.SESSION_SECONDS, path='/api/v1', httponly=True, secure=config.SESSION_COOKIE_SECURE, samesite='strict')
    response.headers['Cache-Control'] = 'no-store'
    return {'access_token': issue_token(user.id, request.app.state.secret), 'role': user.role}


@router.get('/me', response_model=UserOut)
def me(user=Depends(current_user)):
    return user


@router.post('/logout', status_code=204)
def logout(request: Request, user=Depends(current_user), db=Depends(get_db)):
    token = request.cookies.get(config.SESSION_COOKIE_NAME)
    if token:
        db.execute(delete(AuthSession).where(AuthSession.token_hash == session_hash(token), AuthSession.employee_id == user['id']))
        db.commit()
    response = Response(status_code=204)
    response.delete_cookie(config.SESSION_COOKIE_NAME, path='/api/v1', httponly=True, secure=config.SESSION_COOKIE_SECURE, samesite='strict')
    return response
