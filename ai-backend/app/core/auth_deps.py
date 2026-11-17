"""Autenticação de usuário e controle de perfil (RBAC)."""

from __future__ import annotations

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from ..models.app_user import AppUser
from ..models.operational import AppSession
from .database import get_session


def get_current_user(
    x_session_token: str = Header(default="", alias="X-Session-Token"),
    db: Session = Depends(get_session),
) -> AppUser:
    if not x_session_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sessão ausente.")
    session = db.query(AppSession).filter(
        AppSession.token == x_session_token, AppSession.revoked == 0
    ).first()
    if session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sessão inválida.")
    user = db.query(AppUser).filter(AppUser.username == session.username).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário não encontrado.")
    return user


def require_perfil(*perfis: str):
    """Dependency que só permite os perfis informados."""

    def _check(user: AppUser = Depends(get_current_user)) -> AppUser:
        if user.perfil not in perfis:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Perfil '{user.perfil}' não autorizado para esta operação.",
            )
        return user

    return _check
