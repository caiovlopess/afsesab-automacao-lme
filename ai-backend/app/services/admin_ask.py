"""Consultas em linguagem natural sobre a base do AF Copilot.

O router é determinístico (garante resposta correta mesmo sem modelo); o Gemini
apenas redige a frase final usando UM RESUMO AGREGADO — sem nomes de pacientes.
"""

from __future__ import annotations

import re
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..core.config import Settings
from ..core.logging import get_logger
from ..models.sql_models import FictionalLme, FictionalUser
from .fictional_views import FORNECEDORES, MEDICAMENTOS, build_master

logger = get_logger(__name__)


class AdminAskService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def answer(self, question: str, db: Session) -> dict[str, Any]:
        q = question.strip().lower()
        if "fornecedor" in q or "fornecedores" in q or "cnpj" in q:
            return self._suppliers(q)
        if "lme" in q and any(word in q for word in (
            "não autorizada", "nao autorizada", "não foram autorizadas",
            "nao foram autorizadas", "autorizadas ainda", "sem autorização",
            "sem autorizacao", "pendente", "aguardando",
        )):
            return self._pending_lmes(db)
        if "medicamento" in q or "remédio" in q:
            return self._medicines(q)
        if "cid" in q:
            return self._by_cid(q, db)
        return self._patients(q, db) if q.strip() else self._overview(db)

    # ------------------------------------------------------------------ #
    def _suppliers(self, question: str) -> dict[str, Any]:
        cities = ["salvador", "são paulo", "sao paulo", "recife", "porto alegre",
                  "belo horizonte", "feira de santana"]
        chosen = next((c for c in cities if c in question), None)
        rows = FORNECEDORES
        if chosen:
            alias = {"sao paulo": "são paulo"}.get(chosen, chosen)
            rows = [f for f in FORNECEDORES if alias in f[2].lower()]
        cols = ["CNPJ", "Razão Social", "Cidade", "Contato", "Telefone", "Endereço"]
        data = [[f[i] for i in range(6)] for f in rows]
        if chosen:
            text = f"Fornecedores localizados em {chosen.title()}: {len(data)} registro(s)."
        else:
            text = f"Encontrei {len(data)} fornecedores cadastrados."
        return self._result(text, cols, data, "fornecedores")

    def _pending_lmes(self, db: Session) -> dict[str, Any]:
        # Mesma base determinística da tabela, para IDs e pacientes coincidirem.
        users = db.query(FictionalUser).order_by(FictionalUser.id).limit(100).all()
        master = build_master(users, db)
        pendentes = [(i + 1, r) for i, r in enumerate(master) if r["Status"] == "pendente"]
        cols = ["LME", "Medicamento", "Paciente", "Unidade", "CID", "Emissão"]
        data = [
            [f"LME-{idx:06d}", r["Medicamento"], r["Paciente"], r["Unidade"],
             r["CID-10"], r["Data"]]
            for idx, r in pendentes[:100]
        ]
        total = db.query(func.count(FictionalLme.id)).filter(
            FictionalLme.status == "pendente").scalar() or 0
        return self._result(
            f"Existem {total} LMEs aguardando autorização. Relação abaixo (até 100):",
            cols, data, "lmes-pendentes",
        )

    def _medicines(self, question: str) -> dict[str, Any]:
        term = re.sub(r"(qual|quais|o|os|a|as|medicamento|medicamentos|de|do|da)\b", "", question).strip()
        rows = [m for m in MEDICAMENTOS if not term or term in " ".join(m).lower()]
        cols = ["Código", "Nome", "Princípio Ativo", "Apresentação"]
        data = [[m[0], m[1], m[2], m[3]] for m in rows[:100]]
        return self._result(f"Medicamentos encontrados: {len(data)}.", cols, data, "medicamentos")

    def _overview(self, db: Session) -> dict[str, Any]:
        total = db.query(func.count(FictionalLme.id)).scalar() or 0
        users = db.query(func.count(FictionalUser.id)).scalar() or 0
        by_status = dict(db.query(FictionalLme.status, func.count(FictionalLme.id))
                         .group_by(FictionalLme.status).all())
        cols = ["Indicador", "Valor"]
        data = [["LMEs no sistema", total], ["Pacientes", users],
                *[[k, v] for k, v in by_status.items()]]
        return self._result("Visão geral da operação:", cols, data, "visao-geral")

    def _by_cid(self, question: str, db: Session) -> dict[str, Any]:
        match = re.search(r"\b([A-TV-Z]\d{2}(?:\.\d{1,4})?)\b", question.upper())
        cid = match.group(1) if match else ""
        q = db.query(FictionalLme, FictionalUser).join(
            FictionalUser, FictionalLme.user_id == FictionalUser.id
        )
        if cid:
            q = q.filter(FictionalLme.cid10 == cid)
        rows = q.order_by(FictionalLme.id).limit(100).all()
        cols = ["LME", "Medicamento", "Paciente", "CID", "Status"]
        data = [[f"LME-{l.id:06d}", l.medicamento, u.nome, l.cid10, l.status] for l, u in rows]
        return self._result(f"LMEs por CID {cid or 'não informado'}: {len(data)} registro(s).",
                            cols, data, "lmes-por-cid")

    def _patients(self, question: str, db: Session) -> dict[str, Any]:
        term = re.sub(r"(qual|quais|mostre|liste|o|a|os|as|de|do|da)\b", "", question).strip()
        users = db.query(FictionalUser)
        if term:
            users = users.filter(FictionalUser.nome.ilike(f"%{term}%"))
        rows = users.order_by(FictionalUser.id).limit(100).all()
        cols = ["ID", "Paciente", "CNS", "Unidade"]
        data = [[u.id, u.nome, u.cns_ficticio, u.unidade] for u in rows]
        return self._result(f"Pacientes encontrados: {len(data)}.", cols, data, "pacientes")

    # ------------------------------------------------------------------ #
    def _result(self, text: str, cols: list[str], data: list[list[Any]], intencao: str) -> dict[str, Any]:
        self.text = text
        return {
            "answer": text,
            "columns": cols,
            "rows": data,
            "intent": intencao,
            "model": "consulta-direta",
            "suggestions": [
                "Qual o fornecedor de Salvador?",
                "Liste as LMEs que não foram autorizadas ainda",
                "Quais medicamentos estão cadastrados?",
            ],
        }
