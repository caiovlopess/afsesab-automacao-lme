"""Insights de IA para o administrador do AF Copilot.

Segurança LGPD: somente AGREGADOS (contagens, valores, medicamentos, CIDs)
saem do backend. Nenhum nome, CNS, e-mail ou prontuário é enviado ao modelo.
"""

from __future__ import annotations

import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from typing import Any

from sqlalchemy import Integer, func
from sqlalchemy.orm import Session

from ..core.config import Settings
from ..core.logging import get_logger
from ..models.sql_models import FictionalLme, FictionalUser
from ..schemas.responses import AdminInsightsResponse

logger = get_logger(__name__)
_JSON = re.compile(r"\{.*\}", re.DOTALL)


class AdminInsightsService:
    CACHE_TTL = 300  # 5 minutos

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._models: dict[str, Any] = {}
        self._cache: dict[str, tuple[float, Any]] = {}

    def _model(self, name: str) -> Any:
        if name not in self._models:
            from langchain_google_genai import ChatGoogleGenerativeAI

            self._models[name] = ChatGoogleGenerativeAI(
                model=name,
                google_api_key=self.settings.gemini_api_key,
                temperature=0.3,
                timeout=30,
                max_retries=0,
                transport="rest",
            )
        return self._models[name]

    def _aggregates(self, db: Session) -> dict[str, Any]:
        total_lmes = db.query(func.count(FictionalLme.id)).scalar() or 0
        total_users = db.query(func.count(FictionalUser.id)).scalar() or 0
        total_value = db.query(func.coalesce(func.sum(FictionalLme.valor), 0)).scalar() or 0
        by_status = dict(db.query(FictionalLme.status, func.count(FictionalLme.id))
                         .group_by(FictionalLme.status).all())
        top_meds = db.query(FictionalLme.medicamento, func.count(FictionalLme.id)
                            ).group_by(FictionalLme.medicamento
                                       ).order_by(func.count(FictionalLme.id).desc()).limit(6).all()
        top_cids = db.query(FictionalLme.cid10, func.count(FictionalLme.id)
                            ).group_by(FictionalLme.cid10
                                       ).order_by(func.count(FictionalLme.id).desc()).limit(6).all()
        return {
            "total_lmes": total_lmes,
            "total_pacientes": total_users,
            "valor_total": round(float(total_value), 2),
            "por_status": by_status,
            "medicamentos_mais_frequentes": [{"medicamento": m, "quantidade": q} for m, q in top_meds],
            "cids_mais_frequentes": [{"cid": c, "quantidade": q} for c, q in top_cids],
        }

    def generate(self, db: Session, foco: str = "geral") -> AdminInsightsResponse:
        cached = self._cache.get(foco)
        if cached and time.time() - cached[0] < self.CACHE_TTL:
            logger.info("Insights em cache para foco=%s", foco)
            return cached[1]
        result = self._generate_uncached(db, foco)
        self._cache[foco] = (time.time(), result)
        return result

    def _generate_uncached(self, db: Session, foco: str = "geral") -> AdminInsightsResponse:
        data = self._aggregates(db)
        fallback = self._fallback_insights(data, foco)

        if not self.settings.gemini_api_key:
            return AdminInsightsResponse(**fallback, model="sem-chave")

        prompt = f"""Você é um analista de operações de uma Diretoria Regional de Saúde.
Analise os AGREGADOS abaixo (sem dados pessoais) e ajude o administrador a decidir.

FOCO: {foco}
DADOS:
{json.dumps(data, ensure_ascii=False, indent=2)}

Retorne JSON estrito com:
- "resumo": frase curta de 1 linha;
- "insights": 3 a 5 observações objetivas com números;
- "alertas": 1 a 3 pontos de atenção (ex.: atraso em faturamento);
- "acoes": 2 a 4 ações práticas priorizadas para a equipe.
Use português brasileiro. Não invente dados que não estejam no JSON."""

        models = [self.settings.gemini_model, *self.settings.gemini_fallback_models]
        for name in dict.fromkeys(models):
            try:
                # Limite duro por modelo (sem esperar a thread presa no shutdown).
                pool = ThreadPoolExecutor(max_workers=1)
                try:
                    future = pool.submit(self._model(name).invoke, prompt)
                    raw = future.result(timeout=12).content
                finally:
                    pool.shutdown(wait=False, cancel_futures=True)
                parsed = self._parse(str(raw))
                if parsed:
                    return AdminInsightsResponse(
                        resumo=str(parsed.get("resumo", ""))[:400] or fallback["resumo"],
                        insights=self._list(parsed.get("insights")) or fallback["insights"],
                        alertas=self._list(parsed.get("alertas")) or fallback["alertas"],
                        acoes=self._list(parsed.get("acoes")) or fallback["acoes"],
                        model=name,
                        periodo="11/2026",
                    )
            except Exception as exc:  # noqa: BLE001
                logger.warning("Modelo %s falhou em insights: %s", name, exc)

        return AdminInsightsResponse(**fallback, model="fallback-local")

    def audit(self, db: Session) -> list[dict[str, str]]:
        """Achados acionáveis para o administrador (sem dados pessoais no modelo)."""
        achados: list[dict[str, str]] = []

        pendentes = db.query(func.count(FictionalLme.id)).filter(
            FictionalLme.status == "pendente").scalar() or 0
        if pendentes:
            achados.append({
                "titulo": f"{pendentes} LMEs aguardando autorização",
                "detalhe": "Acima de 10% do volume total pode estourar o prazo de análise.",
                "severidade": "alta",
            })

        por_med = db.query(
            FictionalLme.medicamento,
            func.count(FictionalLme.id),
            func.sum(func.cast(FictionalLme.status == "dispensada", Integer)),
        ).group_by(FictionalLme.medicamento).having(func.count(FictionalLme.id) >= 200).all()
        for med, total, dispensadas in sorted(por_med, key=lambda x: (x[2] or 0) / max(1, x[1]))[:3]:
            taxa = (dispensadas or 0) / max(1, total) * 100
            if taxa < 35:
                achados.append({
                    "titulo": f"Baixa conversão em {med}",
                    "detalhe": f"Apenas {taxa:.1f}% das {total} LMEs foram dispensadas.",
                    "severidade": "media",
                })

        por_unidade = db.query(
            FictionalUser.unidade, func.count(FictionalLme.id)
        ).join(FictionalUser, FictionalLme.user_id == FictionalUser.id) \
            .filter(FictionalLme.status == "pendente") \
            .group_by(FictionalUser.unidade) \
            .order_by(func.count(FictionalLme.id).desc()).limit(3).all()
        for unidade, total in por_unidade:
            achados.append({
                "titulo": f"Pendências concentradas em {unidade}",
                "detalhe": f"{total} LMEs pendentes — priorizar triagem nesta unidade.",
                "severidade": "media",
            })

        duplicados = db.query(
            FictionalLme.user_id, func.count(FictionalLme.id)
        ).group_by(FictionalLme.user_id).having(func.count(FictionalLme.id) > 4).limit(3).all()
        for user_id, total in duplicados:
            achados.append({
                "titulo": f"Paciente com {total} LMEs",
                "detalhe": f"Registro {user_id} — verificar necessidade de novas autorizações.",
                "severidade": "baixa",
            })

        return achados[:8]

    @staticmethod
    def _fallback_insights(data: dict[str, Any], foco: str) -> dict[str, Any]:
        status = data.get("por_status", {})
        faturadas = int(status.get("faturada", 0))
        pendentes = int(status.get("pendente", 0))
        top = (data.get("medicamentos_mais_frequentes") or [{}])[0]
        return {
            "resumo": (
                f"{data.get('total_lmes', 0)} LMEs ativas, "
                f"{faturadas} faturadas e {pendentes} aguardando análise."
            ),
            "insights": [
                f"Volume total: {data.get('total_lmes', 0)} LMEs para {data.get('total_pacientes', 0)} pacientes.",
                f"Faturamento acumulado: R$ {data.get('valor_total', 0):,.2f}.",
                f"Medicamento mais frequente: {top.get('medicamento', '—')} ({top.get('quantidade', 0)} LMEs).",
                f"Distribuição: {', '.join(f'{k}: {v}' for k, v in status.items())}.",
            ],
            "alertas": [
                f"{pendentes} LMEs pendentes podem impactar o prazo de dispensação."
            ] if pendentes else [],
            "acoes": [
                "Priorizar a análise das LMEs pendentes mais antigas.",
                "Conferir documentação dos processos antes do faturamento.",
                "Monitorar estoque dos medicamentos mais frequentes.",
            ],
        }

    @staticmethod
    def _parse(raw: str) -> dict[str, Any]:
        match = _JSON.search(raw)
        text = match.group(0) if match else raw
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {}

    @staticmethod
    def _list(value: Any) -> list[str]:
        if isinstance(value, list):
            return [str(v)[:400] for v in value if v][:8]
        if isinstance(value, str) and value.strip():
            return [value.strip()[:400]]
        return []
