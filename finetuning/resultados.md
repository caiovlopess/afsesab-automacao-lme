# Fine-tuning preliminar — resultados

Este documento registra o experimento de extração de medicamento e quantidade a
partir de texto livre de LME. **Nenhum número de treino ou de acurácia foi
inventado.** O que ainda não foi executado está marcado como `PENDENTE`.

## 1. Dataset

Gerado por `python finetuning/gerar_dataset.py` (semente fixa 42), com dados
fictícios. Contagens reais da execução local:

| Item | Quantidade |
|---|---:|
| Total | 300 |
| Treino (`train.jsonl`) | 270 |
| Teste (`test.jsonl`) | 30 |
| Medicamentos distintos | 6 |
| Exemplos de teste por medicamento | 5 |

Cada exemplo tem os campos `instruction`, `input` (texto livre) e `output`
(JSON com `medicamento` e `quantidade`). O teste é estratificado por
medicamento; as quantidades usadas são 30, 60 e 90.

Exemplo real gerado:

```json
{
  "instruction": "Extraia o medicamento e a quantidade da solicitação de LME. Responda somente com JSON no formato {\"medicamento\": \"...\", \"quantidade\": 0}.",
  "input": "Renovação de LME: Sirolimo 1mg, 90 comprimidos, para o paciente Bruno Lima (Santo Antônio de Jesus).",
  "output": "{\"medicamento\": \"Sirolimo 1mg\", \"quantidade\": 90}"
}
```

## 2. Configuração do experimento

| Item | Valor |
|---|---|
| Modelo base | `Qwen/Qwen2.5-0.5B-Instruct` (alternativa: 1.5B) |
| Técnica | LoRA com Unsloth |
| `max_seq_length` | 1024 |
| `r` / `lora_alpha` | 16 / 16 |
| Épocas | 3 |
| Batch por dispositivo | 2 |
| Acumulação de gradiente | 4 |
| Learning rate | 2e-4 |
| GPU | Google Colab T4 |

Esses são os parâmetros configurados no notebook, não resultados.

## 3. Como executar

1. Abra `finetuning/treino.ipynb` no Google Colab com GPU T4.
2. Execute as células na ordem; envie `train.jsonl`, `test.jsonl` e
   `avaliar.py` quando solicitado.
3. Ao final, copie a tabela de avaliação e os tempos de treino para a seção 4.
4. Comando de avaliação usado no notebook:

   ```bash
   python avaliar.py \
     --base-model Qwen/Qwen2.5-0.5B-Instruct \
     --adapter lme-qwen-lora \
     --test test.jsonl \
     --limite 30 \
     --saida resultados_avaliacao.json
   ```

## 4. Resultados

### 4.1 Treino

| Métrica | Valor |
|---|---|
| Ambiente (Colab/GPU) | PENDENTE: registrar a GPU e a versão do Unsloth |
| Data da execução | PENDENTE: data real do treino |
| Tempo de treino (s) | PENDENTE: copiar `train_runtime` |
| Loss final de treino | PENDENTE: copiar `train_loss` |
| Adaptador salvo | PENDENTE: informar o caminho/arquivo |

### 4.2 Avaliação nos 30 exemplos de teste

| Modelo | JSON válido | Medicamento correto | Quantidade correta | Ambos corretos (acurácia) |
|---|---:|---:|---:|---:|
| Base | PENDENTE | PENDENTE | PENDENTE | PENDENTE |
| Ajustado (LoRA) | PENDENTE | PENDENTE | PENDENTE | PENDENTE |

**Definição da acurácia principal:** percentual de exemplos em que a saída é um
JSON válido **e** o medicamento **e** a quantidade estão corretos.

> PENDENTE: rodar o notebook no Colab e substituir cada célula acima pela saída
> real de `avaliar.py`. Não preencher por estimativa.

## 5. Leitura dos resultados

Quando os números forem preenchidos, comparar:

- quantos exemplos o modelo base já acerta (linha de base);
- quanto o LoRA melhora JSON válido, medicamento, quantidade e acerto completo;
- se o ganho é maior que a variação esperada com apenas 30 exemplos (cada acerto
  vale 3,3 pontos percentuais).

## 6. Limitações

- Dataset sintético, pequeno e com vocabulário repetitivo; não representa a
  variedade de textos reais.
- Trinta exemplos de teste permitem apenas uma indicação preliminar; não é um
  benchmark.
- O modelo pode aprender o formato do dataset e não generalizar para redações
  novas.
- O experimento não usa dados reais, não passou por revisão clínica e não
  substitui avaliação de privacidade/LGPD.
- O fine-tuning não altera as permissões do MongoDB nem o escopo por cidade; a
  autorização continua no backend.
