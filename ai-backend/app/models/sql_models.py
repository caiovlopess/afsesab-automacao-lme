"""Modelos SQLAlchemy — massa fictícia (nenhum dado real de paciente)."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import ForeignKey, Index, String, Float, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class FictionalUser(Base):
    """Paciente fictício. O sufixo @example.invalid marca dados sintéticos."""

    __tablename__ = "fictional_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(160), unique=True, index=True, nullable=False)
    cns_ficticio: Mapped[str] = mapped_column(String(15), unique=True, index=True, nullable=False)
    unidade: Mapped[str] = mapped_column(String(80), default="UBS Fictícia Centro")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    lmes: Mapped[list["FictionalLme"]] = relationship(back_populates="paciente")


class CatalogMedication(Base):
    """Medicamento cadastrado pelo administrador no painel."""

    __tablename__ = "catalog_medications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    codigo: Mapped[str] = mapped_column(String(30), unique=True, index=True, nullable=False)
    nome: Mapped[str] = mapped_column(String(160), nullable=False)
    principio: Mapped[str] = mapped_column(String(160), nullable=False)
    apresentacao: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class FictionalLme(Base):
    """LME fictícia com status de faturamento."""

    __tablename__ = "fictional_lmes"
    __table_args__ = (
        Index("ix_lme_status", "status"),
        Index("ix_lme_usuario", "user_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("fictional_users.id"), nullable=False)
    medicamento: Mapped[str] = mapped_column(String(160), nullable=False)
    cid10: Mapped[str] = mapped_column(String(12), nullable=False)
    dosagem: Mapped[str] = mapped_column(String(60), default="")
    status: Mapped[str] = mapped_column(String(24), nullable=False)  # pendente|autorizada|faturada|dispensada
    valor: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    paciente: Mapped[FictionalUser] = relationship(back_populates="lmes")
