import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.db.database import get_db

bearer = HTTPBearer(auto_error=False)


def hash_password(password):
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 600000).hex()
    return f'{salt}${digest}'


def verify_password(password, encoded):
    salt, expected = encoded.split('$')
    actual = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 600000).hex()
    return hmac.compare_digest(actual, expected)


def encode(data):
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode()


def issue_token(user_id, secret):
    header = encode(b'{"alg":"HS256","typ":"JWT"}')
    payload = encode(json.dumps({'sub': str(user_id), 'exp': int(time.time()) + 3600}).encode())
    message = f'{header}.{payload}'
    signature = encode(hmac.digest(secret.encode(), message.encode(), 'sha256'))
    return f'{message}.{signature}'


def current_user(request: Request, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)], db=Depends(get_db)):
    error = HTTPException(401, 'Учетные данные не были предоставлены', headers={'WWW-Authenticate': 'Bearer'})
    if credentials is None:
        raise error
    try:
        header, payload, signature = credentials.credentials.split('.')
        expected = encode(hmac.digest(request.app.state.secret.encode(), f'{header}.{payload}'.encode(), 'sha256'))
        if not hmac.compare_digest(signature, expected):
            raise ValueError
        if json.loads(base64.urlsafe_b64decode(header + '=' * (-len(header) % 4))) != {'alg': 'HS256', 'typ': 'JWT'}:
            raise ValueError
        claims = json.loads(base64.urlsafe_b64decode(payload + '=' * (-len(payload) % 4)))
        if claims['exp'] <= time.time():
            raise ValueError
        user = db.execute('SELECT id, username, role, full_name FROM employee WHERE id = ?', (int(claims['sub']),)).fetchone()
        if user is None:
            raise ValueError
        return dict(user)
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
