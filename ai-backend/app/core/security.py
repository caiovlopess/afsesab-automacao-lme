"""Autenticação local e CORS restrito.

O backend gera um token de sessão na inicialização e o grava em
`runtime/auth_token` com permissões restritas. O Electron lê esse arquivo.
Assim, nenhum segredo é versionado ou embarcado no cliente.
"""

from __future__ import annotations

import hmac
import secrets
from pathlib import Path

from fastapi import Header, HTTPException, status

from .config import get_settings


def ensure_auth_token() -> str:
    """Cria (ou lê) o token local e retorna seu valor."""
    settings = get_settings()
    path: Path = settings.auth_token_path
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists():
        token = path.read_text(encoding="utf-8").strip()
        if len(token) >= 16:
            return token

    token = secrets.token_urlsafe(32)
    path.write_text(token, encoding="utf-8")
    try:  # Unix: 0600. No Windows chmod é limitado, mas o arquivo fica no perfil do usuário.
        path.chmod(0o600)
    except OSError:
        pass
    return token


def verify_internal_token(
    x_internal_auth_token: str = Header(default="", alias="X-Internal-Auth-Token"),
) -> None:
    """Dependency FastAPI que valida o cabeçalho de autenticação interna."""
    expected = ensure_auth_token()
    if not x_internal_auth_token or not hmac.compare_digest(x_internal_auth_token, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token interno inválido ou ausente.",
            headers={"WWW-Authenticate": "InternalToken"},
        )


def configure_cors(app: object) -> None:
    """Aplica CORS restrito às origens configuradas."""
    from fastapi.middleware.cors import CORSMiddleware

    settings = get_settings()
    app.add_middleware(  # type: ignore[attr-defined]
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["POST", "GET", "OPTIONS"],
        allow_headers=["Content-Type", "X-Internal-Auth-Token"],
    )
