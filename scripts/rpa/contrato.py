"""Contrato de integração para um RPA futuro (stub, sem acesso à rede).

Este arquivo NÃO implementa RPA e NÃO acessa o sistema real. Ele apenas define o
formato que um adaptador futuro deve respeitar para se encaixar no fluxo atual,
sem mudar autorização, auditoria ou resposta.

Uso:
    python scripts/rpa/contrato.py
"""

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class ConsultaRPA:
    """Pedido recebido pelo adaptador, com os mesmos campos do webhook."""

    perfil: str
    cidade: str
    status: str
    medicamento: str | None = None


@dataclass(frozen=True)
class ResultadoRPA:
    """Resposta no mesmo formato de ``scripts/consulta_ia.py``."""

    permitido: bool
    total: int
    registros: list[dict] = field(default_factory=list)
    motivo: str = ""


class AdaptadorRPA(Protocol):
    """Interface que um adaptador real (por exemplo, Playwright) deve cumprir."""

    def consultar(self, pedido: ConsultaRPA) -> ResultadoRPA:
        ...


class AdaptadorMock:
    """Exemplo seguro: devolve dados fictícios e não acessa nenhum sistema."""

    def consultar(self, pedido: ConsultaRPA) -> ResultadoRPA:
        # A negação ilustra o mesmo comportamento da camada Python atual.
        if pedido.cidade != "Santo Antônio de Jesus":
            return ResultadoRPA(
                permitido=False,
                total=0,
                motivo="cidade fora do escopo do perfil de demonstração",
            )

        return ResultadoRPA(
            permitido=True,
            total=1,
            registros=[
                {
                    "nome": "Paciente Fictício",
                    "cpf": "***.***.***-00",
                    "medicamento": pedido.medicamento or "Medicamento Fictício",
                    "status": pedido.status,
                }
            ],
            motivo="dados fictícios do adaptador mock",
        )


def main() -> None:
    adaptador: AdaptadorRPA = AdaptadorMock()
    resultado = adaptador.consultar(
        ConsultaRPA(
            perfil="teste_farmaceutico_sai",
            cidade="Santo Antônio de Jesus",
            status="ATIVA",
            medicamento="Medicamento Fictício",
        )
    )
    print(resultado)


if __name__ == "__main__":
    main()
