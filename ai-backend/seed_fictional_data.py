"""Gera a base de demonstração do AF Copilot.

Nomes e e-mails são REALISTAS (para o sistema parecer real numa apresentação),
mas os registros são sintéticos — uso exclusivo de demonstração acadêmica.

Uso:
    python seed_fictional_data.py --users 12000 --lmes 18000 --force
"""

from __future__ import annotations

import argparse
import random
import unicodedata

from sqlalchemy import text

from app.core.database import SessionLocal, init_db
from app.models.sql_models import FictionalLme, FictionalUser

FIRST_NAMES = [
    "Arlindo", "Maria", "João", "Ana", "José", "Francisca", "Carlos", "Antônio",
    "Paulo", "Lúcia", "Rafael", "Juliana", "Marcos", "Patrícia", "Ricardo", "Fernanda",
    "André", "Camila", "Luiz", "Beatriz", "Gustavo", "Larissa", "Fábio", "Renata",
    "Diego", "Mariana", "Sérgio", "Aline", "Bruno", "Carla", "Eduardo", "Natália",
    "Felipe", "Isabela", "Henrique", "Tatiane", "Márcio", "Daniela", "Gilberto", "Sandra",
    "Wanderley", "Célia", "Otávio", "Rosângela", "Vinícius", "Aparecida", "Leandro", "Simone",
]
LAST_NAMES = [
    "Cruz Santos Silva", "Oliveira Lima", "Souza Carvalho", "Ferreira Rocha",
    "Almeida Prado", "Nascimento Costa", "Pereira Barbosa", "Martins Fonseca",
    "Ribeiro Dias", "Monteiro Azevedo", "Gomes Vieira", "Dutra Campos",
    "Moraes Filho", "Farias Nunes", "Teixeira Braga", "Cardoso Reis",
    "Pinto Amaral", "Figueiredo Castro", "Mendes Ramos", "Barbosa Cunha",
    "Azevedo Frota", "Lopes Machado", "Vasconcelos Freire", "Correia Leal",
]

MEDICAMENTOS = [
    "Metformina", "Insulina Glargina", "Losartana", "Atorvastatina", "Salbutamol",
    "Budesonida", "Carbamazepina", "Levotiroxina", "Adalimumabe", "Infliximabe",
    "Tenofovir", "Sofosbuvir", "Metotrexato", "Prednisona", "Omeprazol",
]
CIDS = ["E11", "I10", "J45", "G40", "M05", "M06", "B18", "B20", "C50", "E03", "J44", "K50"]
STATUS = ["pendente", "autorizada", "faturada", "dispensada"]
PESOS = [0.25, 0.25, 0.35, 0.15]
UNIDADES = [
    "UBS Centro", "UBS Jardim Primavera", "UBS Vila Nova",
    "UPA Leste", "Hospital Municipal Dr. João Silva",
]


def _slug(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.lower())
    return "".join(c for c in decomposed if not unicodedata.combining(c)).replace(" ", ".")


def seed(users_count: int, lmes_count: int, force: bool) -> None:
    init_db()
    rng = random.Random(20261116)
    session = SessionLocal()
    try:
        existing = session.query(FictionalUser).count()
        if existing > 0 and not force:
            print("Base já populada. Use --force para regerar.")
            return
        if existing > 0:
            session.query(FictionalLme).delete()
            session.query(FictionalUser).delete()
            session.commit()

        users: list[FictionalUser] = []
        for i in range(1, users_count + 1):
            nome = f"{FIRST_NAMES[(i - 1) % len(FIRST_NAMES)]} {LAST_NAMES[((i - 1) * 7) % len(LAST_NAMES)]}"
            email = f"{_slug(nome)}.{i:05d}@email.com"
            users.append(FictionalUser(
                nome=nome,
                email=email,
                cns_ficticio=f"{i:015d}"[:15],
                unidade=rng.choice(UNIDADES),
            ))
        for start in range(0, len(users), 1000):
            session.add_all(users[start:start + 1000])
            session.commit()
        print(f"Usuários inseridos: {users_count} (ex.: {users[0].nome})")

        lmes: list[FictionalLme] = []
        for i in range(lmes_count):
            lmes.append(FictionalLme(
                user_id=rng.randint(1, users_count),
                medicamento=rng.choice(MEDICAMENTOS),
                cid10=rng.choice(CIDS),
                dosagem=rng.choice(["850 mg", "100 mg/mL", "5 mg", "40 mg", "500 mg"]),
                status=rng.choices(STATUS, weights=PESOS, k=1)[0],
                valor=round(rng.uniform(45, 3200), 2),
            ))
        for start in range(0, len(lmes), 1000):
            session.add_all(lmes[start:start + 1000])
            session.commit()
        print(f"LMEs inseridas: {lmes_count}")

        counts = dict(session.execute(
            text("SELECT status, COUNT(*) FROM fictional_lmes GROUP BY status")
        ).all())
        print("Por status:", counts)
    finally:
        session.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--users", type=int, default=12000)
    parser.add_argument("--lmes", type=int, default=18000)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    seed(args.users, args.lmes, args.force)
