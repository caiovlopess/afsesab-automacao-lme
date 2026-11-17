# AF Copilot — Automação Inteligente de Consultas de LME (AFSESAB)

**Grupo:** Núcleo de Automação Farmacêutica

**Integrantes:**

- Caio Victor Lopes Serra — matrícula 231071580
- Diógenes Santana — matrícula [PREENCHER]
- Kleber Lucas — matrícula [PREENCHER]
- Carlos Henrique Santos de Carvalho — matrícula 232070273

**Disciplinas:** Projeto de Inteligência Artificial; Segurança e Otimização de Banco de Dados; Integração.

**Repositório:** https://github.com/caiovlopess/afsesab-automacao-lme

**Escopo:** projeto acadêmico com **somente dados fictícios/anonimizados**. Nenhuma chave, senha ou dado real de paciente é versionado. A integração com o AFSESAB real depende de autorização institucional.

---

## 1. Visão geral — o que mudou desde 27/10

A proposta inicial previa uma **aplicação web** com RPA e MongoDB. A regra da disciplina — **nada de SaaS, aplicação web ou site** — levou a uma arquitetura desktop. O resultado é um repositório com duas camadas complementares:

| Camada | O que é | Onde está |
|---|---|---|
| **Aplicação principal (Fase 1)** | App desktop split-view: clone local do AFSESAB + copiloto de IA, com FastAPI, SQLite e RAG | `desktop-client/`, `ai-backend/`, `tools/` |
| **Protótipo/evedências (complementar)** | Consulta autorizada em MongoDB, n8n, prompts versionados, fine-tuning, scripts de segurança e latência | `scripts/`, `n8n/`, `finetuning/`, `prompts/`, `docs/` |

O MongoDB **não foi abandonado**: ficou reservado para a Fase 2 (auditoria/cache), com `docker-compose.yml` e Repository Pattern preparados.

---

## 2. Problema que o sistema resolve

Consultas individuais e repetitivas de LME consomem tempo da gestão farmacêutica e dificultam buscas por município, medicamento, vigência e status.

- **Entrada:** pergunta em linguagem natural ou filtros de município, medicamento, vigência e status.
- **Saída:** relação mínima de registros autorizados, estruturada.
- **Maior risco:** acesso indevido, exposição de dados pessoais/clínicos e associação incorreta entre paciente e município.

---

## 3. O que funciona hoje

### Aplicação desktop (principal)

- Split-view: ~70% clone local do AFSESAB / ~30% copiloto de IA.
- Login local com sessão por token (PBKDF2) e RBAC: Farmacêutico / Administrador / Auditor.
- 9 menus e 47 submenus com títulos e colunas próprios; 47/47 assinaturas distintas.
- Resolvedor de LME: Autorizar / Faturar / Dispensar / Devolver, com gravação no SQLite e auditoria.
- Copiloto: busca global, perguntas em linguagem natural, insights agregados e alertas operacionais.
- RAG local (ChromaDB + sentence-transformers) com respostas instantâneas para protocolos conhecidos.
- OCR multimodal para validação de receitas; PDFs de LME via ReportLab.
- Auditoria append-only, exportação CSV/PDF restrita por perfil.
- Sanitização LGPD zero-trust no Electron antes de qualquer envio; nenhuma chave no cliente.

### Protótipo complementar

- MongoDB 7 em Docker com 10.000 pacientes fictícios, views por cidade com CPF mascarado.
- Roles e usuários de teste com privilégio mínimo; `audit_log` com usuário que só faz `insert`.
- `scripts/consulta_ia.py`: consulta apenas as views permitidas, nega accessos fora do escopo e audita permitidos/negados.
- Workflow do n8n exportado em `n8n/workflow_lme.json` + guia de montagem em `docs/guia_n8n.md`.
- Prompts versionados (`prompts/v1.md`, `v2.md`, `CHANGELOG.md`).
- Dataset sintético de fine-tuning (300 exemplos, 270 treino / 30 teste), notebook LoRA/Unsloth e avaliador.
- Scripts de consultas lentas, medição de latência e testes de segurança/integração.

---

## 4. Arquitetura ponta a ponta

```text
[ Clone AFSESAB / BrowserView ]
   -> preload REA (MutationObserver) -> ipcRenderer
   -> Electron Main (filtro LGPD zero-trust)
   -> Sidebar (X-Internal-Auth-Token, CORS af://af-desktop)
   -> FastAPI 127.0.0.1:8000 (Pydantic + autenticação + RBAC)
        -> SQLite (SQLAlchemy): usuarios, LMEs, catalogo, sessoes, auditoria
        -> ChromaDB: vetores dos protocolos (RAG)
        -> Gemini: geracao e multimodal (somente no backend)
   -> resposta estruturada na sidebar
```

O LLM **nunca acessa o banco diretamente**: ele interpreta e propõe filtros; o backend valida esquema, tipos e permissões antes de executar. Nenhuma chave de API existe no cliente.

---

## 5. Estrutura do repositório

```text
afsesab-automacao-lme/
├── desktop-client/     Electron 30 + TypeScript (app principal)
├── ai-backend/         FastAPI, RAG, SQLite, seguranca, scripts
├── tools/              Playwright / CDP (recon e validacao)
├── docs/               relatorios, regras LME, plano de testes, evidencias, PDFs
├── n8n/                workflow exportado + README
├── finetuning/         dataset, notebook, avaliador, resultados
├── prompts/            v1, v2 e CHANGELOG
├── scripts/            CLI, seguranca, latencia, consultas lentas, rpa (stub)
├── .github/workflows/  CI (pytest + npm build)
├── requirements.txt    dependencias Python (app + prototipo)
├── start.ps1           sobe backend + Electron
└── smoke-test.ps1      valida health, RAG, 401 e 415
```

---

## 6. Como rodar

### 6.1 Aplicação desktop (principal)

```powershell
# Backend
cd ai-backend
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r ..\requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# Electron (outro terminal)
cd desktop-client
npm install
npm run build
npm start -- --demo        # dados ficticios
```

**Tudo de uma vez**, na raiz: `.\start.ps1` (sobe o backend, espera `/health` e abre o Electron).

### 6.2 Protótipo MongoDB / n8n (complementar)

```powershell
docker compose up -d
python -m pip install -r requirements.txt
python scripts/gerar_dados.py
python scripts/seguranca.js
```

O guia completo do n8n está em `docs/guia_n8n.md`.

---

## 7. Evidências por disciplina

| Critério | Onde está |
|---|---|
| Relatório de andamento (1–2 p.) | `docs/relatorio.md` |
| README e como rodar | este arquivo |
| Fluxo RAG ponta a ponta | `ai-backend/app/services/rag_service.py`, `docs/evidencias/01_split_view_lme_ia.png` |
| Prompts versionados | `prompts/v1.md`, `v2.md`, `CHANGELOG.md` |
| Casos de teste | `docs/casos_de_teste.md`, `ai-backend/tests/test_security.py`, `security_test.py` |
| Fine-tuning (dataset + avaliador) | `finetuning/` |
| Custo e latência | `scripts/medir_latencia.py`, `docs/evidencias/` |
| Papéis e permissões | `docs/matriz_papeis.md`, `scripts/seguranca.js`, RBAC no backend |
| Proteção de dado sensível | LGPD no Electron + RedactingFilter no backend + `docs/Relatorio-Seguranca-AF-Copilot.pdf` |
| Base com volume | 12.000 usuários / 18.000 LMEs (SQLite) e 10.000 pacientes (MongoDB) |
| Consultas lentas | `scripts/consultas_lentas.js`, `docs/evidencias/consulta_*.txt` |
| IA × permissões + auditoria | `scripts/consulta_ia.py`, `docs/evidencias/integracao.txt`, `audit_logs` |

---

## 8. Segurança

Chaves apenas em `.env` (gitignored); `.env.example` sem valores reais. CORS restrito a `af://af-desktop`, token local com `hmac.compare_digest`, Pydantic v2 com `extra="forbid"`, upload de 5 MB com validação de magic bytes, logs com redação de CPF/CNS/e-mail, ORM parametrizado, PromptGuard com 12 padrões, CPF mascarado nas views do MongoDB e auditoria append-only.

---

## 9. Pendências

- Concluir a execução/validação dos casos C6–C8 do workflow do n8n (`n8n/workflow_lme.json` já exportado).
- Salvar a medição de latência/custo em `docs/evidencias/latencia.txt`.
- Executar o fine-tuning no Colab e preencher `finetuning/resultados.md` com números reais.
- RPA no portal real depende de autorização institucional; há apenas contrato e stub em `scripts/rpa/`.

> Onde não há medição, o projeto declara pendente. Em segurança, evidência vale mais do que afirmação.

---

## 10. Documentação adicional

- `TECNOLOGIAS.txt` — inventário completo de tecnologias e versões.
- `VALIDATION.md` — validação ponta a ponta (API, Electron e LGPD).
- `docs/Relatorio-Seguranca-AF-Copilot.pdf` — relatório de segurança (6 páginas).
- `docs/evidencias/LEGENDS.md` — legendas prontas para os prints.
- `ai-backend/README.md`, `desktop-client/README.md`, `tools/README.md`.
