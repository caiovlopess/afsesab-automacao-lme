"""Avalia a extração de medicamento/quantidade no modelo base e no ajustado.

Métrica principal: percentual de exemplos em que a saída é um JSON válido e
traz o medicamento E a quantidade corretos. Também reporta JSON válido,
medicamento correto e quantidade correta separadamente.

Este script depende de GPU/transformers e foi pensado para rodar no Google
Colab. Ele NÃO contém resultados: os números só aparecem quando você executar.

Exemplo (no Colab, dentro de finetuning/):

    python avaliar.py \
      --base-model Qwen/Qwen2.5-0.5B-Instruct \
      --adapter lme-qwen-lora \
      --test test.jsonl \
      --limite 30 \
      --saida resultados_avaliacao.json
"""

import argparse
import json
from pathlib import Path

DIRETORIO = Path(__file__).resolve().parent


def carregar_exemplos(caminho, limite):
    exemplos = []
    with Path(caminho).open(encoding="utf-8") as arquivo:
        for linha in arquivo:
            if linha.strip():
                exemplos.append(json.loads(linha))
    return exemplos[:limite]


def normalizar_medicamento(valor):
    if not isinstance(valor, str):
        return ""
    return " ".join(valor.strip().lower().split())


def normalizar_quantidade(valor):
    try:
        return int(valor)
    except (TypeError, ValueError):
        return None


def extrair_json(texto):
    """Extrai o primeiro objeto JSON da resposta do modelo."""
    inicio = texto.find("{")
    if inicio == -1:
        return None
    try:
        objeto, _ = json.JSONDecoder().raw_decode(texto[inicio:])
    except json.JSONDecodeError:
        return None
    return objeto if isinstance(objeto, dict) else None


def montar_prompt(exemplo):
    return exemplo["instruction"] + "\n\n" + exemplo["input"]


def carregar_modelo(base_model, adapter, device):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(base_model)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    tipo = torch.float16 if device == "cuda" else torch.float32
    modelo = AutoModelForCausalLM.from_pretrained(
        base_model,
        torch_dtype=tipo,
        device_map="auto" if device == "cuda" else None,
    )
    if adapter:
        from peft import PeftModel

        modelo = PeftModel.from_pretrained(modelo, adapter)
    modelo.to(device)
    modelo.eval()
    return modelo, tokenizer


def gerar_resposta(modelo, tokenizer, prompt, device, max_new_tokens):
    import torch

    mensagens = [{"role": "user", "content": prompt}]
    texto = tokenizer.apply_chat_template(
        mensagens, tokenize=False, add_generation_prompt=True
    )
    entradas = tokenizer(texto, return_tensors="pt").to(device)
    with torch.inference_mode():
        saida = modelo.generate(
            **entradas,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            pad_token_id=tokenizer.pad_token_id,
        )
    novos_tokens = saida[0][entradas["input_ids"].shape[1] :]
    return tokenizer.decode(novos_tokens, skip_special_tokens=True).strip()


def avaliar(modelo, tokenizer, exemplos, device, max_new_tokens):
    metricas = {
        "total": len(exemplos),
        "json_valido": 0,
        "medicamento_correto": 0,
        "quantidade_correta": 0,
        "ambos_corretos": 0,
        "falhas": [],
    }

    for indice, exemplo in enumerate(exemplos, start=1):
        resposta = gerar_resposta(
            modelo, tokenizer, montar_prompt(exemplo), device, max_new_tokens
        )
        esperado = json.loads(exemplo["output"])
        obtido = extrair_json(resposta)

        json_ok = obtido is not None
        medicamento_ok = json_ok and normalizar_medicamento(
            obtido.get("medicamento")
        ) == normalizar_medicamento(esperado["medicamento"])
        quantidade_ok = json_ok and normalizar_quantidade(
            obtido.get("quantidade")
        ) == normalizar_quantidade(esperado["quantidade"])
        ambos_ok = medicamento_ok and quantidade_ok

        metricas["json_valido"] += int(json_ok)
        metricas["medicamento_correto"] += int(medicamento_ok)
        metricas["quantidade_correta"] += int(quantidade_ok)
        metricas["ambos_corretos"] += int(ambos_ok)

        if not ambos_ok and len(metricas["falhas"]) < 5:
            metricas["falhas"].append(
                {
                    "indice": indice,
                    "esperado": esperado,
                    "resposta": resposta,
                }
            )
        print(
            f"  {indice:2d}/{len(exemplos)} "
            f"json={'ok' if json_ok else 'falhou'} "
            f"medicamento={'ok' if medicamento_ok else 'falhou'} "
            f"quantidade={'ok' if quantidade_ok else 'falhou'}"
        )

    for chave in (
        "json_valido",
        "medicamento_correto",
        "quantidade_correta",
        "ambos_corretos",
    ):
        metricas[chave + "_pct"] = round(
            100 * metricas[chave] / metricas["total"], 1
        ) if metricas["total"] else 0.0
    return metricas


def imprimir_tabela(resultados):
    print("\n| Modelo | JSON válido | Medicamento | Quantidade | Ambos |")
    print("|---|---:|---:|---:|---:|")
    for nome, m in resultados.items():
        print(
            f"| {nome} | {m['json_valido_pct']}% | "
            f"{m['medicamento_correto_pct']}% | "
            f"{m['quantidade_correta_pct']}% | "
            f"{m['ambos_corretos_pct']}% |"
        )
    print(
        "\nAcuracidade principal = coluna 'Ambos' "
        "(JSON válido + medicamento + quantidade)."
    )


def main():
    parser = argparse.ArgumentParser(
        description="Avalia extração de LME no modelo base e no ajustado."
    )
    parser.add_argument(
        "--base-model", default="Qwen/Qwen2.5-0.5B-Instruct"
    )
    parser.add_argument(
        "--adapter",
        help="Pasta do adaptador LoRA. Sem ela, avalia só o modelo base.",
    )
    parser.add_argument(
        "--test", default=str(DIRETORIO / "test.jsonl"), help="Arquivo JSONL."
    )
    parser.add_argument("--limite", type=int, default=30)
    parser.add_argument("--max-new-tokens", type=int, default=64)
    parser.add_argument(
        "--saida", help="Arquivo JSON opcional para salvar as métricas."
    )
    args = parser.parse_args()

    try:
        import torch
    except ImportError:
        print(
            "PyTorch não está instalado. Rode este script no Colab, depois de "
            "instalar transformers, peft e torch."
        )
        return 1

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Dispositivo: {device}")
    print(f"Modelo base: {args.base_model}")
    print(f"Adaptador: {args.adapter or '(nenhum)'}")
    print(f"Exemplos: {args.limite}")

    exemplos = carregar_exemplos(args.test, args.limite)
    if not exemplos:
        print("Nenhum exemplo de teste encontrado.")
        return 1

    resultados = {}
    print("\nAvaliando modelo base...")
    modelo, tokenizer = carregar_modelo(args.base_model, None, device)
    resultados["base"] = avaliar(
        modelo, tokenizer, exemplos, device, args.max_new_tokens
    )

    if args.adapter:
        print("\nAplicando adaptador LoRA e avaliando o modelo ajustado...")
        from peft import PeftModel

        modelo = PeftModel.from_pretrained(modelo, args.adapter)
        modelo.eval()
        resultados["ajustado"] = avaliar(
            modelo, tokenizer, exemplos, device, args.max_new_tokens
        )

    imprimir_tabela(resultados)

    if args.saida:
        with Path(args.saida).open("w", encoding="utf-8") as arquivo:
            json.dump(resultados, arquivo, ensure_ascii=False, indent=2)
        print(f"\nMétricas salvas em {args.saida}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
