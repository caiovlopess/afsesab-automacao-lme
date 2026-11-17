"""Modelos de domínio persistidos na Fase 2 (logs anonimizados, histórico, cache)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AuditLog(BaseModel):
    """Registro de auditoria SEM dados pessoais (somente sinais clínicos)."""

    event: str
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utcnow)


class AnalysisCache(BaseModel):
    key: str
    response: dict[str, Any]
    created_at: datetime = Field(default_factory=utcnow)
