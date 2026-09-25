from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.schemas.dns import LoginRequest, LoginResponse
from app.services.auth import create_session, destroy_session, get_session, user_out

router = APIRouter()
_bearer = HTTPBearer(auto_error=False)


@router.post("/login", response_model=LoginResponse, summary="Mock login (any credentials accepted)")
def login(payload: LoginRequest):
    username = payload.username.strip() or "root"
    session = create_session(username)
    return LoginResponse(token=session.token, user=user_out(session.username))


@router.post("/logout", summary="Mock logout")
def logout(creds: HTTPAuthorizationCredentials | None = Depends(_bearer)):
    if creds and creds.credentials:
        destroy_session(creds.credentials)
    return {"ok": True}


@router.get("/me", summary="Current session")
def me(session=Depends(get_session)):
    return {"user": user_out(session.username)}
