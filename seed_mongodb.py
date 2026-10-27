"""Carga inicial de dados sintéticos para o protótipo AFSESAB.
Nunca use este script para carregar dados reais de saúde.
"""
import os
import random
from datetime import date, timedelta
from pymongo import MongoClient, ASCENDING, DESCENDING

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("MONGODB_DB", "afsesab_demo")
random.seed(42)

CIDADES = [
    {"_id": "cidade_001", "nome": "Ilheus", "uf": "BA"},
    {"_id": "cidade_002", "nome": "Itabuna", "uf": "BA"},
    {"_id": "cidade_003", "nome": "Cidade Ficticia Norte", "uf": "BA"},
]
MEDICAMENTOS = ["medicamento_exemplo_a", "medicamento_exemplo_b", "medicamento_exemplo_c"]
STATUS = ["vigente", "vencida", "em_analise"]

def main():
    client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
    client.admin.command("ping")
    db = client[DB_NAME]

    for name in ["cidades", "pacientes", "consultas_lme", "auditoria"]:
        db[name].delete_many({})

    db.cidades.insert_many(CIDADES)
    pacientes, lmes = [], []
    hoje = date.today()
    for i in range(1, 301):
        cidade = random.choice(CIDADES)
        paciente_id = f"paciente_{i:04d}"
        pacientes.append({
            "_id": paciente_id,
            "origem_id": f"ORIGEM-SINTETICA-{i:04d}",
            "cidade_id": cidade["_id"],
            "ativo": random.choice([True, True, True, False]),
        })
        for j in range(random.randint(1, 3)):
            inicio = hoje - timedelta(days=random.randint(0, 700))
            fim = inicio + timedelta(days=random.randint(90, 365))
            status = "vigente" if fim >= hoje else random.choice(["vencida", "em_analise"])
            lmes.append({
                "_id": f"lme_{i:04d}_{j+1}",
                "paciente_id": paciente_id,
                "medicamento": random.choice(MEDICAMENTOS),
                "quantidade": random.choice([30, 60, 90]),
                "data_inicio": inicio.isoformat(),
                "data_fim": fim.isoformat(),
                "status_lme": status,
                "data_consulta": hoje.isoformat(),
                "sintetico": True,
            })

    db.pacientes.insert_many(pacientes)
    db.consultas_lme.insert_many(lmes)
    db.pacientes.create_index([("cidade_id", ASCENDING), ("ativo", ASCENDING)])
    db.consultas_lme.create_index([
        ("paciente_id", ASCENDING), ("status_lme", ASCENDING), ("data_fim", DESCENDING)
    ])
    db.consultas_lme.create_index([
        ("medicamento", ASCENDING), ("status_lme", ASCENDING), ("data_fim", DESCENDING)
    ])
    db.auditoria.create_index([("data_hora", DESCENDING)])
    print(f"Carga concluída: {len(pacientes)} pacientes sintéticos e {len(lmes)} LMEs sintéticas.")
    print(f"Banco: {DB_NAME}. Nenhum dado real foi usado.")
    client.close()

if __name__ == "__main__":
    main()
