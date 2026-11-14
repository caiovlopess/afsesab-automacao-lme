import os
import re
import unittest
from datetime import datetime, timezone
from uuid import uuid4

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import OperationFailure


VIEW_CITIES = {
    "pacientes_sai": "Santo Antônio de Jesus",
    "pacientes_amargosa": "Amargosa",
    "pacientes_nazare": "Nazaré",
    "pacientes_cruz": "Cruz das Almas",
}
MASKED_CPF = re.compile(r"^\*\*\*\.\*\*\*\.\*\*\*-\d{2}$")


def connect_as(user_name, password):
    return MongoClient(
        "localhost",
        27018,
        username=user_name,
        password=password,
        authSource="lme",
        serverSelectionTimeoutMS=5000,
    )


class TestSecurityPermissions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        load_dotenv()
        passwords = {
            "teste_farmaceutico_sai": os.getenv("TEST_FARMACEUTICO_SAI_PASSWORD"),
            "teste_auditor": os.getenv("TEST_AUDITOR_PASSWORD"),
            "teste_ia": os.getenv("TEST_IA_PASSWORD"),
            "teste_workflow_audit": os.getenv("TEST_WORKFLOW_AUDIT_PASSWORD"),
        }
        missing = [name for name, password in passwords.items() if not password]
        if missing:
            raise RuntimeError(
                "Defina no .env as senhas para: " + ", ".join(missing)
            )
        cls.clients = {
            user_name: connect_as(user_name, password)
            for user_name, password in passwords.items()
        }
        cls.database = {
            user_name: client["lme"] for user_name, client in cls.clients.items()
        }

    @classmethod
    def tearDownClass(cls):
        for client in cls.clients.values():
            client.close()

    def assert_not_authorized(self, collection):
        with self.assertRaises(OperationFailure) as error:
            collection.find_one()
        self.assertEqual(error.exception.code, 13)
        self.assertIn("not authorized", str(error.exception).lower())

    def assert_masked_city_view(self, database, view_name, expected_city):
        patient = database[view_name].find_one()
        self.assertIsNotNone(
            patient,
            f"{view_name} está vazia; gere os dados fictícios antes dos testes.",
        )
        self.assertEqual(patient["cidade"], expected_city)
        self.assertRegex(patient["cpf"], MASKED_CPF)

    def test_farmaceutico_reads_only_its_city_view(self):
        database = self.database["teste_farmaceutico_sai"]
        self.assert_masked_city_view(
            database, "pacientes_sai", VIEW_CITIES["pacientes_sai"]
        )
        self.assert_not_authorized(database["pacientes"])
        self.assert_not_authorized(database["pacientes_amargosa"])

    def test_auditor_reads_audit_log_and_masked_views(self):
        database = self.database["teste_auditor"]
        database["audit_log"].find_one()
        for view_name, city in VIEW_CITIES.items():
            self.assert_masked_city_view(database, view_name, city)
        self.assert_not_authorized(database["pacientes"])

    def test_ia_reads_views_inserts_audit_and_cannot_read_original(self):
        database = self.database["teste_ia"]
        for view_name, city in VIEW_CITIES.items():
            self.assert_masked_city_view(database, view_name, city)

        database["audit_log"].insert_one(
            {
                "evento": "teste_permissao_insert",
                "teste_id": str(uuid4()),
                "criado_em": datetime.now(timezone.utc),
            }
        )
        self.assert_not_authorized(database["audit_log"])
        self.assert_not_authorized(database["pacientes"])

    def test_workflow_audit_only_inserts_audit_events(self):
        database = self.database["teste_workflow_audit"]
        database["audit_log"].insert_one(
            {
                "evento": "teste_workflow_audit_insert",
                "teste_id": str(uuid4()),
                "criado_em": datetime.now(timezone.utc),
            }
        )
        self.assert_not_authorized(database["audit_log"])
        for view_name in VIEW_CITIES:
            self.assert_not_authorized(database[view_name])
        self.assert_not_authorized(database["pacientes"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
