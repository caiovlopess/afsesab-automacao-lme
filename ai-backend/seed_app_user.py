"""Cria/atualiza o usuário de login do aplicativo.

A senha NÃO fica no código: é lida de variáveis de ambiente.
    AF_APP_USER=... AF_APP_PASSWORD=... python seed_app_user.py
"""

from __future__ import annotations

import os
import secrets

from app.api.v1.auth import hash_password
from app.core.database import SessionLocal, init_db
from app.models.app_user import AppUser


def main() -> None:
    username = os.environ.get("AF_APP_USER", "").strip()
    password = os.environ.get("AF_APP_PASSWORD", "")
    if not username or not password:
        raise SystemExit("Defina AF_APP_USER e AF_APP_PASSWORD no ambiente.")

    init_db()
    session = SessionLocal()
    try:
        salt = secrets.token_bytes(16)
        user = session.query(AppUser).filter(AppUser.username == username).first()
        if user is None:
            user = AppUser(username=username)
            session.add(user)
        user.salt = salt.hex()
        user.password_hash = hash_password(password, salt)
        user.nome = "Henrique Carvalho"
        user.perfil = "Farmacêutico"
        session.commit()
        print(f"Usuário de acesso criado/atualizado: {username} (senha armazenada como hash PBKDF2).")
    finally:
        session.close()


if __name__ == "__main__":
    main()
