"""Implementação em memória e stub MongoDB para auditoria/cache."""

from __future__ import annotations

from typing import Any

from ..core.config import get_settings
from ..core.logging import get_logger
from ..models.domain import AnalysisCache, AuditLog
from .base import Repository, T

logger = get_logger(__name__)


class InMemoryRepository(Repository[T, str]):
    """Implementação temporária usada na Fase 1."""

    def __init__(self) -> None:
        self._items: dict[str, T] = {}

    def save(self, entity: T) -> None:  # type: ignore[override]
        key = getattr(entity, "key", None) or getattr(entity, "event", "log")
        self._items[str(key)] = entity

    def get(self, key: str) -> T | None:
        return self._items.get(key)

    def list(self, limit: int = 100) -> list[T]:
        return list(self._items.values())[:limit]


class AuditRepository(InMemoryRepository[AuditLog]):
    def log_event(self, event: str, payload: dict[str, Any]) -> None:
        # Defesa em profundidade: nunca persistir chaves típicas de PII.
        blocked = {"cpf", "cns", "name", "nome", "birth_date", "prontuario", "email", "phone"}
        safe = {k: v for k, v in payload.items() if k.lower() not in blocked}
        self.save(AuditLog(event=event, payload=safe))


class QueryCacheRepository(InMemoryRepository[AnalysisCache]):
    def get_cached(self, key: str) -> dict[str, Any] | None:
        item = self.get(key)
        return item.response if item else None


class MongoAuditRepository(AuditRepository):
    """Stub para Fase 2: trocar a injeção quando `database_url` estiver definido.

    Exemplo de uso futuro:
        client = MongoClient(settings.database_url)
        collection = client["af_copilot"]["audit_logs"]
        collection.insert_one(log.model_dump(mode="json"))
    """

    def __init__(self, database_url: str) -> None:
        super().__init__()
        self.database_url = database_url
        logger.info("MongoAuditRepository preparado (Fase 2): %s", database_url.split("@")[-1])


def build_repositories() -> tuple[AuditRepository, QueryCacheRepository]:
    """Fábrica que permitirá alternar para Mongo via config na Fase 2."""
    settings = get_settings()
    audit: AuditRepository
    if settings.database_url:
        audit = MongoAuditRepository(settings.database_url)
    else:
        audit = AuditRepository()
    return audit, QueryCacheRepository()
