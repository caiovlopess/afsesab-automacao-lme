"""Consulta à massa FICTÍCIA (usuários e LMEs) armazenada em SQLite."""

from __future__ import annotations

from typing import Literal

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from ...core.auth_deps import get_current_user, require_perfil
from ...core.database import get_session
from ...core.security import verify_internal_token
from ...models.app_user import AppUser
from ...models.operational import AuditLog
from ...models.sql_models import CatalogMedication, FictionalLme, FictionalUser
from ...services.fictional_views import build_view
from ...services.fictional_views import build_master
from ...services.lme_pdf import build_lme_pdf_from_row
from ...services.report_export import build_csv, build_pdf, filename as report_filename

router = APIRouter()

# Chave de view: somente letras minúsculas, dígitos e underscore.
VIEW_KEY_PATTERN = r"^[a-z0-9_]{2,40}$"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nome: str
    email: str
    unidade: str


class LmeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    medicamento: str
    cid10: str
    dosagem: str
    status: str
    valor: float


class MedicationIn(BaseModel):
    nome: str = Field(min_length=2, max_length=160, pattern=r"^[\w\sÀ-ÿ.\-/()]+$")
    principio: str = Field(min_length=2, max_length=160, pattern=r"^[\w\sÀ-ÿ.\-/()]+$")
    apresentacao: str = Field(min_length=2, max_length=120, pattern=r"^[\w\sÀ-ÿ.\-/()]+$")


class MedicationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    codigo: str
    nome: str
    principio: str
    apresentacao: str


@router.post("/fictional/medicamentos", response_model=MedicationOut)
def create_medication(
    payload: MedicationIn,
    db: Session = Depends(get_session),
    user: AppUser = Depends(require_perfil("Administrador", "Farmacêutico")),
    _auth: None = Depends(verify_internal_token),
) -> MedicationOut:
    """Cadastro de medicamento pelo administrador (persistido no SQLite)."""
    count = db.query(func.count(CatalogMedication.id)).scalar() or 0
    record = CatalogMedication(
        codigo=f"SIM-{20000 + count + 1:06d}",
        nome=payload.nome.strip(),
        principio=payload.principio.strip(),
        apresentacao=payload.apresentacao.strip(),
    )
    db.add(record)
    db.add(AuditLog(
        actor=user.username, acao="cadastrar_medicamento", entidade="medicamento",
        entidade_id=record.codigo, detalhes=f"{record.nome} | {record.apresentacao}",
    ))
    db.commit()
    db.refresh(record)
    return MedicationOut.model_validate(record)


class StatusChange(BaseModel):
    status: Literal["pendente", "autorizada", "faturada", "dispensada"]
    motivo: str = Field(default="", max_length=300)


@router.post("/fictional/lmes/{lme_id}/status")
def change_lme_status(
    lme_id: int = Path(ge=1, le=100000),
    payload: StatusChange = ...,
    db: Session = Depends(get_session),
    user: AppUser = Depends(require_perfil("Administrador", "Farmacêutico")),
    _auth: None = Depends(verify_internal_token),
) -> dict[str, object]:
    """Ação real sobre a LME — altera status e grava auditoria imutável."""
    lme = db.query(FictionalLme).filter(FictionalLme.id == lme_id).first()
    if lme is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="LME não encontrada.")
    anterior = str(lme.status)
    lme.status = payload.status
    db.add(AuditLog(
        actor=user.username,
        acao="alterar_status_lme",
        entidade="lme",
        entidade_id=str(lme_id),
        detalhes=f"{anterior}->{payload.status} | motivo: {payload.motivo or 'não informado'}",
    ))
    db.commit()
    return {"id": lme_id, "status_anterior": anterior, "status": payload.status, "por": user.username}


@router.get("/fictional/audit")
def list_audit(
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_session),
    _user: AppUser = Depends(require_perfil("Administrador", "Auditor", "Farmacêutico")),
    _auth: None = Depends(verify_internal_token),
) -> list[dict[str, object]]:
    logs = db.query(AuditLog).order_by(AuditLog.id.desc()).limit(limit).all()
    return [{
        "id": log.id, "actor": log.actor, "acao": log.acao, "entidade": log.entidade,
        "entidade_id": log.entidade_id, "detalhes": log.detalhes,
        "created_at": log.created_at.isoformat() if log.created_at else "",
    } for log in logs]


@router.get("/fictional/audit/export")
def export_audit(
    formato: str = Query("csv", pattern="^(csv|pdf)$"),
    db: Session = Depends(get_session),
    _user: AppUser = Depends(require_perfil("Administrador", "Auditor")),
    _auth: None = Depends(verify_internal_token),
) -> Response:
    logs = db.query(AuditLog).order_by(AuditLog.id.desc()).limit(500).all()
    view = {
        "title": "Log de Auditoria",
        "columns": ["ID", "Usuário", "Ação", "Entidade", "Registro", "Detalhes", "Data"],
        "rows": [[l.id, l.actor, l.acao, l.entidade, l.entidade_id, l.detalhes,
                  l.created_at.strftime("%d/%m/%Y %H:%M") if l.created_at else ""] for l in logs],
    }
    content, mime = (build_pdf(view), "application/pdf") if formato == "pdf" \
        else (build_csv(view), "text/csv; charset=utf-8")
    return Response(content=content, media_type=mime,
                    headers={"Content-Disposition": f'attachment; filename="auditoria.{formato}"'})


class StatsOut(BaseModel):
    total_usuarios: int
    total_lmes: int
    por_status: dict[str, int]
    top_medicamentos: dict[str, int] = Field(default_factory=dict)


@router.get("/fictional/stats", response_model=StatsOut)
def fictional_stats(
    db: Session = Depends(get_session),
    _auth: None = Depends(verify_internal_token),
) -> StatsOut:
    total_users = db.query(func.count(FictionalUser.id)).scalar() or 0
    total_lmes = db.query(func.count(FictionalLme.id)).scalar() or 0
    rows = db.query(FictionalLme.status, func.count(FictionalLme.id)).group_by(FictionalLme.status).all()
    top = db.query(FictionalLme.medicamento, func.count(FictionalLme.id)) \
             .group_by(FictionalLme.medicamento) \
             .order_by(func.count(FictionalLme.id).desc()).limit(6).all()
    return StatsOut(
        total_usuarios=total_users,
        total_lmes=total_lmes,
        por_status={str(status): int(count) for status, count in rows},
        top_medicamentos={str(name): int(count) for name, count in top},
    )


@router.get("/fictional/lmes/{lme_id}/pdf")
def fictional_lme_pdf(
    lme_id: int = Path(ge=1, le=100000),
    db: Session = Depends(get_session),
    _auth: None = Depends(verify_internal_token),
) -> Response:
    """PDF de uma LME fictícia, no layout dos laudos do AFSESAB."""
    if lme_id < 1:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="LME não encontrada.")
    # Usa a MESMA linha determinística exibida na tabela do clone.
    users = db.query(FictionalUser).order_by(FictionalUser.id).limit(100).all()
    master = build_master(users, db)
    row = master[(lme_id - 1) % len(master)]
    pdf = build_lme_pdf_from_row(row, lme_id)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="LME-{lme_id:06d}.pdf"'},
    )


@router.get("/fictional/export/{key}")
def fictional_export(
    key: str = Path(pattern=VIEW_KEY_PATTERN),
    formato: str = Query("csv", pattern="^(csv|pdf)$"),
    db: Session = Depends(get_session),
    _auth: None = Depends(verify_internal_token),
) -> Response:
    from ...services.fictional_views import build_view as build

    view = build(key, db)
    if formato == "pdf":
        content, mime = build_pdf(view), "application/pdf"
    else:
        content, mime = build_csv(view), "text/csv; charset=utf-8"
    return Response(
        content=content,
        media_type=mime,
        headers={
            "Content-Disposition": f'attachment; filename="{report_filename(view, formato)}"'
        },
    )


@router.get("/fictional/view/{key}")
def fictional_view(
    key: str = Path(pattern=VIEW_KEY_PATTERN),
    db: Session = Depends(get_session),
    _auth: None = Depends(verify_internal_token),
) -> dict[str, object]:
    """Dataset específico de cada tela do clone (títulos/colunas únicos)."""
    return build_view(key, db)


@router.get("/fictional/users", response_model=list[UserOut])
def fictional_users(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_session),
    _auth: None = Depends(verify_internal_token),
) -> list[UserOut]:
    rows = db.query(FictionalUser).order_by(FictionalUser.id).offset(offset).limit(limit).all()
    return [UserOut.model_validate(r) for r in rows]


@router.get("/fictional/lmes", response_model=list[LmeOut])
def fictional_lmes(
    status: Literal["pendente", "autorizada", "faturada", "dispensada"] | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_session),
    _auth: None = Depends(verify_internal_token),
) -> list[LmeOut]:
    query = db.query(FictionalLme)
    if status:
        query = query.filter(FictionalLme.status == status)
    rows = query.order_by(FictionalLme.id).offset(offset).limit(limit).all()
    return [LmeOut.model_validate(r) for r in rows]
