"""Mede latência e estima custo das chamadas ao webhook do n8n.

Configuração no `.env`:
- ``N8N_WEBHOOK_URL``: URL do webhook (obrigatória).
- ``N8N_REQUESTS``: número de chamadas (padrão 5).
- ``LLM_PRICE_INPUT_PER_1M`` e ``LLM_PRICE_OUTPUT_PER_1M``: preço em USD por
  1 milhão de tokens. Se não forem preenchidos, o custo não é calculado.

O script não inventa preço nem tokens: se a resposta do webhook não trouxer os
campos de uso, ele informa isso e não calcula custo.
"""

import argparse
import json
import math
import os
import statistics
import sys
import time
from urllib import error, request

from dotenv import load_dotenv

load_dotenv()

CHAVES_ENTRADA = {"prompt_tokens", "input_tokens"}
CHAVES_SAIDA = {"completion_tokens", "output_tokens"}


def post_json(url, corpo, timeout):
    """Faz um POST e devolve (status, duração_ms, corpo_json)."""
    dados = json.dumps(corpo).encode("utf-8")
    requisicao = request.Request(
        url,
        data=dados,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    inicio = time.perf_counter()
    try:
        with request.urlopen(requisicao, timeout=timeout) as resposta:
            texto = resposta.read().decode("utf-8", errors="replace")
            status = resposta.status
    except error.HTTPError as erro:
        texto = erro.read().decode("utf-8", errors="replace")
        status = erro.code
    duracao_ms = (time.perf_counter() - inicio) * 1000

    try:
        corpo_json = json.loads(texto) if texto else {}
    except json.JSONDecodeError:
        corpo_json = {"resposta_nao_json": texto}
    return status, duracao_ms, corpo_json


def extrair_tokens(obj):
    """Procura campos de tokens de entrada/saída em qualquer nível do JSON.

    Devolve ``(entrada, saida)`` ou ``None`` se nenhum campo for encontrado.
    """
    entrada = 0
    saida = 0
    encontrado = False

    def visitar(valor):
        nonlocal entrada, saida, encontrado
        if isinstance(valor, dict):
            for chave, item in valor.items():
                if chave in CHAVES_ENTRADA and isinstance(item, (int, float)):
                    entrada += int(item)
                    encontrado = True
                elif chave in CHAVES_SAIDA and isinstance(item, (int, float)):
                    saida += int(item)
                    encontrado = True
                else:
                    visitar(item)
        elif isinstance(valor, list):
            for item in valor:
                visitar(item)

    visitar(obj)
    return (entrada, saida) if encontrado else None


def percentil(valores, p):
    """Percentil por posto mais próximo (nearest-rank)."""
    if not valores:
        return None
    ordenados = sorted(valores)
    indice = max(0, math.ceil(p / 100 * len(ordenados)) - 1)
    return ordenados[indice]


def ler_preco(nome):
    valor = os.getenv(nome)
    if not valor:
        return None
    try:
        return float(valor)
    except ValueError:
        print(f"Aviso: {nome} não é um número; custo não será calculado.")
        return None


def main():
    parser = argparse.ArgumentParser(
        description="Mede latência e estima custo do webhook n8n."
    )
    parser.add_argument(
        "--url",
        default=os.getenv("N8N_WEBHOOK_URL", ""),
        help="URL do webhook (padrão: N8N_WEBHOOK_URL do .env).",
    )
    parser.add_argument(
        "--n",
        type=int,
        default=int(os.getenv("N8N_REQUESTS", "5")),
        help="Número de chamadas (padrão: N8N_REQUESTS ou 5).",
    )
    parser.add_argument(
        "--perfil", default="teste_farmaceutico_sai", help="Perfil da consulta."
    )
    parser.add_argument(
        "--cidade",
        default="Santo Antônio de Jesus",
        help="Cidade da consulta.",
    )
    parser.add_argument("--status", default="ATIVA", help="Status da LME.")
    parser.add_argument(
        "--medicamento",
        default="Adalimumabe 40mg",
        help="Medicamento da consulta.",
    )
    parser.add_argument(
        "--timeout", type=float, default=120, help="Timeout de cada chamada em s."
    )
    args = parser.parse_args()

    if not args.url:
        print(
            "Defina N8N_WEBHOOK_URL no .env ou use --url.", file=sys.stderr
        )
        return 1
    if args.n < 1:
        print("--n deve ser pelo menos 1.", file=sys.stderr)
        return 1

    corpo = {
        "perfil": args.perfil,
        "cidade": args.cidade,
        "status": args.status,
        "medicamento": args.medicamento,
    }
    print("=== Medição do webhook n8n ===")
    print(f"URL: {args.url}")
    print(f"Requisições: {args.n}")
    print("Corpo:", json.dumps(corpo, ensure_ascii=False))
    print()

    latencias = []
    status_codes = []
    tokens_entrada = 0
    tokens_saida = 0
    respostas_com_tokens = 0

    for numero in range(1, args.n + 1):
        try:
            status, duracao, resposta = post_json(
                args.url, corpo, args.timeout
            )
        except Exception as erro:  # erro de rede, DNS, timeout etc.
            print(f"Chamada {numero}: erro de rede: {erro}")
            continue

        latencias.append(duracao)
        status_codes.append(status)
        tokens = extrair_tokens(resposta)
        if tokens is not None:
            respostas_com_tokens += 1
            tokens_entrada += tokens[0]
            tokens_saida += tokens[1]

        print(
            f"Chamada {numero}: HTTP {status}, {duracao:.1f} ms, "
            f"tokens={'sim' if tokens is not None else 'não retornados'}"
        )

    if not latencias:
        print("\nNenhuma chamada concluída; nada para resumir.", file=sys.stderr)
        return 1

    sucessos = sum(1 for codigo in status_codes if 200 <= codigo < 300)
    print("\n--- Resumo ---")
    print(f"Sucessos (2xx): {sucessos}/{len(status_codes)}")
    print(f"Latência média: {statistics.mean(latencias):.1f} ms")
    print(f"Latência p95: {percentil(latencias, 95):.1f} ms")
    print(f"Latência mínima: {min(latencias):.1f} ms")
    print(f"Latência máxima: {max(latencias):.1f} ms")

    if respostas_com_tokens == 0:
        print("Tokens de entrada: a API não retornou tokens.")
        print("Tokens de saída: a API não retornou tokens.")
        print("Custo estimado: não calculado (a API não retornou tokens).")
        return 0

    print(f"Respostas com tokens: {respostas_com_tokens}/{len(latencias)}")
    print(f"Tokens de entrada (soma): {tokens_entrada}")
    print(f"Tokens de saída (soma): {tokens_saida}")

    preco_entrada = ler_preco("LLM_PRICE_INPUT_PER_1M")
    preco_saida = ler_preco("LLM_PRICE_OUTPUT_PER_1M")
    if preco_entrada is None or preco_saida is None:
        print(
            "Custo estimado: não calculado (configure "
            "LLM_PRICE_INPUT_PER_1M e LLM_PRICE_OUTPUT_PER_1M no .env)."
        )
        return 0

    custo = (
        tokens_entrada / 1_000_000 * preco_entrada
        + tokens_saida / 1_000_000 * preco_saida
    )
    print(f"Custo estimado do conjunto de {args.n} chamadas: US$ {custo:.6f}")
    print(f"Custo estimado por chamada: US$ {custo / args.n:.6f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
