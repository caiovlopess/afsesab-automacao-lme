"""Exportação de relatórios do clone em CSV e PDF."""

from __future__ import annotations

import csv
import io
import re
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

AZUL = colors.HexColor("#0B3D70")


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")[:60]


def build_csv(view: dict) -> bytes:
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";", quoting=csv.QUOTE_MINIMAL)
    writer.writerow(view["columns"])
    for row in view["rows"]:
        writer.writerow(["" if v is None else v for v in row])
    return ("\ufeff" + output.getvalue()).encode("utf-8")  # BOM para Excel


def build_pdf(view: dict) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=12 * mm, rightMargin=12 * mm,
        topMargin=14 * mm, bottomMargin=14 * mm,
        title=view["title"], author="AF Copilot",
    )
    styles = getSampleStyleSheet()
    title = ParagraphStyle("title", parent=styles["Heading1"], fontSize=15, textColor=AZUL, spaceAfter=4)
    meta = ParagraphStyle("meta", parent=styles["Normal"], fontSize=8, textColor=colors.HexColor("#546E7A"), spaceAfter=10)
    cell = ParagraphStyle("cell", parent=styles["Normal"], fontSize=7, leading=9)

    cols = view["columns"]
    data = [[Paragraph(f"<b>{c}</b>", cell) for c in cols]]
    for row in view["rows"][:300]:
        data.append([Paragraph(str(v), cell) for v in row])

    width = doc.width / max(1, len(cols))
    table = Table(data, colWidths=[width] * len(cols), repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D8E0E8")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8EFF7")),
        ("TEXTCOLOR", (0, 0), (-1, 0), AZUL),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7FAFC")]),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))

    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    doc.build([
        Paragraph(view["title"], title),
        Paragraph(f"AFSESAB · Sistema de Gestão Farmacêutica · Gerado em {now}", meta),
        table,
        Spacer(1, 6),
        Paragraph(f"Total de registros: {len(view['rows'])}", meta),
    ])
    return buffer.getvalue()


def filename(view: dict, extension: str) -> str:
    return f"{_slug(view['title'])}.{extension}"
