"""Insights de IA para o administrador."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from ...core.database import get_session
from ...core.logging import get_logger
from ...core.security import verify_internal_token
from ...schemas.responses import AdminInsightsResponse
from ...services.admin_ask import AdminAskService
from ...services.prompt_guard import PromptGuard
from sqlalchemy.orm import Session

router = APIRouter()
logger = get_logger(__name__)


class InsightsRequest(BaseModel):
    foco: str = Field(default="geral", max_length=80)


class AskRequest(BaseModel):
    pergunta: str = Field(min_length=3, max_length=300)


class AskResponse(BaseModel):
    answer: str
    columns: list[str]
    rows: list[list[object]]
    intent: str
    model: str
    suggestions: list[str]
    security_notice: str = ""


@router.post("/admin/audit")
async def admin_audit(
    request: Request,
    db: Session = Depends(get_session),
    _auth: None = Depends(verify_internal_token),
) -> dict[str, object]:
    achados = request.app.state.insights.audit(db)
    return {"total": len(achados), "achados": achados}


@router.post("/admin/ask", response_model=AskResponse)
async def admin_ask(
    payload: AskRequest,
    request: Request,
    db: Session = Depends(get_session),
    _auth: None = Depends(verify_internal_token),
) -> AskResponse:
    check = PromptGuard.analyze(payload.pergunta)
    if not check.safe:
        # A consulta é determinística (roteador), então nenhuma instrução é executada.
        # Ainda assim neutralizamos o texto e avisamos o usuário.
        logger.warning("Prompt injection detectado em /admin/ask: %s", check.reasons[:2])
        result = AdminAskService(request.app.state.settings).answer("visão geral", db)
        result["security_notice"] = "Entrada bloqueada: foi detectada uma tentativa de manipulação de instruções."
        return AskResponse(**result)

    result = AdminAskService(request.app.state.settings).answer(check.sanitized, db)
    return AskResponse(**result)


@router.post("/admin/insights", response_model=AdminInsightsResponse)
async def admin_insights(
    payload: InsightsRequest,
    request: Request,
    db: Session = Depends(get_session),
    _auth: None = Depends(verify_internal_token),
) -> AdminInsightsResponse:
    check = PromptGuard.analyze(payload.foco, max_length=80)
    foco = "geral" if not check.safe else check.sanitized
    if not check.safe:
        logger.warning("Prompt injection detectado em /admin/insights: %s", check.reasons[:2])
    result = request.app.state.insights.generate(db, foco)
    if not check.safe and not result.resumo.startswith("Entrada bloqueada"):
        result.resumo = "Entrada bloqueada por segurança. " + result.resumo
    return result
