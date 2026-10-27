"""CLI demonstrativa. Usa filtros fechados e dados sintéticos; não integra com AFSESAB."""
import os
from datetime import date
from pymongo import MongoClient

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("MONGODB_DB", "afsesab_demo")

# Exemplo didático de autorização. Em produção, obter identidade de um provedor institucional.
PAPEIS = {
    "profissional_demo": {"papel": "profissional", "cidades_permitidas": ["cidade_001", "cidade_002"]},
    "auditor_demo": {"papel": "auditor", "cidades_permitidas": []},
}

def buscar(db, usuario, cidade_id, status, medicamento=None):
    perfil = PAPEIS.get(usuario)
    if not perfil:
        raise PermissionError("DENY: usuário não reconhecido.")
    if perfil["papel"] != "profissional":
        raise PermissionError("DENY: este papel não pode consultar registros clínicos.")
    if cidade_id not in perfil["cidades_permitidas"]:
        raise PermissionError("DENY: município fora do escopo autorizado.")
    if status not in {"vigente", "vencida", "em_analise"}:
        raise ValueError("Status inválido.")
    filtro_pacientes = {"cidade_id": cidade_id, "ativo": True}
    ids = [p["_id"] for p in db.pacientes.find(filtro_pacientes, {"_id": 1})]
    filtro_lme = {"paciente_id": {"$in": ids}, "status_lme": status}
    if medicamento:
        filtro_lme["medicamento"] = medicamento
    return list(db.consultas_lme.find(
        filtro_lme,
        {"_id": 1, "paciente_id": 1, "medicamento": 1, "quantidade": 1,
         "data_inicio": 1, "data_fim": 1, "status_lme": 1}
    ).limit(100))

def main():
    client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
    client.admin.command("ping")
    db = client[DB_NAME]
    print("AFSESAB — demonstração CLI com dados fictícios")
    print("Usuário demo disponível: profissional_demo")
    print("Cidades: cidade_001 (Ilhéus), cidade_002 (Itabuna)")
    usuario = input("Usuário: ").strip()
    cidade = input("ID da cidade: ").strip()
    status = input("Status (vigente/vencida/em_analise): ").strip()
    medicamento = input("Medicamento (Enter para todos): ").strip() or None
    try:
        resultados = buscar(db, usuario, cidade, status, medicamento)
        print(f"Resultados (limite 100): {len(resultados)}")
        for item in resultados:
            print(item)
        # Não registrar os registros clínicos no log de auditoria.
        db.auditoria.insert_one({
            "usuario_id": usuario, "acao": "consulta_demo",
            "data_hora": date.today().isoformat(), "resultado": "sucesso",
            "detalhes_minimos": {"cidade_id": cidade, "status": status}
        })
    except (PermissionError, ValueError) as exc:
        print(exc)
        db.auditoria.insert_one({
            "usuario_id": usuario or "desconhecido", "acao": "consulta_demo",
            "data_hora": date.today().isoformat(), "resultado": "negado",
            "detalhes_minimos": {"motivo": type(exc).__name__}
        })
    finally:
        client.close()

if __name__ == "__main__":
    main()
