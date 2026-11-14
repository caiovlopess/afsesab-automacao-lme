"""Testes de integração da consulta com permissão e auditoria.

Prova que:
(a) o perfil autorizado lê a view da sua cidade com CPF mascarado;
(b) o perfil sem permissão não lê outra cidade nem a coleção original, e a
    tentativa negada fica registrada em audit_log;
(c) nenhum CPF completo aparece na saída;
(d) cidade desconhecida é negada e auditada.
"""

import json
import os
import re
import unittest

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import OperationFailure

from consulta_ia import (
    CIDADES,
    MONGO_HOST,
    MONGO_PORT,
    PERFIS,
    conectar,
    consultar,
    mascarar_cpf,
)

CPF_MASCARADO = re.compile(r"^\*\*\*\.\*\*\*\.\*\*\*-\d{2}$")
CPF_COMPLETO = re.compile(r"\d{3}\.\d{3}\.\d{3}-\d{2}")
CPF_SOMENTE_DIGITOS = re.compile(r"(?<!\d)\d{11}(?!\d)")


class TestIntegracaoConsulta(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        load_dotenv()
        variaveis = list(PERFIS.values()) + ["TEST_WORKFLOW_AUDIT_PASSWORD"]
        faltando = [nome for nome in variaveis if not os.getenv(nome)]
        if faltando:
            raise RuntimeError(
                "Defina no .env as variáveis: " + ", ".join(faltando)
            )
        cls.cliente_auditor = MongoClient(
            MONGO_HOST,
            MONGO_PORT,
            username="teste_auditor",
            password=os.getenv("TEST_AUDITOR_PASSWORD"),
            authSource="lme",
            serverSelectionTimeoutMS=5000,
        )
        cls.audit_log = cls.cliente_auditor["lme"]["audit_log"]

    @classmethod
    def tearDownClass(cls):
        cls.cliente_auditor.close()

    def buscar_auditoria(self, solicitacao_id):
        return self.audit_log.find_one({"solicitacao_id": solicitacao_id})

    def assert_sem_cpf_completo(self, texto):
        self.assertIsNone(CPF_COMPLETO.search(texto), "CPF formatado encontrado")
        self.assertIsNone(
            CPF_SOMENTE_DIGITOS.search(texto), "CPF com 11 dígitos encontrado"
        )

    def test_a_perfil_autorizado_recebe_dados_mascarados(self):
        resultado = consultar(
            "teste_farmaceutico_sai", "Santo Antônio de Jesus", "ATIVA", limite=5
        )
        self.assertTrue(resultado["permitido"], resultado.get("motivo"))
        self.assertGreater(
            resultado["total"],
            0,
            "Sem registros ATIVA na view; rode scripts/gerar_dados.py novamente.",
        )
        for registro in resultado["registros"]:
            self.assertEqual(registro["cidade"], "Santo Antônio de Jesus")
            self.assertRegex(registro["cpf"], CPF_MASCARADO)
        self.assert_sem_cpf_completo(
            json.dumps(resultado, ensure_ascii=False, default=str)
        )

        auditoria = self.buscar_auditoria(resultado["solicitacao_id"])
        self.assertIsNotNone(auditoria)
        self.assertTrue(auditoria["permitido"])
        self.assertEqual(auditoria["usuario"], "teste_farmaceutico_sai")
        self.assertEqual(auditoria["registros_retornados"], resultado["total"])

        print(
            "\n(a) registro retornado:",
            json.dumps(resultado["registros"][0], ensure_ascii=False),
        )
        print(
            "(a) auditoria:",
            json.dumps(
                {
                    "usuario": auditoria["usuario"],
                    "view": auditoria["view"],
                    "permitido": auditoria["permitido"],
                    "registros_retornados": auditoria["registros_retornados"],
                    "criado_em": auditoria["criado_em"].isoformat(),
                },
                ensure_ascii=False,
            ),
        )

    def test_b_perfil_sem_permissao_nao_recebe_e_registra_negacao(self):
        resultado = consultar("teste_farmaceutico_sai", "Amargosa", "ATIVA")
        self.assertFalse(resultado["permitido"])
        self.assertEqual(resultado["registros"], [])
        self.assertEqual(resultado["view"], "pacientes_amargosa")
        self.assertIn("negado", resultado["motivo"].lower())

        auditoria = self.buscar_auditoria(resultado["solicitacao_id"])
        self.assertIsNotNone(auditoria)
        self.assertFalse(auditoria["permitido"])
        self.assertEqual(auditoria["usuario"], "teste_farmaceutico_sai")
        self.assertEqual(auditoria["view"], "pacientes_amargosa")
        self.assertIn("not authorized", auditoria["motivo"].lower())

        # A coleção original também é negada para o mesmo perfil.
        cliente = conectar("teste_farmaceutico_sai")
        try:
            with self.assertRaises(OperationFailure) as erro:
                cliente["lme"]["pacientes"].find_one()
        finally:
            cliente.close()
        self.assertEqual(erro.exception.code, 13)

        print("\n(b) motivo da negacao:", resultado["motivo"])
        print(
            "(b) auditoria negada:",
            json.dumps(
                {
                    "usuario": auditoria["usuario"],
                    "view": auditoria["view"],
                    "permitido": auditoria["permitido"],
                    "motivo": auditoria["motivo"],
                    "criado_em": auditoria["criado_em"].isoformat(),
                },
                ensure_ascii=False,
            ),
        )

    def test_c_cpf_nunca_aparece_completo(self):
        resultado = consultar("teste_auditor", "Nazaré", "ATIVA", limite=10)
        self.assertTrue(resultado["permitido"], resultado.get("motivo"))
        self.assertGreater(
            resultado["total"],
            0,
            "Sem registros ATIVA na view; rode scripts/gerar_dados.py novamente.",
        )
        texto = json.dumps(resultado["registros"], ensure_ascii=False)
        self.assert_sem_cpf_completo(texto)
        for registro in resultado["registros"]:
            self.assertRegex(registro["cpf"], CPF_MASCARADO)

        # Teste direto da função de máscara (defesa em profundidade).
        self.assertEqual(mascarar_cpf("123.456.789-00"), "***.***.***-00")
        self.assertEqual(mascarar_cpf("12345678900"), "***.***.***-00")

        print(
            "\n(c) exemplo mascarado:",
            json.dumps(resultado["registros"][0], ensure_ascii=False),
        )

    def test_d_cidade_desconhecida_negada_e_auditada(self):
        resultado = consultar("teste_ia", "Cidade Inexistente", "ATIVA")
        self.assertFalse(resultado["permitido"])
        self.assertIsNone(resultado["view"])
        self.assertEqual(resultado["motivo"], "cidade fora do escopo")

        auditoria = self.buscar_auditoria(resultado["solicitacao_id"])
        self.assertIsNotNone(auditoria)
        self.assertFalse(auditoria["permitido"])
        self.assertEqual(auditoria["usuario"], "teste_ia")
        self.assertEqual(auditoria["pergunta"]["cidade"], "Cidade Inexistente")

    def test_e_status_com_tipo_invalido_rejeitado_e_auditado(self):
        # Simula uma tentativa de injeção: em vez de texto, envia um objeto.
        resultado = consultar(
            "teste_farmaceutico_sai",
            "Santo Antônio de Jesus",
            {"$ne": None},
        )
        self.assertFalse(resultado["permitido"])
        self.assertEqual(resultado["motivo"], "status inválido")
        self.assertEqual(resultado["registros"], [])

        auditoria = self.buscar_auditoria(resultado["solicitacao_id"])
        self.assertIsNotNone(auditoria)
        self.assertFalse(auditoria["permitido"])
        self.assertEqual(auditoria["motivo"], "status inválido")
        self.assertEqual(auditoria["pergunta"]["status"], "{'$ne': None}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
