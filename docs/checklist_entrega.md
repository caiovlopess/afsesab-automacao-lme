# Checklist de entrega

Legenda: **OK** = existe e foi executado/verificado; **PENDENTE** = depende de
uma execução que ainda não foi feita; **N/A** = fora do escopo desta entrega,
declarado no relatório.

## Parte comum

| Item | Status | Evidência |
|---|---|---|
| Repositório organizado com pastas de código, docs, prompts e fine-tuning | OK | `README.md`, `docs/`, `scripts/`, `prompts/`, `finetuning/` |
| README com integrantes e passo a passo do zero | OK | `README.md` |
| Arquitetura descrita e atualizada (MongoDB + n8n + Docker) | OK | `README.md`, `docs/relatorio.md` |
| Uso exclusivo de dados fictícios | OK | `scripts/gerar_dados.py`, `docs/regras_lme/`, `finetuning/` |
| MongoDB em Docker com volume e porta local | OK | `docker-compose.yml` |
| n8n em Docker com a pasta de regras montada | OK | `docker-compose.yml`; `docker compose exec n8n ls /home/node/regras_lme` |
| Carga de 10.000 pacientes fictícios | OK | `scripts/gerar_dados.py`; saída real `Total: 10000` |
| Comparação de consultas com e sem índice | OK | `docs/evidencias/consulta_cidade_status_vigencia.txt`, `consulta_medicamento_status.txt` |
| Relatório de 1–2 páginas com integrantes, riscos e contribuição individual | OK | `docs/relatorio.md` |
| Nenhum segredo no repositório; `.env` ignorado | OK | `.gitignore`, `.env.example`; varredura final |
| RPA com Playwright | N/A | Fora do escopo; contrato, riscos e pré-requisitos em `scripts/rpa/README.md`; justificativa na seção 7 de `docs/relatorio.md` |

## IA

| Item | Status | Evidência |
|---|---|---|
| Prompt v1 | OK | `prompts/v1.md` |
| Prompt v2 com recusa sem permissão, CPF protegido e formato fixo | OK | `prompts/v2.md` |
| CHANGELOG explicando o que mudou de v1 para v2 e por quê | OK | `prompts/CHANGELOG.md` |
| Base de regras fictícias (4–5 documentos curtos) | OK | `docs/regras_lme/` (5 arquivos) |
| Workflow do n8n com webhook, consulta, regras, LLM e auditoria | PARCIAL | `n8n/workflow_lme.json` exportado; guia em `docs/guia_n8n.md`; falta executar C6–C8 |
| RAG das regras no n8n (leitura direta dos arquivos) | PENDENTE | `docs/guia_n8n.md`, seção 9; depende do workflow montado |
| Dataset sintético de fine-tuning (300 exemplos, 270/30) | OK | `finetuning/gerar_dataset.py`, `train.jsonl`, `test.jsonl` |
| Notebook de treino LoRA/Unsloth para Colab | OK (roteiro) | `finetuning/treino.ipynb` |
| Avaliador base vs. ajustado | OK (código) | `finetuning/avaliar.py` |
| Resultados reais do fine-tuning | PENDENTE | `finetuning/resultados.md` (até rodar no Colab) |
| Medição de latência e custo | PENDENTE | `scripts/medir_latencia.py`; falta `docs/evidencias/latencia.txt` |
| Casos de teste de IA/LLM (C6–C8) | PENDENTE | `docs/casos_de_teste.md` |

## Segurança e integração

| Item | Status | Evidência |
|---|---|---|
| Roles com privilégio mínimo em vez de `GRANT`/`DENY` | OK | `scripts/seguranca.js`, `docs/matriz_papeis.md` |
| Views por cidade, sem expor a coleção original | OK | `scripts/seguranca.js`, `docs/matriz_papeis.md` |
| CPF mascarado nas views e na saída | OK | `scripts/seguranca.js`, `scripts/consulta_ia.py`, testes |
| Usuário de auditoria que só faz `insert` | OK | `scripts/seguranca.js`, `scripts/testes_seguranca.py` |
| Auditoria de tentativas permitidas e negadas | OK | `scripts/consulta_ia.py`, `docs/evidencias/integracao.txt` |
| Testes de permissão (4) | OK | `scripts/testes_seguranca.py`, `docs/evidencias/seguranca.txt`; `Ran 4 tests ... OK` |
| Testes de integração (5), incluindo NoSQL injection | OK | `scripts/testes_integracao.py`; `docs/evidencias/integracao.txt` |
| Consulta com o usuário do perfil (nunca root) | OK | `scripts/consulta_ia.py` |
| Negação de outra cidade e da coleção original | OK | `docs/evidencias/integracao.txt` |
| Casos de segurança documentados | OK | `docs/casos_de_teste.md` (C2–C5) |
| Webhook do n8n testado (permitido e negado) | PENDENTE | `docs/casos_de_teste.md` (C6–C7) |
| Prompt injection no LLM testado | PENDENTE | `docs/casos_de_teste.md` (C8) |
| Segredos apenas no `.env` e nas credenciais do n8n | OK | `.env.example` sem valores reais; `n8n/README.md` |
| JSON exportado do n8n sem credenciais/chaves | OK | `n8n/workflow_lme.json`; varredura de `password`, `apiKey`, `Authorization`, `Bearer`, `sk-` sem correspondências |
| Revisão de LGPD/uso real documentada | OK | `docs/relatorio.md`, `README.md` |

## Itens que dependem de execução do usuário

1. Montar o workflow em `http://localhost:5678` seguindo `docs/guia_n8n.md`.
2. Exportar para `n8n/workflow_lme.json` e conferir segredos.
3. Rodar C6–C8 de `docs/casos_de_teste.md`.
4. Rodar `python scripts/medir_latencia.py --n 10` e salvar em
   `docs/evidencias/latencia.txt`.
5. Rodar `finetuning/treino.ipynb` no Colab e preencher
   `finetuning/resultados.md`.

> Enquanto esses cinco itens não forem executados, os status acima permanecem
> `PENDENTE`. Não substitua por valores estimados.

## Validação final executada

| Verificação | Resultado |
|---|---|
| `docker compose config --quiet` | OK |
| `python -m py_compile` em todos os scripts | OK |
| Recriar o banco `lme` do zero (`dropDatabase` + `gerar_dados.py` + `seguranca.js`) | OK: 10.000 registros, views/roles recriadas |
| `python scripts/testes_seguranca.py` | OK: 4 testes |
| `python scripts/testes_integracao.py` | OK: 5 testes |
| Notebook e dataset | OK: 27 células, 270 treino, 30 teste, sem sobreposição |
| Varredura de segredos (valores reais do `.env`) | OK: nenhuma senha/chave encontrada nos arquivos |
| `.env` fora do Git | OK: ignorado e não staged |
| `docker compose down -v` completo | **NÃO EXECUTADO**: apagaria as 3 credenciais e o workflow existentes no n8n. O comando está documentado no README; a recriação do banco foi validada separadamente. |
