# Fine-tuning preliminar

Experimento opcional de extração de `medicamento` e `quantidade` a partir de
texto livre de LME. Usa apenas dados fictícios.

## Arquivos

| Arquivo | Para que serve |
|---|---|
| `gerar_dataset.py` | Gera `train.jsonl` (270) e `test.jsonl` (30), com semente fixa. |
| `train.jsonl` / `test.jsonl` | Dataset sintético já gerado. |
| `treino.ipynb` | Roteiro de treino LoRA com Unsloth no Google Colab (GPU T4). |
| `avaliar.py` | Compara o modelo base com o modelo ajustado nos 30 exemplos de teste. |
| `resultados.md` | Registro dos resultados; permanece `PENDENTE` até a execução real. |

## Ordem

1. Gerar o dataset (já executado; rode de novo se quiser reproduzir):

   ```powershell
   python finetuning/gerar_dataset.py
   ```

2. Abrir `treino.ipynb` no Google Colab com GPU T4 e executar as células na
   ordem. O notebook envia `train.jsonl`, `test.jsonl` e `avaliar.py`.

3. Copiar a tabela de saída de `avaliar.py` e os tempos de treino para
   `resultados.md`.

## O que já foi executado

- `python finetuning/gerar_dataset.py`: **300 exemplos**, sendo **270 de treino**
  e **30 de teste** (5 por medicamento). Verificado que não há sobreposição entre
  treino e teste e que todos os `output` são JSON válido.

## O que ainda não foi executado

- Treino no Colab e avaliação base vs. ajustado. Até lá, `resultados.md` fica
  com `PENDENTE`. Não invente acurácia, tempo ou custo.

## Dependências do notebook

O notebook instala Unsloth, TRL, PEFT, Accelerate, bitsandbytes e Transformers
no próprio Colab. O `requirements.txt` da raiz cobre apenas a parte local
(MongoDB, geração de dados e testes), não o treino.
