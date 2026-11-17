"""Usuário de acesso ao aplicativo (login local do trabalho acadêmico)."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import String, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column

from ..core.database import Base


class AppUser(Base):
    __tablename__ = "app_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    salt: Mapped[str] = mapped_column(String(64), nullable=False)
    nome: Mapped[str] = mapped_column(String(120), default="Usuário")
    perfil: Mapped[str] = mapped_column(String(40), default="Farmacêutico")
    unidade: Mapped[str] = mapped_column(String(120), default="5ª DIRETORIA REGIONAL DE SAÚDE - GANDU")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
