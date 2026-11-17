"""Contratos de saída da API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class CamelResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class AnalysisResponse(CamelResponse):
    inclusion_criteria: list[str] = Field(default_factory=list)
    required_exams: list[str] = Field(default_factory=list)
    dispensing_alerts: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    passos: list[str] = Field(default_factory=list)
    exemplo: str = ""
    disclaimer: str = "Ferramenta de apoio à decisão; confirme sempre o PCDT vigente."


class ExtractedData(CamelResponse):
    active_ingredient: str = ""
    concentration: str = ""
    posology: str = ""
    cid: str = ""
    issue_date: str = ""


class ValidationResponse(CamelResponse):
    extracted: ExtractedData = Field(default_factory=ExtractedData)
    inconsistencies: list[str] = Field(default_factory=list)
    status: Literal["ok", "warning", "error"] = "ok"
    disclaimer: str = "Validação automatizada; a decisão final é do farmacêutico responsável."


class AdminInsightsResponse(CamelResponse):
    resumo: str
    insights: list[str] = Field(default_factory=list)
    alertas: list[str] = Field(default_factory=list)
    acoes: list[str] = Field(default_factory=list)
    model: str = ""
    periodo: str = ""


class HealthResponse(CamelResponse):
    status: str
    version: str
    vector_store_ready: bool = False
