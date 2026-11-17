# Validação executada (2026-11-16)

Ambiente: Windows, Node 24, Electron 30, Python 3.11 (venv), FastAPI 0.115.

## Backend

```
py -V:Astral/CPython3.11.16 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt   # OK
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

`smoke-test.ps1` resultados:

| Teste | Resultado |
| --- | --- |
| `GET /health` | `200 {"status":"ok","version":"0.1.0"}` |
| `POST /analyze-context` (sem API key) | 200 com resposta de fallback estruturada |
| Sem `X-Internal-Auth-Token` | **401** |
| Upload `.txt` (magic bytes inválidos) | **415** |

## Cliente

```
cd desktop-client && npm install && npm run build   # tsc + copy-assets: OK
.\node_modules\.bin\electron.cmd . --remote-debugging-port=9223
```

`tools/validate-app.mjs` resultados:

| Verificação | Resultado |
| --- | --- |
| Sidebar carregada | `af://af-desktop/index.html`, 3 botões |
| `window.afDesktop` (contextBridge) | `object` |
| REA no BrowserView (`window.__AF_REA__`) | `object` |
| `inspectStructure()` via IPC + `executeJavaScript` | 7 elementos mapeados |
| `analyzeContext()` via IPC → Main → FastAPI | resposta JSON válida |
| `getBackendUrl()` | `http://127.0.0.1:8000` |

## Fluxo LGPD fim a fim

`tools/validate-rea.mjs` disparou um `input` no portal com:

```
metformina 850 mg E11 CPF 123.456.789-00
```

A Sidebar recebeu **somente**:

```json
{"drugs":["metformina"],"dosages":["850 mg"],"cid10":["E11"],
 "safeText":"metformina 850 mg E11","source":"afsesab"}
```

O CPF foi removido no Main antes de qualquer saída do processo. ✅

## App empacotado + chave Gemini

- `GEMINI_API_KEY` configurada **somente** em `ai-backend/.env` (gitignored).
  Busca no repositório: nenhuma ocorrência em código/renderer/logs.
- Modelo principal `gemini-3.8-flash` (conforme solicitado). A chave atingiu o
  limite diário do free tier desse modelo (20 req/dia); configurado fallback
  automático `gemini-3.1-flash-lite`, validado com **uma** chamada mínima.
- `transport="rest"` + `timeout=30` + fallback evitam travamentos por retry gRPC.
- `electron-builder` falhou por symlinks (sem Developer Mode); empacotamento manual
  em `release/AF Copilot/AF Copilot.exe`, validado:
  - Sidebar `af://af-desktop`, API exposta, badge apontando ao backend;
  - REA ativo no BrowserView; `inspectStructure()` = 8 elementos;
  - backend subiu automaticamente ao abrir o `.exe` (health 200).

## Dados fictícios (modo demo)

- Login no site real **não foi criado**: o portal exige e-mail válido e a identidade
  informada não é um e-mail. Como você pediu, seguimos apenas com dados fictícios.
- SQLite gerou 12.000 usuários e 18.000 LMEs (`faturada` = 6.327). Endpoints
  `/fictional/stats`, `/fictional/users` e `/fictional/lmes?status=faturada` OK.
- Portal mock local carregado no painel esquerdo via `--demo` (file://).
- Teste de captura com valor fictício `Metformina 850 mg E11 CPF 123.456.789-00`:
  a Sidebar recebeu `metformina`, `insulina`, `850 mg`, `100 UI`, `E11` —
  **CPF removido**. Bug corrigido: o heurístico de nome próprio apagava o fármaco
  quando o rótulo do campo continha palavras capitalizadas; agora fármacos são
  protegidos antes da redaction e rótulos não entram no texto sanitizado.

## Clone + login (validado)

- Tela de login com PBKDF2 (210.000 iterações + salt), sem senha em texto no código.
- Login `POST /api/v1/auth/login` → 200 e abertura do app principal.
- Clone local com 9 menus / 19 submenus; dashboard mostrou 6 cards
  (12.000 usuários, 18.000 LMEs, 6.327 faturadas).
- Navegação `Componente Especializado > LME` carregou 100 linhas fictícias.
- Sidebar do copiloto sem badge de backend (info removida conforme pedido).

## Resolvedor de problemas (implementado)

- Ações reais nas LMEs: Autorizar / Faturar / Dispensar / Devolver — alteram o
  status no SQLite e refletem na tabela na hora (validado: pendente → autorizada).
- Auditoria append-only: loga login, cadastro de medicamento e mudanças de status;
  visualização no clone (ícone 📋) e exportação CSV/PDF (RBAC: só Admin/Auditor —
  Farmacêutico recebeu 403 corretamente).
- Alertas operacionais no dashboard (6 achados da IA).
- Cache de insights com TTL de 5 min: 2ª chamada caiu de 13.258 ms para 3 ms.
- Busca global única: paciente (`Arlindo` → 100 linhas), CID (`E11` → 100 LMEs),
  fornecedor e medicamento.
- Validação de receita por LME (botão 📷) com diálogo de arquivo + OCR multimodal.
- RBAC com sessão (`X-Session-Token`), perfis Farmacêutico/Administrador/Auditor.
- Testes pytest: 5/5 passaram. CI no GitHub Actions (segurança + build).
- Corrigido: login devolvia `session_token` (snake_case) e o cliente lia
  `sessionToken` — causava 401 "Sessão ausente" nas ações.

## Segurança (teste com 5/20 requisições)

- SQL Injection: todas as consultas usam SQLAlchemy ORM parametrizado; o único
  SQL cru é estático (`GROUP BY status`). Chaves de view/export validadas por
  regex `^[a-z0-9_]{2,40}$` e `lme_id` limitado a `1..100000` → 3 payloads
  maliciosos retornaram 422.
- Arquivo SQLite com permissão restrita (`0600`; no Windows `icacls` em produção).
- Prompt injection: 12 payloads (PT/EN) testados no guard local — 12/12 bloqueados;
  3 entradas legítimas sem falso positivo; PII redigida na saída do modelo.
- Integração: `/admin/ask` e `/admin/insights` sinalizam bloqueio; RAG e visão
  delimitam entrada do usuário como dados e redigem PII da resposta.
- Comando: `python security_test.py` (5 requisições HTTP, 0–3 chamadas ao Gemini).

## Correção do paciente do PDF (nome trocado)

- Causa: a tabela do clone vinha de um dataset determinístico (`build_master`),
  mas o endpoint do PDF buscava `FictionalLme` direto do banco — os IDs não
  coincidiam (clicar em Fábio abria o PDF de Sandra).
- Correção: `build_lme_pdf_from_row()` usa a **mesma linha** da tabela; o endpoint
  seleciona `master[(id-1) % 100]`. `admin_ask._pending_lmes` também foi alinhado.
- Validado em 5 IDs: tabela e PDF coincidem em paciente + medicamento
  (ex.: ID 26 → Mariana Martins Fonseca / Etanercepte nos dois).

## Ícone e barra superior

- Ícone: brasão oficial da Bahia (Wikimedia, domínio público) convertido para
  `assets/app.ico` (7 tamanhos) e aplicado às janelas + empacotamento.
- Brasão também exibido dentro do cartão de login e no cabeçalho do clone.
- Botões da barra: ☰ recolhe/expande menu, ? abre ajuda, 👤 abre perfil, ⏻ faz
  logout real (volta à tela de acesso). Todos validados.

## Exportação, auditoria e pacientes

- CSV (2,6 KB) e PDF (9,5 KB) exportados por `GET /fictional/export/{key}` e
  salvos em `Downloads/AF Copilot/`.
- `POST /admin/audit` retornou 8 achados (pendências, baixa conversão, unidades
  críticas, pacientes com muitos LMEs).
- Tela LME: 48 pacientes distintos em 100 registros + filtro por paciente.

## Correção da tela de login branca

- Causa: `login/index.html` referenciava `app.js`, mas o build copiava o script como
  `login.js`; sem handler, o form fazia submit nativo (`?`) e o protocolo `af://`
  tentava abrir arquivo com `?` no nome → `ERR_FILE_NOT_FOUND`.
- Correções: script corrigido para `login.js`, botão `type=button`, query string
  removida no handler do protocolo e `Menu.setApplicationMenu(null)` (sem barra
  File/Edit/View).
- Validado: login visível, credenciais aceitas e app principal aberto.

## Correções finais (screenshots)

- `rel_comprometimento`: CONSUMO 53 / ESTOQUE 441 / 12,0% (antes vazio).
- `pedido`: `PED-20260026` com unidade, medicamento e status.
- `rel_autorizada_faturada`: 30 autorizadas / 20 faturadas / diferença 10.
- `entrada`: `NF-10270`, quantidade 22, data 03/11/2026.
- `ajuste_vinculo`, `paciente_ext`, `paciente_insulina`: pacientes reais
  (Tatiane Nascimento Costa, Marcos Moraes Filho, Gustavo Azevedo Frota) e
  tratamentos/insulinas variados.
- LME e LME em Transferência agora mostram o paciente.
- Cadastro: `POST /fictional/medicamentos` gravou `SIM-020001` no SQLite.
- Pergunta "fornecedor de Salvador" → CNPJ + contato + telefone + endereço.
- Pergunta "LMEs não autorizadas" → 4.450 pendentes com relação de 100 itens.
- RAG local: 4 ms, fonte PCDT Diabetes, 3 passos e exemplo.
- Dashboard: 6 cards, 1 gráfico de rosca e 6 barras.

## Nomes realistas + IA administrativa

- Base regerada com 12.000 nomes brasileiros plausíveis (1º: Arlindo Cruz Santos Silva)
  e e-mails `@email.com`; rótulos "fictício" removidos da UI e do PDF.
- Toolbar do administrador com 4 focos; insight gerado via fallback
  `gemini-3.1-flash-lite` com números agregados reais da base.
- Limite duro de 12s por modelo aplicado também ao RAG (`rag_service.py`).
- Validação final: 47/47 assinaturas de telas distintas; PDF sem a palavra "fictício".

## PDFs de LME

- `GET /api/v1/fictional/lmes/1/pdf` → 200, 3.614 bytes, magic `%PDF-`.
- Clone: 100 botões 📄 na tela LME; clique abriu janela com
  `.../Temp/LME-000001.pdf` no visualizador embutido do Chromium.
- Exemplo salvo em `docs/LME-ficticia-exemplo.pdf`.

## Correção das abas repetidas

- Estrutura real dos menus lida no portal autenticado via CDP: 9 menus / 47 submenus.
- Antes: todos os submenus renderizavam a mesma tabela de LME.
- Depois: endpoint `/api/v1/fictional/view/{key}` com 47 especificações
  (título + colunas + fonte de dados) — `tools/check-views.mjs` confirmou
  **47 assinaturas distintas / 47**.
- UI validada: `Medicamento` (13 linhas), `Pedido` (100), `Dispensação` (100),
  cada um com colunas diferentes.

## Correções feitas durante a validação

- `config.py`: `BASE_DIR` era `app/` em vez de `ai-backend/`; `NoDecode` para `CORS_ORIGINS` (pydantic-settings 2.7.1).
- `audit_repository.py`: import faltando `T`.
- `local-auth.ts`: caminho do token corrigido para 4 níveis (`dist/main/security`).
- `webview-preload.ts`: imports relativos não funcionam em preload sandboxed → metadados inlined.
- `renderer/app.ts`: `import type` gerava `exports` no browser → tipos inferidos da API global.
- `rag_service.py`: `/health` não carrega mais embeddings; fallback sem API key não baixa modelo; imports lazy.
- `vision_service.py`: import do Gemini lazy.
