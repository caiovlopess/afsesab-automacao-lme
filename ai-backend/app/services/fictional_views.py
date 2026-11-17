"""Datasets do clone do AFSESAB — dados realistas, completos e sem repetição.

Cada tela tem colunas próprias e valores determinísticos (números, datas,
pacientes, medicamentos). Nenhuma célula fica vazia por falta de mapeamento.
"""

from __future__ import annotations

import hashlib
from datetime import date, timedelta
from typing import Any

from sqlalchemy.orm import Session

from ..models.sql_models import CatalogMedication, FictionalLme, FictionalUser

# ---------------------------------------------------------------- catálogos
MEDICAMENTOS = [
    ("SIM-000123", "Metformina", "Metformina", "Comprimido 850 mg"),
    ("SIM-000124", "Insulina Glargina", "Insulina glargina", "Solução 100 UI/mL"),
    ("SIM-000125", "Losartana Potássica", "Losartana", "Comprimido 50 mg"),
    ("SIM-000126", "Atorvastatina", "Atorvastatina", "Comprimido 20 mg"),
    ("SIM-000127", "Salbutamol", "Salbutamol", "Aerosol 100 mcg"),
    ("SIM-000128", "Budesonida", "Budesonida", "Pó inalatório 400 mcg"),
    ("SIM-000129", "Carbamazepina", "Carbamazepina", "Comprimido 200 mg"),
    ("SIM-000130", "Levotiroxina Sódica", "Levotiroxina", "Comprimido 50 mcg"),
    ("SIM-000131", "Adalimumabe", "Adalimumabe", "Solução 40 mg/0,8 mL"),
    ("SIM-000132", "Infliximabe", "Infliximabe", "Pó liofilizado 100 mg"),
    ("SIM-000133", "Tenofovir", "Tenofovir disoproxil", "Comprimido 300 mg"),
    ("SIM-000134", "Sofosbuvir", "Sofosbuvir", "Comprimido 400 mg"),
    ("SIM-000135", "Metotrexato", "Metotrexato", "Comprimido 2,5 mg"),
    ("SIM-000136", "Omeprazol", "Omeprazol", "Cápsula 20 mg"),
    ("SIM-000137", "Prednisona", "Prednisona", "Comprimido 5 mg"),
    ("SIM-000138", "Anlodipino", "Anlodipino", "Comprimido 5 mg"),
    ("SIM-000139", "Hidroclorotiazida", "Hidroclorotiazida", "Comprimido 25 mg"),
    ("SIM-000140", "Sinvastatina", "Sinvastatina", "Comprimido 20 mg"),
    ("SIM-000141", "Clopidogrel", "Clopidogrel", "Comprimido 75 mg"),
    ("SIM-000142", "Ácido Acetilsalicílico", "AAS", "Comprimido 100 mg"),
    ("SIM-000143", "Ranitidina", "Ranitidina", "Comprimido 150 mg"),
    ("SIM-000144", "Formoterol", "Formoterol", "Pó inalatório 12 mcg"),
    ("SIM-000145", "Tiotrópio", "Tiotrópio", "Cápsula 18 mcg"),
    ("SIM-000146", "Fenitoína", "Fenitoína", "Comprimido 100 mg"),
    ("SIM-000147", "Valproato de Sódio", "Valproato", "Comprimido 500 mg"),
    ("SIM-000148", "Etanercepte", "Etanercepte", "Solução 50 mg/mL"),
    ("SIM-000149", "Rituximabe", "Rituximabe", "Solução 100 mg/10 mL"),
    ("SIM-000150", "Trastuzumabe", "Trastuzumabe", "Pó liofilizado 440 mg"),
    ("SIM-000151", "Bevacizumabe", "Bevacizumabe", "Solução 25 mg/mL"),
    ("SIM-000152", "Imatinibe", "Imatinibe", "Comprimido 100 mg"),
    ("SIM-000153", "Lamivudina", "Lamivudina", "Comprimido 150 mg"),
    ("SIM-000154", "Efavirenz", "Efavirenz", "Cápsula 600 mg"),
    ("SIM-000155", "Darunavir", "Darunavir", "Comprimido 600 mg"),
    ("SIM-000156", "Ribavirina", "Ribavirina", "Comprimido 250 mg"),
    ("SIM-000157", "Micofenolato", "Micofenolato", "Comprimido 500 mg"),
    ("SIM-000158", "Ciclosporina", "Ciclosporina", "Cápsula 100 mg"),
    ("SIM-000159", "Tacrolimo", "Tacrolimo", "Cápsula 5 mg"),
    ("SIM-000160", "Azatioprina", "Azatioprina", "Comprimido 50 mg"),
    ("SIM-000161", "Sildenafil", "Sildenafil", "Comprimido 50 mg"),
    ("SIM-000162", "Bosentana", "Bosentana", "Comprimido 125 mg"),
]

ESTABELECIMENTOS = [
    ("0000001", "UBS Centro", "Gandu", "BA"),
    ("0000002", "UBS Jardim Primavera", "Gandu", "BA"),
    ("0000003", "UBS Vila Nova", "Gandu", "BA"),
    ("0000004", "UPA Leste", "Gandu", "BA"),
    ("0000005", "Hospital Municipal Dr. João Silva", "Salvador", "BA"),
    ("0000006", "UBS Praia Grande", "Salvador", "BA"),
    ("0000007", "UBS Nova Esperança", "Feira de Santana", "BA"),
    ("0000008", "Hospital Regional Sul", "Vitória da Conquista", "BA"),
]

PROGRAMAS = [
    ("PRG-01", "Componente Especializado", "CEAF"),
    ("PRG-02", "Básico e Estratégico", "Básico"),
    ("PRG-03", "Farmácia Popular", "Básico"),
    ("PRG-04", "HEMOBA", "Especializado"),
    ("PRG-05", "Saúde da Mulher", "Estratégico"),
    ("PRG-06", "Saúde da Criança", "Estratégico"),
]

PROFISSIONAIS = [
    ("CRM-BA-0001", "Ana Paula Ferreira", "Farmacêutica", "UBS Centro"),
    ("CRM-BA-0002", "João Batista Oliveira", "Clínico Geral", "UPA Leste"),
    ("CRM-BA-0003", "Maria das Graças Rocha", "Endocrinologista", "Hospital Municipal"),
    ("CRM-BA-0004", "Carlos Eduardo Nunes", "Farmacêutico", "UBS Vila Nova"),
    ("CRM-BA-0005", "Fernanda Lopes Machado", "Cardiologista", "Hospital Municipal"),
    ("CRM-BA-0006", "Ricardo Almeida Prado", "Neurologista", "UPA Leste"),
    ("CRM-BA-0007", "Juliana Torres Barbosa", "Farmacêutica", "Hospital Regional Sul"),
    ("CRM-BA-0008", "Marcos Vinícius Freire", "Pneumologista", "UBS Centro"),
    ("CRM-BA-0009", "Patrícia Gomes Vieira", "Reumatologista", "Hospital Municipal"),
    ("CRM-BA-0010", "Antônio Carlos Dias", "Farmacêutico", "UBS Jardim Primavera"),
    ("CRM-BA-0011", "Camila Rezende Costa", "Oncologista", "Hospital Municipal"),
    ("CRM-BA-0012", "Diego Farias Nunes", "Infectologista", "UPA Leste"),
]

FORNECEDORES = [
    ("12.345.678/0001-01", "Distribuidora Bahia Farma Ltda", "Salvador", "Carlos Andrade", "(71) 3221-4500", "Av. Sete de Setembro, 1200 — Salvador/BA"),
    ("23.456.789/0001-02", "Bio Saúde S.A.", "São Paulo", "Renata Mello", "(11) 3344-7788", "Rua Faria Lima, 2100 — São Paulo/SP"),
    ("34.567.890/0001-03", "Med Norte Distribuidora", "Recife", "Paulo Sérgio Lima", "(81) 3421-9900", "Av. Boa Viagem, 800 — Recife/PE"),
    ("45.678.901/0001-04", "Farma Sul Comércio Ltda", "Porto Alegre", "Luciana Prado", "(51) 3211-2200", "Rua dos Andradas, 450 — Porto Alegre/RS"),
    ("56.789.012/0001-05", "Vita Medicamentos S.A.", "Belo Horizonte", "Gustavo Rocha", "(31) 3277-1100", "Av. Afonso Pena, 1900 — Belo Horizonte/MG"),
    ("67.890.123/0001-06", "Central Farma Bahia", "Feira de Santana", "Ana Cláudia Souza", "(75) 3224-6600", "Av. Getúlio Vargas, 300 — Feira de Santana/BA"),
]

SIGTAP = [
    ("11/2026", "0301010077", "Consulta farmacêutica", "Ativo"),
    ("11/2026", "0202010010", "Consulta médica", "Ativo"),
    ("11/2026", "0301030025", "Dispensação de medicamento", "Ativo"),
    ("11/2026", "0405010020", "Hemograma completo", "Ativo"),
    ("10/2026", "0402030030", "Glicemia em jejum", "Ativo"),
    ("10/2026", "0402030110", "HbA1c", "Ativo"),
    ("10/2026", "0203010005", "Atendimento de urgência", "Ativo"),
    ("09/2026", "0304010010", "Vacinação", "Ativo"),
]

PCDT = [
    ("PCDT-001", "Diabetes Mellitus", "E11", "Metformina; Insulina"),
    ("PCDT-002", "Hipertensão Arterial", "I10", "Losartana; Anlodipino"),
    ("PCDT-003", "Asma", "J45", "Budesonida; Salbutamol"),
    ("PCDT-004", "Epilepsia", "G40", "Carbamazepina"),
    ("PCDT-005", "Artrite Reumatoide", "M06", "Metotrexato; Adalimumabe"),
    ("PCDT-006", "Hepatite C", "B18", "Sofosbuvir"),
    ("PCDT-007", "DPOC", "J44", "Tiotrópio; Formoterol"),
    ("PCDT-008", "Doença de Crohn", "K50", "Infliximabe"),
]

CID_LABELS = {
    "E11": "Diabetes Mellitus", "I10": "Hipertensão Arterial", "J45": "Asma",
    "G40": "Epilepsia", "M05": "Artrite Reumatoide", "M06": "Artrite Reumatoide",
    "B18": "Hepatiteviral C", "B20": "HIV/AIDS", "C50": "Neoplasia de Mama",
    "E03": "Hipotireoidismo", "J44": "DPOC", "K50": "Doença de Crohn",
}
CID_LIST = list(CID_LABELS)
STATUS_LIST = ["pendente", "autorizada", "faturada", "dispensada"]


def _n(seed: str, low: int, high: int) -> int:
    """Número determinístico e estável a partir de uma chave."""
    digest = hashlib.md5(seed.encode("utf-8")).hexdigest()
    return low + int(digest[:8], 16) % (high - low + 1)


def _date(offset_days: int) -> str:
    return (date(2026, 11, 1) + timedelta(days=offset_days % 28)).strftime("%d/%m/%Y")


# ---------------------------------------------------------------- master
def build_master(users: list[FictionalUser], db: Any | None = None) -> list[dict[str, Any]]:
    """100 registros mestres; quando `db` é informado, o status reflete o banco."""
    statuses: dict[int, str] = {}
    if db is not None:
        for row in db.query(FictionalLme.id, FictionalLme.status).limit(120).all():
            statuses[int(row[0])] = str(row[1])

    rows: list[dict[str, Any]] = []
    for i in range(100):
        code, med, principle, presentation = MEDICAMENTOS[i % len(MEDICAMENTOS)]
        user = users[i % len(users)] if users else None
        status = STATUS_LIST[_n(f"status{i}", 0, 3)]
        qty = _n(f"qty{i}", 10, 180)
        stock = _n(f"stock{i}", 60, 600)
        consumed = min(qty, _n(f"cons{i}", 8, qty))
        pct = round(consumed / stock * 100, 1)
        falta = _n(f"falta{i}", 0, 1)
        autorizadas = _n(f"aut{i}", 10, 120)
        faturadas = max(0, autorizadas - _n(f"diff{i}", 0, 35))
        fornecedor = FORNECEDORES[i % len(FORNECEDORES)]
        prof = PROFISSIONAIS[i % len(PROFISSIONAIS)]
        cpf = CID_LIST[_n(f"cid{i}", 0, len(CID_LIST) - 1)]
        rows.append({
            "ID": i + 1,
            "Nº": f"PED-{20260001 + i}",
            "Nota": f"NF-{10240 + i}",
            "Medicamento": med,
            "Código": code,
            "Princípio Ativo": principle,
            "Apresentação": presentation,
            "CID-10": cpf,
            "Patologia": CID_LABELS[cpf],
            "Dosagem": presentation.split()[-2] + " " + presentation.split()[-1],
            "Status": status,
            "Situação": "Ativo" if i % 7 else "Em análise",
            "Paciente": user.nome if user else "—",
            "CNS": user.cns_ficticio if user else "—",
            "Unidade": user.unidade if user else "UBS Centro",
            "Valor (R$)": f"{_n(f'valor{i}', 45, 3200) + (_n(f'cent{i}', 0, 99) / 100):.2f}",
            "Quantidade": qty,
            "CONSUMO": consumed,
            "ESTOQUE": stock,
            "%": f"{pct:.1f}%",
            "AUTORIZADAS": autorizadas,
            "FATURADAS": faturadas,
            "DIFERENÇA": autorizadas - faturadas,
            "Data": _date(i),
            "Validade": _date(i + 60),
            "Competência": "11/2026" if i % 2 else "10/2026",
            "Origem": "CEAF",
            "Destino": ESTABELECIMENTOS[(i + 2) % len(ESTABELECIMENTOS)][1],
            "Prescritor": prof[1],
            "Fornecedor": fornecedor[1],
            "CNPJ": fornecedor[0],
            "Cidade": fornecedor[2],
            "Contato": fornecedor[3],
            "Telefone": fornecedor[4],
            "Endereço": fornecedor[5],
            "Frequência em dias": str(_n(f"freq{i}", 15, 60)),
            "Posologia": f"{_n(f'dose{i}', 1, 3)}x ao dia",
            "Tratamento": f"{CID_LABELS[cpf]} ({cpf})",
            "Insulina": "Glargina" if i % 3 == 0 else "Regular" if i % 3 == 1 else "NPH",
            "Lote": f"LOTE-{_n(f'lote{i}', 10000, 99999)}",
            "Saldo": str(_n(f"saldo{i}", 20, 400)),
            "Ajuste": f"{_n(f'ajuste{i}', 5, 90)} unidades",
            "Responsável": prof[1],
            "Motivo": "Atualização de estoque" if i % 2 else "Regularização de vínculo",
            "Protocolo": PCDT[i % len(PCDT)][0],
            "Critério": "Inclusão confirmada",
            "Indicador": ["Cobertura LME", "Prazo de análise", "Dispensação no prazo", "Faturamento"][i % 4],
            "Meta": "90%",
            "Realizado": f"{_n(f'real{i}', 70, 99)}%",
        })
    for i, row in enumerate(rows):
        if i + 1 in statuses:
            row["Status"] = statuses[i + 1]
    return rows


# ---------------------------------------------------------------- specs
def _spec(title: str, columns: list[str], source: str = "master",
          offset: int = 0, limit: int = 100, status: str | None = None,
          note: str = "") -> dict[str, Any]:
    return {
        "title": title, "columns": columns, "source": source,
        "offset": offset, "limit": limit, "status": status, "note": note,
    }


VIEWS: dict[str, dict[str, Any]] = {
    "medicamento": _spec("Medicamento", ["Código", "Nome", "Princípio Ativo", "Apresentação"], "medicamentos"),
    "produto": _spec("Produto", ["Código", "Medicamento", "Apresentação", "Situação"], "medicamentos", offset=6),
    "estabelecimento": _spec("Estabelecimento de Saúde", ["CNES", "Nome", "Município", "UF"], "estabelecimentos"),
    "paciente": _spec("Paciente", ["ID", "Paciente", "CNS", "Unidade"], "master", offset=0),
    "programas": _spec("Programas de Saúde", ["Código", "Programa", "Componente"], "programas"),
    "lista_medicamentos": _spec("Lista de Medicamentos", ["Código", "Medicamento", "Apresentação", "Programa"], "medicamentos", limit=40),
    "profissional": _spec("Profissional", ["CRM", "Nome", "Especialidade", "Unidade"], "profissionais"),
    "carga_sigtap": _spec("Carga do SIGTAP", ["Competência", "Procedimento", "Descrição", "Status"], "sigtap"),
    "fornecedor": _spec("Fornecedor/Fabricante", ["CNPJ", "Razão Social", "Cidade", "Contato", "Telefone"], "fornecedores"),
    "almoxarifado": _spec("Almoxarifado", ["Código", "Descrição", "Unidade"], "almoxarifados"),
    "usuarios": _spec("Usuários", ["ID", "Paciente", "CNS", "Unidade"], "master", offset=5),
    "paciente_ext": _spec("Paciente Tratamento Ext", ["ID", "Paciente", "Tratamento", "Situação"], "master", offset=12),
    "paciente_insulina": _spec("Pacientes Tratamento Insulina", ["ID", "Paciente", "Insulina", "Posologia"], "master", offset=20),
    "rel_planejamento": _spec("Relatório Planejamento de Aquisição", ["Medicamento", "Quantidade", "Valor (R$)", "Situação"], "master", offset=8),
    "lme": _spec("LME", ["ID", "Medicamento", "Paciente", "CID-10", "Dosagem", "Status", "Valor (R$)"], "master", offset=0),
    "lme_transferencia": _spec("LME em Transferência", ["ID", "Medicamento", "Paciente", "Origem", "Destino", "Status"], "master", offset=15),
    "entrada": _spec("Entrada de Medicamentos", ["Nota", "Medicamento", "Quantidade", "Data"], "master", offset=30),
    "pedido": _spec("Pedido", ["Nº", "Unidade", "Medicamento", "Status"], "master", offset=25),
    "ajuste_estoque": _spec("Ajuste de Estoque", ["ID", "Medicamento", "Ajuste", "Responsável"], "master", offset=40),
    "ajuste_vinculo": _spec("Ajuste de Vínculo", ["ID", "Paciente", "Unidade", "Situação"], "master", offset=35),
    "transferencia": _spec("Transferência entre Unidades", ["ID", "Medicamento", "Origem", "Destino"], "master", offset=45),
    "divergencia": _spec("Divergência de Entrega", ["ID", "Medicamento", "Ajuste", "Situação"], "master", offset=50),
    "rel_autorizada_faturada": _spec("Quantidade Autorizada x Faturada", ["Medicamento", "AUTORIZADAS", "FATURADAS", "DIFERENÇA"], "master", offset=3),
    "rel_entrada": _spec("Entrada de Medicamentos", ["Nota", "Medicamento", "Quantidade", "Fornecedor"], "master", offset=55),
    "rel_mapa": _spec("Mapa de Medicamentos", ["Medicamento", "Unidade", "ESTOQUE", "%"], "master", offset=10),
    "rel_comprometimento": _spec("Relatório Comprometimento Estoque", ["Medicamento", "CONSUMO", "ESTOQUE", "%"], "master", offset=1),
    "rel_indicadores": _spec("Indicadores", ["Indicador", "Meta", "Realizado", "Status"], "master", offset=60, limit=40),
    "rel_acompanhamento": _spec("Acompanhamento de Pedidos", ["Nº", "Unidade", "Situação", "Data"], "master", offset=18),
    "rel_distribuicao": _spec("Distribuição", ["Medicamento", "Unidade", "Quantidade", "Data"], "master", offset=22),
    "rel_ajuste_estoque": _spec("Ajuste de Estoque", ["ID", "Medicamento", "Ajuste", "Responsável"], "master", offset=65),
    "rel_posicao": _spec("Posição de Estoque", ["Medicamento", "Quantidade", "Saldo", "ESTOQUE"], "master", offset=28),
    "rel_estoque_anterior": _spec("Estoque Dia Anterior", ["Medicamento", "ESTOQUE", "Saldo", "Data"], "master", offset=70),
    "esp_lme": _spec("LME", ["ID", "Medicamento", "Paciente", "CID-10", "Data"], "master", offset=5),
    "esp_glaucoma": _spec("Comparecimento de Pacientes Glaucoma", ["ID", "Paciente", "Tratamento", "Situação"], "master", offset=75),
    "esp_lme_glaucoma": _spec("LME Glaucoma", ["ID", "Paciente", "Medicamento", "Situação"], "master", offset=80),
    "esp_atendimentos": _spec("Consulta de Atendimentos", ["Data", "Paciente", "Prescritor", "Patologia"], "master", offset=85),
    "esp_patologias": _spec("Patologias x Medicamentos", ["CID-10", "Patologia", "Medicamento", "Quantidade"], "master", offset=90),
    "esp_dispensacao": _spec("Dispensação", ["ID", "Medicamento", "Paciente", "Data"], "master", offset=95, status="dispensada"),
    "esp_movimentos": _spec("Movimentos de Dispensa", ["ID", "Medicamento", "Ajuste", "Data"], "master", offset=33),
    "esp_paciente_status": _spec("Paciente LME por Status", ["Paciente", "Status", "Medicamento", "CID-10"], "master", offset=38),
    "esp_pacientes_atendidos": _spec("Relatório de Pacientes Atendidos", ["ID", "Paciente", "Unidade", "Situação"], "master", offset=42),
    "esp_deferidos": _spec("Pacientes Deferidos e Devolvidos", ["ID", "Paciente", "Situação", "Motivo"], "master", offset=48),
    "esp_ativos": _spec("Relatório Pacientes Ativos", ["ID", "Paciente", "Unidade", "Situação"], "master", offset=52),
    "sigaf_distribuicao": _spec("Distribuição SIGAF", ["Nota", "Unidade", "Medicamento", "Valor (R$)"], "master", offset=58),
    "sigaf_ajuste_vinculo": _spec("Ajuste de Vínculo SIGAF", ["ID", "Unidade", "Situação", "Valor (R$)"], "master", offset=62),
    "sigaf_ajuste_estoque": _spec("Ajuste de Estoque SIGAF", ["ID", "Medicamento", "Ajuste", "Valor (R$)"], "master", offset=68),
    "sigaf_exportar": _spec("Exportar Dados Estoque", ["Medicamento", "Lote", "Validade", "Saldo"], "master", offset=72),
}


def build_view(key: str, db: Session) -> dict[str, Any]:
    spec = VIEWS.get(key) or _spec("Registros", ["ID", "Medicamento"])
    cols = spec["columns"]
    source = spec["source"]
    status = spec.get("status")

    users = db.query(FictionalUser).order_by(FictionalUser.id).limit(100).all()
    master = build_master(users, db)

    if source == "master":
        subset = master[spec.get("offset", 0):]
        if status:
            subset = [r for r in subset if r["Status"] == status]
        rows = [[r.get(c, "") for c in cols] for r in subset[:spec.get("limit", 100)]]
    elif source == "medicamentos":
        idx = {"Código": 0, "Nome": 1, "Medicamento": 1, "Princípio Ativo": 2, "Apresentação": 3}
        catalog = [
            (m.codigo, m.nome, m.principio, m.apresentacao)
            for m in db.query(CatalogMedication).order_by(CatalogMedication.id).all()
        ]
        all_meds = catalog + MEDICAMENTOS[spec.get("offset", 0):]
        rows = [[m[idx.get(c, 0)] for c in cols] for m in all_meds]
    elif source == "estabelecimentos":
        idx = {"CNES": 0, "Nome": 1, "Município": 2, "UF": 3}
        rows = [[e[idx.get(c, 0)] for c in cols] for e in ESTABELECIMENTOS]
    elif source == "programas":
        idx = {"Código": 0, "Programa": 1, "Componente": 2}
        rows = [[p[idx.get(c, 0)] for c in cols] for p in PROGRAMAS]
    elif source == "profissionais":
        idx = {"CRM": 0, "Nome": 1, "Especialidade": 2, "Unidade": 3}
        rows = [[p[idx.get(c, 0)] for c in cols] for p in PROFISSIONAIS]
    elif source == "fornecedores":
        idx = {"CNPJ": 0, "Razão Social": 1, "Cidade": 2, "Contato": 3, "Telefone": 4, "Endereço": 5}
        rows = [[f[idx.get(c, 0)] for c in cols] for f in FORNECEDORES]
    elif source == "sigtap":
        idx = {"Competência": 0, "Procedimento": 1, "Descrição": 2, "Status": 3}
        rows = [[s[idx.get(c, 0)] for c in cols] for s in SIGTAP]
    elif source == "almoxarifados":
        rows = [["ALM-01", "Almoxarifado Central", "Gandu"],
                ["ALM-02", "Almoxarifado Norte", "Gandu"],
                ["ALM-03", "Almoxarifado Hospitalar", "Salvador"]]
    else:
        rows = []

    return {
        "key": key,
        "title": spec["title"],
        "columns": cols,
        "rows": rows[: spec.get("limit", 100)],
        "has_pdf": source == "master" and "ID" in cols,
        "note": spec.get("note", "Fonte: base de dados local do AF Copilot."),
    }
