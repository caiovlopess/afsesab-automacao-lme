"""Geração de PDF de LME fictícia no layout dos formulários do AFSESAB.

Campos espelhados dos rótulos reais extraídos do source map do portal
(src/i18n/pt-BR/Attributes.js): Situação da LME, Medicamentos, CID,
Quantidade Autorizada, Frequência em Dias, Prescritor, Unidade Dispensadora etc.
"""

from __future__ import annotations

import io
from datetime import datetime, timedelta
from types import SimpleNamespace
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from ..models.sql_models import FictionalLme, FictionalUser

AZUL = colors.HexColor("#0B3D70")
CINZA = colors.HexColor("#D8E0E8")


def build_lme_pdf(lme: FictionalLme, user: FictionalUser | None) -> bytes:
    """Retorna o PDF de uma LME fictícia."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=f"LME Fictícia {lme.id:06d}",
        author="AF Copilot — projeto acadêmico",
    )

    styles = getSampleStyleSheet()
    titulo = ParagraphStyle(
        "titulo", parent=styles["Heading1"], fontSize=17, textColor=AZUL,
        alignment=TA_CENTER, spaceAfter=2,
    )
    subtitulo = ParagraphStyle(
        "subtitulo", parent=styles["Normal"], fontSize=9, textColor=colors.HexColor("#546E7A"),
        alignment=TA_CENTER, spaceAfter=10,
    )
    secao = ParagraphStyle(
        "secao", parent=styles["Heading2"], fontSize=10, textColor=AZUL, spaceBefore=10, spaceAfter=4,
    )
    normal = ParagraphStyle("normal", parent=styles["Normal"], fontSize=9, leading=13)

    emitida = lme.created_at.strftime("%d/%m/%Y") if lme.created_at else "—"
    validade = (
        (lme.created_at + timedelta(days=30)).strftime("%d/%m/%Y")
        if lme.created_at else "—"
    )
    cns = user.cns_ficticio if user else f"{lme.user_id:015d}"[:15]
    nome = user.nome if user else "—"
    unidade = user.unidade if user else "UBS Centro"

    story = [
        Paragraph("AFSESAB — LAUDO DE MEDICAMENTO ESPECIALIZADO (LME)", titulo),
        Paragraph("5ª DIRETORIA REGIONAL DE SAÚDE — GANDU · SISTEMA DE GESTÃO FARMACÊUTICA", subtitulo),
    ]

    story.append(Paragraph("1. Identificação", secao))
    story.append(_grid([
        ["Número da LME", f"LME-{lme.id:06d}", "Situação da LME", lme.status.upper()],
        ["Data de emissão", emitida, "Validade", validade],
        ["Competência", "11/2026", "Protocolo", "PCDT — Ministério da Saúde"],
    ]))

    story.append(Paragraph("2. Paciente", secao))
    story.append(_grid([
        ["Nome", nome, "CNS", cns],
        ["Unidade solicitante", unidade, "Estabelecimento de Saúde", "Hospital Municipal Dr. João Silva"],
        ["CID-10", lme.cid10, "Patologia", _patologia(lme.cid10)],
    ]))

    story.append(Paragraph("3. Medicamento e posologia", secao))
    story.append(_grid([
        ["Medicamento", lme.medicamento, "Apresentação", lme.dosagem],
        ["Posologia", "1 comprimido via oral 2x ao dia", "Frequência em dias", "30"],
        ["Quantidade Autorizada", "60", "Período de Tratamento", "11/2026 a 01/2027"],
        ["Saldo disponível", "60", "Lista de Medicamento", "Lista Especializado CEAF"],
    ]))

    story.append(Paragraph("4. Critérios e exames", secao))
    story.append(Paragraph(
        "<b>Critérios de inclusão:</b> diagnóstico confirmado por CID-10, "
        "falha/intolerância ao tratamento básico e prescrição por profissional habilitado.", normal,
    ))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "<b>Exames obrigatórios para LME/IME:</b> hemograma completo, creatinina, "
        "glicemia em jejum e HbA1c (quando aplicável).", normal,
    ))

    story.append(Paragraph("5. Prescrição e dispensação", secao))
    story.append(_grid([
        ["Prescritor", "CRM-BA-0001 — Ana Paula Ferreira", "Unidade Dispensadora", "Almoxarifado Central"],
        ["Valor estimado (R$)", f"{lme.valor:.2f}", "Número da APAC", f"APAC-{lme.id:06d}"],
    ]))

    story.append(Spacer(1, 16))
    story.append(Paragraph(
        "Documento gerado eletronicamente pelo sistema AF Copilot. "
        "Dados conferidos com a unidade solicitante antes da dispensação.", normal,
    ))
    story.append(Spacer(1, 18))
    story.append(_grid([
        ["_______________________________", "_______________________________"],
        ["Prescritor responsável", "Farmacêutico responsável"],
    ]))

    doc.build(story)
    return buffer.getvalue()


def build_lme_pdf_from_row(row: dict[str, Any], lme_id: int) -> bytes:
    """Gera o PDF a partir da MESMA linha exibida na tabela do clone.

    Isso garante que o paciente/medicamento do PDF sejam exatamente os da linha
    clicada ( antes o PDF buscava o registro do banco e os IDs não batiam ).
    """
    try:
        emitida = datetime.strptime(str(row.get("Data", "")), "%d/%m/%Y")
    except (ValueError, TypeError):
        emitida = None

    lme = SimpleNamespace(
        id=lme_id,
        status=str(row.get("Status", "")).upper(),
        created_at=emitida,
        user_id=lme_id,
        cid10=str(row.get("CID-10", "")),
        medicamento=str(row.get("Medicamento", "")),
        dosagem=str(row.get("Apresentação") or row.get("Dosagem", "")),
        valor=float(str(row.get("Valor (R$)", "0")).replace(",", ".") or 0),
    )
    user = SimpleNamespace(
        nome=str(row.get("Paciente", "")),
        cns_ficticio=str(row.get("CNS", "")),
        unidade=str(row.get("Unidade", "UBS Centro")),
    )
    return build_lme_pdf(lme, user)


def _grid(data: list[list[str]]) -> Table:
    table = Table(data, colWidths=[42 * mm, 48 * mm, 42 * mm, 48 * mm] if len(data[0]) == 4
                  else [60 * mm, 120 * mm], hAlign="LEFT")
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, CINZA),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F3F6F9")),
        ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#F3F6F9")),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("LEADING", (0, 0), (-1, -1), 11),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return table


def _patologia(cid: str) -> str:
    return {
        "E11": "Diabetes mellitus", "I10": "Hipertensão arterial", "J45": "Asma",
        "G40": "Epilepsia", "M05": "Artrite reumatoide", "M06": "Artrite reumatoide",
        "B18": "Hepatite viral", "B20": "HIV/AIDS", "C50": "Neoplasia de mama",
        "E03": "Hipotireoidismo", "J44": "DPOC", "K50": "Doença de Crohn",
    }.get(cid, "Patologia não informada")
