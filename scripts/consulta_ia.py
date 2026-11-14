"""Consulta autorizada às views de LME (simula o que o n8n fará).

Regras de segurança desta camada:
- conecta ao MongoDB com o usuário do perfil, nunca com o root;
- consulta somente as views por cidade;
- registra cada tentativa em ``audit_log`` usando o usuário
  ``teste_workflow_audit``, que só tem permissão de insert;
- nunca devolve CPF completo (mascara de novo, além da máscara da view).
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from uuid import uuid4

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import OperationFailure, PyMongoError

load_dotenv()

DB_NAME = "lme"
MONGO_HOST = os.getenv("MONGO_HOST", "localhost")
MONGO_PORT = int(os.getenv("MONGO_PORT", "27018"))

# Usuário de teste -> variável de ambiente que guarda a senha.
PERFIS = {
    "teste_farmaceutico_sai": "TEST_FARMACEUTICO_SAI_PASSWORD",
    "teste_auditor": "TEST_AUDITOR_PASSWORD",
    "teste_ia": "TEST_IA_PASSWORD",
}
USUARIO_AUDITORIA = "teste_workflow_audit"

# Cidade -> view permitida. A coleção original ``pacientes`` nunca é usada aqui.
CIDADES = {
    "Santo Antônio de Jesus": "pacientes_sai",
    "Amargosa": "pacientes_amargosa",
    "Nazaré": "pacientes_nazare",
    "Cruz das Almas": "pacientes_cruz",
}
STATUS_VALIDOS = {"ATIVA", "VENCIDA", "PENDENTE", "CANCELADA"}
PROJECAO = {"_id": 0, "nome": 1, "cidade": 1, "lme": 1, "cpf": 1}

CPF_FORMATADO = re.compile(r"\d{3}\.\d{3}\.\d{3}-\d{2}")
CPF_SOMENTE_DIGITOS = re.compile(r"(?<!\d)\d{11}(?!\d)")


def _senha(prefixo_variavel):
    valor = os.getenv(prefixo_variavel)
    if not valor:
        raise RuntimeError(
            f"Defina {prefixo_variavel} no .env antes de executar a consulta."
        )
    return valor


def conectar(usuario):
    """Abre conexão com o MongoDB usando as credenciais do próprio perfil."""
    if usuario not in PERFIS:
        raise ValueError(f"Perfil desconhecido: {usuario}")
    return MongoClient(
        MONGO_HOST,
        MONGO_PORT,
        username=usuario,
        password=_senha(PERFIS[usuario]),
        authSource=DB_NAME,
        serverSelectionTimeoutMS=5000,
    )


def _conectar_auditoria():
    return MongoClient(
        MONGO_HOST,
        MONGO_PORT,
        username=USUARIO_AUDITORIA,
        password=_senha("TEST_WORKFLOW_AUDIT_PASSWORD"),
        authSource=DB_NAME,
        serverSelectionTimeoutMS=5000,
    )


def mascarar_cpf(texto):
    """Mascara CPF formatado ou com 11 dígitos soltos, preservando os 2 finais."""
    texto = CPF_FORMATADO.sub(
        lambda achado: "***.***.***-" + achado.group(0)[-2:], texto
    )
    return CPF_SOMENTE_DIGITOS.sub(
        lambda achado: "***.***.***-" + achado.group(0)[-2:], texto
    )


def sanitizar(valor):
    """Aplica a máscara de CPF recursivamente em textos, listas e dicionários."""
    if isinstance(valor, str):
        return mascarar_cpf(valor)
    if isinstance(valor, dict):
        return {chave: sanitizar(item) for chave, item in valor.items()}
    if isinstance(valor, list):
        return [sanitizar(item) for item in valor]
    return valor


def registrar_auditoria(perfil, pergunta, view, permitido, motivo, total):
    """Grava o evento em audit_log com o usuário de auditoria (só insert)."""
    documento = {
        "solicitacao_id": pergunta["solicitacao_id"],
        "evento": "consulta_lme",
        "usuario": perfil,
        "pergunta": {
            "cidade": str(pergunta["cidade"]),
            "status": str(pergunta["status"]),
            "medicamento": (
                None
                if pergunta["medicamento"] is None
                else str(pergunta["medicamento"])
            ),
        },
        "view": view,
        "permitido": permitido,
        "motivo": motivo,
        "registros_retornados": total,
        "criado_em": datetime.now(timezone.utc),
    }
    cliente = _conectar_auditoria()
    try:
        return cliente[DB_NAME]["audit_log"].insert_one(documento).inserted_id
    finally:
        cliente.close()


def _negado(solicitacao_id, perfil, pergunta, view, motivo):
    registrar_auditoria(perfil, pergunta, view, False, motivo, 0)
    return {
        "solicitacao_id": solicitacao_id,
        "permitido": False,
        "view": view,
        "motivo": motivo,
        "total": 0,
        "registros": [],
    }


def consultar(perfil, cidade, status, medicamento=None, limite=20):
    """Executa a consulta e devolve um resultado sem dados fora do escopo.

    A autorização de cidade é aplicada pelo MongoDB: o usuário do perfil só
    consegue ler a view concedida ao seu role. Se o Mongo negar, a tentativa
    também é auditada como negada.
    """
    solicitacao_id = str(uuid4())
    pergunta = {
        "solicitacao_id": solicitacao_id,
        "cidade": cidade,
        "status": status,
        "medicamento": medicamento,
    }

    # Validação de tipos antes de montar qualquer filtro (evita injeção).
    if not isinstance(perfil, str) or not isinstance(cidade, str):
        return _negado(solicitacao_id, str(perfil), pergunta, None, "entrada inválida")
    if not isinstance(status, str) or status not in STATUS_VALIDOS:
        return _negado(
            solicitacao_id, perfil, pergunta, None, "status inválido"
        )
    if medicamento is not None and not isinstance(medicamento, str):
        return _negado(
            solicitacao_id, perfil, pergunta, None, "medicamento inválido"
        )
    if perfil not in PERFIS:
        return _negado(solicitacao_id, perfil, pergunta, None, "perfil desconhecido")
    if cidade not in CIDADES:
        return _negado(
            solicitacao_id, perfil, pergunta, None, "cidade fora do escopo"
        )
    if not isinstance(limite, int) or not 1 <= limite <= 100:
        return _negado(
            solicitacao_id, perfil, pergunta, None, "limite inválido"
        )

    view = CIDADES[cidade]
    filtro = {"cidade": cidade, "lme.status": status}
    if medicamento:
        filtro["lme.medicamento"] = medicamento

    cliente = conectar(perfil)
    try:
        registros = list(
            cliente[DB_NAME][view].find(filtro, PROJECAO).limit(limite)
        )
    except OperationFailure as erro:
        motivo = f"acesso negado pelo MongoDB: {erro}"
        return _negado(solicitacao_id, perfil, pergunta, view, motivo)
    except PyMongoError as erro:
        motivo = f"erro de conexão/consulta: {erro}"
        return _negado(solicitacao_id, perfil, pergunta, view, motivo)
    finally:
        cliente.close()

    registros = sanitizar(registros)
    registrar_auditoria(perfil, pergunta, view, True, None, len(registros))
    return {
        "solicitacao_id": solicitacao_id,
        "permitido": True,
        "view": view,
        "motivo": None,
        "total": len(registros),
        "registros": registros,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Consulta fictícia de LME com permissão e auditoria."
    )
    parser.add_argument(
        "--perfil",
        required=True,
        choices=sorted(PERFIS),
        help="Usuário do MongoDB que fará a consulta.",
    )
    parser.add_argument(
        "--cidade", required=True, choices=sorted(CIDADES), help="Cidade da view."
    )
    parser.add_argument(
        "--status",
        required=True,
        choices=sorted(STATUS_VALIDOS),
        help="Status da LME.",
    )
    parser.add_argument("--medicamento", help="Medicamento exato (opcional).")
    parser.add_argument("--limite", type=int, default=20, help="Máximo de registros.")
    args = parser.parse_args()

    try:
        resultado = consultar(
            args.perfil,
            args.cidade,
            args.status,
            args.medicamento,
            args.limite,
        )
    except (RuntimeError, ValueError) as erro:
        print(f"Erro de configuração: {erro}", file=sys.stderr)
        return 1

    print(
        json.dumps(resultado, ensure_ascii=False, indent=2, default=str)
    )
    return 0 if resultado["permitido"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
