"""POST /api/v1/analyze-context — RAG de protocolos clínicos."""

from __future__ import annotations

import hashlib

from fastapi import APIRouter, Depends, Request

from ...core.security import verify_internal_token
from ...models.domain import AnalysisCache
from ...schemas.requests import AnalyzeContextRequest
from ...schemas.responses import AnalysisResponse

router = APIRouter()


@router.post("/analyze-context", response_model=AnalysisResponse)
async def analyze_context(
    payload: AnalyzeContextRequest,
    request: Request,
    _auth: None = Depends(verify_internal_token),
) -> AnalysisResponse:
    services = request.app.state
    context = payload.context

    cache_key = hashlib.sha256(context.safe_text.encode("utf-8")).hexdigest()[:32]
    cached = services.cache.get_cached(cache_key)
    if cached is not None:
        services.audit.log_event("cache_hit", {"key": cache_key})
        return AnalysisResponse.model_validate(cached)

    result = services.rag.analyze(context)
    services.cache.save(
        AnalysisCache(key=cache_key, response=result.model_dump(mode="json"))
    )
    services.audit.log_event(
        "analyze_context",
        {"drugs": context.drugs, "cid10": context.cid10, "sources": result.sources},
    )
    return result
