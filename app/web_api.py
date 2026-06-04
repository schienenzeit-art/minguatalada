# NOT ACTIVE IN PRODUCTION
# Dieses Modul ist ein Architektur-Vorbereitungs-Adapter für eine spätere API-Schicht.
# Es wird von keinem anderen Produktions-Modul importiert und ist aktuell nicht gestartet.
# Voraussetzungen für Aktivierung: Thread-sicherer Session-Kontext (Request-scoped),
# PostgreSQL/geteilte DB, separater ASGI-Startprozess.
# Roadmap: v2.x
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordBearer

from app.config import SECRET_KEY, JWT_ALGORITHM, JWT_EXPIRY
from services.auth_service import AuthService
from services.user_service import UserService

app = FastAPI(title="Anspruchssystem API (adapter)")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")

auth_service = AuthService()
user_service = UserService()


def create_token(user: dict) -> str:
    payload = {
        "sub": user.get("username"),
        "uid": user.get("id"),
        "role": user.get("role_name"),
        "exp": datetime.now(timezone.utc) + JWT_EXPIRY,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=JWT_ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    try:
        data = jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGORITHM])
        username = data.get("sub")
        if not username:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
        user = auth_service.user_repository.get_by_username(username)
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)


@app.post("/api/login")
def api_login(username: str, password: str):
    result = auth_service.login(username, password)
    if not result["success"]:
        raise HTTPException(status_code=401, detail=result["message"])
    token = create_token(result["user"])
    return {"access_token": token, "token_type": "bearer"}


@app.get("/")
def root():
    return RedirectResponse(url="/docs")


@app.get("/api/me")
def api_me(current_user: dict = Depends(get_current_user)):
    return {"id": current_user.get("id"), "username": current_user.get("username"), "role": current_user.get("role_name")}


@app.post("/api/users")
def api_create_user(full_name: str, username: str, password: str, role_id: int, location_id: Optional[int] = None, current_user: dict = Depends(get_current_user)):
    # only admin can create users
    if current_user.get("role_name") != "Admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    res = user_service.create_user(full_name, username, password, role_id, location_id, is_active=True)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("message"))
    return res


@app.post("/api/users/{user_id}/password")
def api_change_password(user_id: int, new_password: str, current_user: dict = Depends(get_current_user)):
    # user can change own password or admin can reset
    if current_user.get("id") == user_id or current_user.get("role_name") == "Admin":
        # admin reset
        if current_user.get("id") == user_id:
            # require current password (not provided here in API minimal)
            raise HTTPException(status_code=400, detail="Use dedicated endpoint with current password")
        else:
            res = user_service.admin_reset_password(current_user.get("id"), user_id, new_password)
            if not res.get("success"):
                raise HTTPException(status_code=400, detail=res.get("message"))
            return res
    raise HTTPException(status_code=403, detail="Forbidden")
