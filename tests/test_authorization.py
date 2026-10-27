"""Testes unitários básicos de autorização, sem conexão com banco."""
import unittest
from src.app_cli import buscar

class FakeCollection:
    def find(self, filtro, proj=None):
        if filtro.get("cidade_id") == "cidade_001":
            return [{"_id": "paciente_0001"}]
        return []
    def __iter__(self):
        return iter([])

class FakeDB:
    pacientes = FakeCollection()
    consultas_lme = FakeCollection()

class AuthorizationTests(unittest.TestCase):
    def test_unknown_user_denied(self):
        with self.assertRaises(PermissionError):
            buscar(FakeDB(), "intruso", "cidade_001", "vigente")
    def test_out_of_scope_city_denied(self):
        with self.assertRaises(PermissionError):
            buscar(FakeDB(), "profissional_demo", "cidade_003", "vigente")
    def test_invalid_status_rejected(self):
        with self.assertRaises(ValueError):
            buscar(FakeDB(), "profissional_demo", "cidade_001", "$ne")

if __name__ == "__main__":
    unittest.main()
