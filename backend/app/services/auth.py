"""Mock auth: in-memory token store. No real credentials are stored."""

import secrets
from dataclasses import dataclass

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette import status

from app.schemas.dns import UserOut

_tokens: dict[str, str] = {}  # token -> username
_bearer = HTTPBearer(auto_error=False)


@dataclass
class Session:
    username: str
    token: str


def create_session(username: str) -> Session:
    token = secrets.token_urlsafe(32)
    _tokens[token] = username.strip() or "root"
    return Session(username=_tokens[token], token=token)


def destroy_session(token: str) -> None:
    _tokens.pop(token, None)


def get_session(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> Session:
    if not creds or not creds.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    username = _tokens.get(creds.credentials)
    if not username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session")
    return Session(username=username, token=creds.credentials)


def user_out(username: str) -> UserOut:
    return UserOut(username=username, display_name=username)
