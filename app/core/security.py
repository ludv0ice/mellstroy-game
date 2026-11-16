import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from fastapi.security import APIKeyCookie, HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext
from sqlalchemy import delete

from app.core import config
from app.db.database import get_db
from app.models.entities import AuthSession, Employee
from app.services.telecom import fields

bearer = HTTPBearer(auto_error=False)
cookie_auth = APIKeyCookie(name=config.SESSION_COOKIE_NAME, auto_error=False)
passwords = CryptContext(schemes=['argon2'], argon2__type='ID')


def hash_password(password):
    return passwords.hash(password)


def verify_password(password, encoded):
    try:
        if encoded.startswith('$argon2'):
            return passwords.verify(password, encoded)
        salt, expected = encoded.split('$')
        actual = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 600000).hex()
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def encode(data):
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode()


def issue_token(user_id, secret):
    header = encode(b'{"alg":"HS256","typ":"JWT"}')
    payload = encode(json.dumps({'sub': str(user_id), 'exp': int(time.time()) + config.SESSION_SECONDS}).encode())
    message = f'{header}.{payload}'
    signature = encode(hmac.digest(secret.encode(), message.encode(), 'sha256'))
    return f'{message}.{signature}'


def token_user_id(token, secret):
    header, payload, signature = token.split('.')
    expected = encode(hmac.digest(secret.encode(), f'{header}.{payload}'.encode(), 'sha256'))
    if not hmac.compare_digest(signature, expected):
        raise ValueError
    if json.loads(base64.urlsafe_b64decode(header + '=' * (-len(header) % 4))) != {'alg': 'HS256', 'typ': 'JWT'}:
        raise ValueError
    claims = json.loads(base64.urlsafe_b64decode(payload + '=' * (-len(payload) % 4)))
    if claims['exp'] <= time.time():
        raise ValueError
    user_id = int(claims['sub'])
    if not 0 < user_id <= 2147483647:
        raise ValueError
    return user_id


def session_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def check_origin(request, required=False):
    origin = request.headers.get('origin')
    if (required or origin is not None) and origin != str(request.base_url).rstrip('/'):
        raise HTTPException(403, 'Для cookie-сессии изменяющий запрос должен исходить с того же адреса приложения')
    if request.headers.get('sec-fetch-site') == 'cross-site':
        raise HTTPException(403, 'Межсайтовый запрос запрещен')


def create_session(db, user_id, previous_token=None):
    db.execute(delete(AuthSession).where(AuthSession.expires_at <= int(time.time())))
    if previous_token:
        db.execute(delete(AuthSession).where(AuthSession.token_hash == session_hash(previous_token)))
    token = secrets.token_urlsafe(48)
    db.add(AuthSession(token_hash=session_hash(token), employee_id=user_id, expires_at=int(time.time()) + config.SESSION_SECONDS))
    db.commit()
    return token


def current_user(request: Request, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)], session_token: Annotated[str | None, Depends(cookie_auth)], db=Depends(get_db)):
    error = HTTPException(401, 'Учетные данные не были предоставлены', headers={'WWW-Authenticate': 'Bearer'})
    try:
        if credentials is not None:
            user_id = token_user_id(credentials.credentials, request.app.state.secret)
        elif session_token:
            session = db.get(AuthSession, session_hash(session_token))
            if session is None or session.expires_at <= time.time():
                raise ValueError
            if request.method not in ('GET', 'HEAD', 'OPTIONS'):
                check_origin(request, required=True)
            user_id = session.employee_id
        else:
            raise ValueError
        user = db.get(Employee, user_id)
        if user is None:
            raise ValueError
        return {key: value for key, value in fields(user).items() if key != 'password_hash'}
    except (ValueError, KeyError, TypeError, OverflowError):
        raise error


def require_roles(*roles):
    def dependency(user=Depends(current_user)):
        if user['role'] not in roles:
            raise HTTPException(403, 'У вас недостаточно прав для выполнения операции')
        return user
    return dependency


staff = require_roles('manager', 'admin')
admin = require_roles('admin')
