"""Repository Pattern — abstração preparada para MongoDB (Fase 2)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

T = TypeVar("T")
K = TypeVar("K")


class Repository(ABC, Generic[T, K]):
    @abstractmethod
    def save(self, entity: T) -> None:
        """Persiste ou atualiza uma entidade."""

    @abstractmethod
    def get(self, key: K) -> T | None:
        """Recupera uma entidade pela chave."""

    @abstractmethod
    def list(self, limit: int = 100) -> list[T]:
        """Lista entidades com limite."""
