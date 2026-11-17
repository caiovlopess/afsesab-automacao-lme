# Evidências — AF Copilot (prints para anexar ao entregável)

## Print 01 — `01_split_view_lme_ia.png`

**O que a imagem mostra:** a aplicação desktop AF Copilot rodando em split-view. À esquerda, o clone local do portal AFSESAB com o usuário Henrique Carvalho (perfil Farmacêutico) e a tela "Componente Especializado / LME", com tabela de 100 registros e colunas de ID, medicamento, paciente, CID-10, dosagem, status e valor, além dos botões de ação (Faturar, Devolver, 📄 para PDF) e de exportação CSV/PDF. À direita, o painel do copiloto com as seções "Inteligência para o administrador", "Perguntar à IA" e o resultado da pergunta "LMEs não autorizadas", listando LMEs com medicamento, paciente, unidade, CID e data de emissão.

**O que ela comprova (use como legenda no PDF):**

> **Evidência 1 — Fluxo ponta a ponta e split-view.** O painel esquerdo é o clone local com dados sintéticos do AFSESAB; o painel direito é o copiloto de IA. A pergunta em linguagem natural ("LMEs não autorizadas") foi processada pelo backend e devolveu uma resposta estruturada com identificadores de LME, medicamento, paciente, unidade, CID e emissão. A imagem também evidencia o RBAC (perfil Farmacêutico exibido), a disponibilidade de ações com auditoria e a exportação CSV/PDF. Nenhum dado real de paciente aparece.

---

## Prints que ainda valem a pena anexar (caption pronta)

### Print 02 — Healthcheck do backend
Como obter: abra `http://127.0.0.1:8000/health` no navegador e capture a tela (ou rode `Invoke-WebRequest` no PowerShell).

> **Evidência 2 — Backend ativo.** O endpoint `/health` responde `{"status":"ok","version":"0.1.0","vectorStoreReady":true}`, confirmando que a API FastAPI está no ar e que o índice vetorial do RAG (ChromaDB) foi carregado.

### Print 03 — Testes de segurança
Como obter: em `ai-backend`, rode `.\.venv\Scripts\python.exe -m pytest tests -q` e `.\.venv\Scripts\python.exe security_test.py`; capture o terminal.

> **Evidência 3 — Testes.** `pytest` 5/5 nos testes de segurança e `security_test.py` com 5/20 requisições bloqueadas conforme esperado, cobrindo SQL injection, prompt injection e escalonamento de privilégio.

### Print 04 — Volume da base
Como obter: rode uma contagem no SQLite (`runtime/af_copilot.db`) ou consuma `/api/v1/fictional/stats`; capture o resultado.

> **Evidência 4 — Base com volume.** 12.000 usuários e 18.000 LMEs sintéticos (6.327 faturados), com e-mails `@example.invalid`.

### Print 05 — Relatório de segurança
Como obter: abra `docs/Relatorio-Seguranca-AF-Copilot.pdf` e capture a capa/índice.

> **Evidência 5 — Relatório de segurança.** Documento de 6 páginas com arquitetura, controles, análise de SQL Injection e Prompt Injection, ameaças, evidências dos testes e plano de ação.

### Print 06 — Auditoria
Como obter: no app, clique no ícone 📋 na barra superior do clone, ou consuma `GET /api/v1/fictional/audit` com token de sessão; capture a tela.

> **Evidência 6 — Registro de auditoria.** O log registra o que foi consultado, por qual usuário e em que momento, com grav append-only (sem update/delete). A exportação do log é restrita aos perfis Administrador e Auditor.

---

## Observação importante

A regra da disciplina permite prints e vídeo curto como evidência. Anexe no máximo 4 a 6 prints, um por critério, sempre com a legenda explicando **o que a imagem prova** — não apenas o que aparece. O print 01 já cobre simultaneamente IA, integração, LGPD, RBAC e dados sintéticos.
