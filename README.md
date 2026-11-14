# AFSESAB — Automação Inteligente de Consultas de LME

**Grupo:** AFSESAB / LME

**Integrantes:**

- Caio Victor
- Diogenes
- Kleber Lucas
- Carlos Henrique

Protótipo acadêmico para demonstrar consultas autorizadas de LME por cidade,
medicamento e status. Usa **somente dados fictícios**, MongoDB em Docker, n8n
para orquestração (workflow ainda em construção) e uma camada Python de
consulta/auditoria. **Não acessa o AFSESAB real** e **não inclui RPA com
Playwright** nesta entrega.

## O que funciona hoje

- MongoDB 7 em Docker, com 10.000 pacientes fictícios em quatro cidades.
- Views por cidade que mascaram o CPF (`***.***.***-NN`) e escondem a coleção
  original.
- Roles e usuários de teste com privilégio mínimo; auditoria em `audit_log` com
  usuário que só faz `insert`.
- Camada Python `scripts/consulta_ia.py` que consulta apenas as views, nega
  acessos fora do escopo e audita permitidos e negados.
- Testes automatizados de segurança e de integração (9 testes no total).
- Medição de latência/custo do webhook do n8n (`scripts/medir_latencia.py`),
  pronta para usar quando o workflow estiver ativo.
- Dataset sintético de fine-tuning (300 exemplos) e roteiro de treino no Colab.

## O que ainda está pendente

- Montar/exportar o workflow do n8n (`n8n/workflow_lme.json`) e rodar os casos
  C6–C8 de `docs/casos_de_teste.md`.
- Rodar a medição de latência real e salvar em `docs/evidencias/latencia.txt`.
- Executar o fine-tuning no Colab e preencher `finetuning/resultados.md`.
- RPA com Playwright (fora do escopo desta entrega; ver `docs/relatorio.md`).

## Arquitetura atual

```text
Cliente (PowerShell/CLI)
  -> webhook do n8n (ou scripts/consulta_ia.py)
  -> validação de perfil, cidade e status
  -> MongoDB: view da cidade, com credencial do próprio perfil
  -> auditoria: audit_log (usuário workflow_audit, só insert)
  -> LLM (n8n): regras fictícias + dados autorizados -> resposta formatada
```

O n8n não substitui a autorização do banco: mesmo que a validação do workflow
falhe, o usuário do perfil só consegue ler a view concedida ao seu role.

## Requisitos

- Windows com PowerShell (os comandos abaixo são para PowerShell) ou
  Linux/macOS com ajuste de caminhos.
- Python 3.10+ (testado com 3.13).
- Docker Desktop com Docker Compose.
- Para o fine-tuning: conta Google com Colab e GPU T4 (opcional).

## Rodar do zero

### 1. Clonar e instalar as dependências Python

```powershell
git clone <URL_DO_REPOSITORIO>
cd afsesab-automacao-lme
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Se a ativação do venv for bloqueada pela política do PowerShell, use
`.\.venv\Scripts\python.exe` no lugar de `python` nos comandos seguintes.

### 2. Criar o `.env`

```powershell
Copy-Item .env.example .env
```

Abra o `.env` e preencha com senhas locais diferentes:

```text
MONGO_ROOT_USER=seu_usuario_local
MONGO_ROOT_PASSWORD=sua_senha_local
TEST_FARMACEUTICO_SAI_PASSWORD=senha_local_farmaceutico
TEST_AUDITOR_PASSWORD=senha_local_auditor
TEST_IA_PASSWORD=senha_local_ia
TEST_WORKFLOW_AUDIT_PASSWORD=senha_local_auditoria_workflow
N8N_WEBHOOK_URL=http://localhost:5678/webhook/lme-consulta
N8N_REQUESTS=10
LLM_PRICE_INPUT_PER_1M=
LLM_PRICE_OUTPUT_PER_1M=
```

O `.env` está no `.gitignore` e **não deve ser commitado**. O `.env.example`
contém apenas placeholders. Preencha `LLM_PRICE_*` somente se quiser estimar
custo; sem esses valores o script de latência não calcula custo.

### 3. Subir MongoDB e n8n

```powershell
docker compose up -d
docker compose ps
```

Espere os dois serviços aparecerem como `Up`. O MongoDB fica em
`localhost:27018` (host) e `mongo:27017` (dentro do Docker). O n8n fica em
`http://localhost:5678`.

### 4. Gerar os dados fictícios e configurar acessos

```powershell
python scripts/gerar_dados.py
docker compose exec mongo mongosh --quiet --file /scripts/seguranca.js
```

O primeiro comando apaga e recria a coleção `pacientes` com 10.000 registros
fictícios. O segundo cria as views mascaradas, o `audit_log`, as roles e os
usuários de teste usando as senhas do `.env`.

Saída esperada do primeiro comando: `Total: 10000`. Saída esperada do segundo:
`Views mascaradas, audit_log, roles e usuários de teste configurados.`

### 5. Rodar os testes

```powershell
python scripts/testes_seguranca.py
python scripts/testes_integracao.py
```

Esperado: `Ran 4 tests ... OK` no primeiro e `Ran 5 tests ... OK` no segundo.
As saídas reais estão em `docs/evidencias/`.

### 6. Consultar pela camada Python (opcional)

```powershell
python scripts/consulta_ia.py `
  --perfil teste_farmaceutico_sai `
  --cidade "Santo Antônio de Jesus" `
  --status ATIVA `
  --limite 2
```

Uma consulta à cidade `Amargosa` com o mesmo perfil deve retornar
`"permitido": false` e sair com código 2, além de registrar a negação em
`audit_log`.

### 7. n8n (opcional, depende do workflow)

1. Abra `http://localhost:5678`.
2. Siga `docs/guia_n8n.md` para criar as credenciais e montar o fluxo.
3. Exporte o workflow para `n8n/workflow_lme.json` (ainda **PENDENTE** neste
   repositório).
4. Importe conforme `n8n/README.md`.
5. Com o webhook ativo, rode:

   ```powershell
   python scripts/medir_latencia.py --n 10
   ```

   Salve a saída real em `docs/evidencias/latencia.txt`. Sem tokens na resposta
   ou sem `LLM_PRICE_*`, o script informa que não calculou o custo.

### 8. Fine-tuning (opcional, no Colab)

Siga `finetuning/README.md`: gere o dataset com
`python finetuning/gerar_dataset.py`, abra `finetuning/treino.ipynb` no Colab
com GPU T4 e copie os números reais para `finetuning/resultados.md`.

## Recomeçar do zero

Para apagar **todos** os dados do MongoDB e **todo** o estado do n8n (workflows,
credenciais e execuções):

```powershell
docker compose down -v
docker compose up -d
python scripts/gerar_dados.py
docker compose exec mongo mongosh --quiet --file /scripts/seguranca.js
python scripts/testes_seguranca.py
python scripts/testes_integracao.py
```

Atenção: `down -v` remove os volumes `mongo_data` e `n8n_data`. Se você já
montou o workflow no n8n, exporte-o antes. Para apagar apenas o MongoDB,
preservando o n8n, remova somente o volume `mongo_data` (veja
`docker volume ls`).

## Estrutura do repositório

```text
docs/
  guia_n8n.md          # passo a passo do workflow
  casos_de_teste.md    # C1–C8, com status real
  matriz_papeis.md     # roles e negações
  plano_testes.md      # cenários e métricas
  regras_lme/          # 5 regras fictícias
  relatorio.md         # relatório da entrega
  checklist_entrega.md # checklist da professora
  evidencias/          # saídas reais
n8n/                   # workflow exportado (PENDENTE)
prompts/               # v1, v2 e CHANGELOG
scripts/
  gerar_dados.py       # carga fictícia
  seguranca.js         # views, roles, usuários e audit_log
  testes_seguranca.py  # 4 testes de permissão
  consulta_ia.py       # consulta + auditoria
  testes_integracao.py # 5 testes de integração
  medir_latencia.py    # latência e custo do webhook
  consultas_lentas.js  # comparação de planos/índices
finetuning/            # dataset, notebook e avaliador
```

## Segurança e privacidade

- **Dados fictícios:** nada de prontuário, CPF ou dado clínico real.
- **Autorização no banco:** o MongoDB não tem `GRANT`/`DENY` de SQL. O
  equivalente é `createRole` com privilégios mínimos por coleção/view, mais
  views que filtram cidade e mascaram CPF. O escopo não depende do prompt.
- **Views:** cada cidade tem uma view (`pacientes_sai`, `pacientes_amargosa`,
  `pacientes_nazare`, `pacientes_cruz`) sobre `pacientes`; a coleção original só
  é acessível ao administrador local.
- **Auditoria:** `teste_workflow_audit` só pode inserir em `audit_log`; o evento
  registra quem pediu, cidade/status/medicamento, view, permitido/negado, motivo
  e total de registros. Não grava nome, CPF nem a resposta do LLM.
- **CPF:** as views mascaram e a camada Python mascara de novo; os testes
  verificam que nenhum CPF completo aparece na saída.
- **Segredos:** apenas no `.env` local e nas credenciais do n8n. O JSON
  exportado do n8n deve ser conferido antes de aceitar (ver `n8n/README.md`).
- **Limites:** o webhook local não tem autenticação nesta versão; não exponha a
  porta 5678 na internet. Em uso real, revisar LGPD, autorização institucional,
  retenção e anonimização antes de enviar dados a um provedor de LLM.

## Documentação e evidências

- `docs/relatorio.md`: visão geral, o que funciona, o que falta, riscos e
  contribuição individual.
- `docs/checklist_entrega.md`: item por item da entrega, com status e evidência.
- `docs/casos_de_teste.md`: casos C1–C8, com execução real onde já houve.
- `docs/guia_n8n.md`: montagem do workflow e tradeoff do RAG.
- `docs/evidencias/`: saídas reais de testes e `explain`.
- `finetuning/resultados.md`: resultados do experimento (PENDENTE até o Colab).

## Limitações

- Base pequena (10.000 registros) e um LME por paciente; não reproduz produção.
- Tempos de `explain` variam por máquina; o relevante é a mudança de plano e a
  redução de `docsExamined`.
- O n8n é um protótipo local, sem autenticação de webhook na configuração
  padrão.
- O fine-tuning é preliminar, com 30 exemplos de teste; não é benchmark.
- O RPA com Playwright não faz parte desta entrega.
