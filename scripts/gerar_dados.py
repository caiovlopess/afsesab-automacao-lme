import os, random
from datetime import timedelta
from faker import Faker
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()
fake = Faker("pt_BR")

user = os.environ["MONGO_ROOT_USER"]
pwd = os.environ["MONGO_ROOT_PASSWORD"]
client = MongoClient(
    "localhost",
    27018,
    username=user,
    password=pwd,
    authSource="admin",
)
db = client["lme"]

CIDADES = ["Santo Antônio de Jesus", "Amargosa", "Nazaré", "Cruz das Almas"]
MEDICAMENTOS = ["Adalimumabe 40mg", "Etanercepte 50mg", "Sirolimo 1mg",
                "Imatinibe 400mg", "Rituximabe 500mg", "Olanzapina 10mg"]
STATUS = ["ATIVA", "VENCIDA", "PENDENTE", "CANCELADA"]

def paciente():
    inicio = fake.date_between(start_date="-18m", end_date="today")
    return {
        "nome": fake.name(),
        "cpf": fake.cpf(),
        "cidade": random.choice(CIDADES),
        "lme": {
            "medicamento": random.choice(MEDICAMENTOS),
            "quantidade": random.choice([30, 60, 90]),
            "vigencia_inicio": inicio.isoformat(),
            "vigencia_fim": (inicio + timedelta(days=180)).isoformat(),
            "status": random.choice(STATUS),
        },
    }

db.pacientes.drop()
for _ in range(10):
    db.pacientes.insert_many([paciente() for _ in range(1000)])

print("Total:", db.pacientes.count_documents({}))