"""Login local do aplicativo (usuário do trabalho acadêmico)."""

from __future__ import annotations

import hashlib
import hmac
import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ...core.database import get_session
from ...models.app_user import AppUser
from ...models.operational import AppSession, AuditLog

router = APIRouter()


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=200)


class LoginResponse(BaseModel):
    username: str
    nome: str
    perfil: str
    unidade: str
    session_token: str


def hash_password(password: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 210_000).hex()


@router.post("/auth/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_session)) -> LoginResponse:
    user = db.query(AppUser).filter(AppUser.username == payload.username).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário ou senha inválidos.")

    candidate = hash_password(payload.password, bytes.fromhex(user.salt))
    if not hmac.compare_digest(candidate, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário ou senha inválidos.")

    token = secrets.token_urlsafe(32)
    db.add(AppSession(token=token, username=user.username))
    db.add(AuditLog(
        actor=user.username, acao="login", entidade="sessao",
        entidade_id=user.username, detalhes=f"perfil={user.perfil}",
    ))
    db.commit()
    return LoginResponse(
        username=user.username,
        nome=user.nome,
        perfil=user.perfil,
        unidade=user.unidade,
        session_token=token,
    )
