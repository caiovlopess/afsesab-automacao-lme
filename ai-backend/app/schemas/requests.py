"""Payloads de entrada com validação estrita + re-sanitização server-side."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic.alias_generators import to_camel

from ..services.sanitizer import sanitize_payload

MAX_STRING = 500
MAX_LIST = 50


class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        str_strip_whitespace=True,
        extra="forbid",
    )


SafeString = Annotated[str, Field(min_length=1, max_length=MAX_STRING)]


def _clean(value: str) -> str:
    """Remove caracteres de controle e reduz espaços."""
    cleaned = "".join(ch for ch in value if ch >= " " or ch in "\t\n")
    return " ".join(cleaned.split())


class ContextPayload(CamelModel):
    """Contexto clínico já sanitizado no cliente (revalidado aqui)."""

    drugs: list[SafeString] = Field(default_factory=list, max_length=MAX_LIST)
    dosages: list[SafeString] = Field(default_factory=list, max_length=MAX_LIST)
    cid10: list[SafeString] = Field(default_factory=list, max_length=MAX_LIST)
    clinical_terms: list[SafeString] = Field(default_factory=list, max_length=MAX_LIST)
    safe_text: str = Field(default="", max_length=4000)
    captured_at: datetime
    source: Literal["afsesab"] = "afsesab"

    @field_validator("drugs", "dosages", "cid10", "clinical_terms", mode="before")
    @classmethod
    def _clean_list(cls, values: object) -> object:
        if not isinstance(values, list):
            return []
        return [_clean(str(v)) for v in values if isinstance(v, str) and _clean(str(v))]

    @field_validator("safe_text", mode="before")
    @classmethod
    def _clean_text(cls, value: object) -> str:
        return _clean(str(value or ""))

    @model_validator(mode="after")
    def _resanitize(self) -> "ContextPayload":
        """Zero-trust: ignora o que veio do cliente e recalcula os sinais."""
        clean = sanitize_payload(self.model_dump())
        self.drugs = clean["drugs"]  # type: ignore[assignment]
        self.dosages = clean["dosages"]  # type: ignore[assignment]
        self.cid10 = clean["cid10"]  # type: ignore[assignment]
        self.clinical_terms = clean["clinical_terms"]  # type: ignore[assignment]
        self.safe_text = clean["safe_text"]  # type: ignore[assignment]
        return self

    @property
    def summary(self) -> str:
        return ", ".join([
            *self.drugs,
            *self.dosages,
            *self.cid10,
            *self.clinical_terms,
        ])[:1000]


class AnalyzeContextRequest(CamelModel):
    context: ContextPayload
    # O cliente envia o contexto no corpo raiz; mantemos compatibilidade
    # aceitando também o formato achatado via validador abaixo.
    include_sources: bool = True

    @model_validator(mode="before")
    @classmethod
    def _flatten(cls, values: object) -> object:
        if isinstance(values, dict) and "context" not in values and "drugs" in values:
            include_sources = values.get("includeSources", values.get("include_sources", True))
            context_data = {
                k: v for k, v in values.items()
                if k not in {"includeSources", "include_sources"}
            }
            return {"context": context_data, "includeSources": include_sources}
        return values
