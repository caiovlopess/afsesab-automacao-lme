# Guia do workflow n8n — consulta de LME com permissão e auditoria

Este guia monta, na interface do n8n, o mesmo fluxo que
`scripts/consulta_ia.py` já executa em Python:

```text
Webhook (perfil + pergunta)
  -> valida e escolhe a view
  -> consulta a view com a credencial MongoDB do perfil
  -> lê as regras fictícias
  -> LLM responde no formato do prompt v2
  -> grava o evento em audit_log
  -> responde ao webhook
```

Versão usada como referência: n8n **2.47.7** no `docker-compose.yml` deste
repositório. Os nomes de nós podem variar um pouco entre versões; quando isso
acontecer, use a busca de nós e escolha o nome equivalente.

## Antes de começar

1. Suba os serviços:

   ```powershell
   docker compose up -d
   ```

2. Confirme que o n8n responde em `http://localhost:5678` e que o MongoDB está
   em `localhost:27018` (host) ou `mongo:27017` (dentro do Docker).
3. Confirme que a pasta de regras está montada dentro do n8n:

   ```powershell
   docker compose exec n8n ls /home/node/regras_lme
   ```

   Devem aparecer os cinco arquivos `01_vigencia.md` a `05_cancelamento.md`.
4. Tenha o `.env` aberto apenas para copiar senhas para as credenciais do n8n.
   Nunca cole senha ou chave em nó, expressão, Code node ou arquivo do
   repositório.

## 1. Criar as credenciais no n8n

No menu lateral esquerdo, clique no ícone de chave (**Credentials**) e depois em
**Create Credential**. Repita para cada item abaixo.

### 1.1 MongoDB do farmacêutico

- Procure e selecione **MongoDB**.
- **Credential Name:** `MongoDB - teste_farmaceutico_sai`
- **Configuration:** `Values` (não use Connection String)
- **Host:** `mongo`
- **Port:** `27017`
- **Database:** `lme`
- **User:** `teste_farmaceutico_sai`
- **Password:** copie `TEST_FARMACEUTICO_SAI_PASSWORD` do seu `.env`
- **Authentication Source:** `lme`
- **Authentication Mechanism:** `SCRAM-SHA-256`
- Clique em **Save**. Use **Test** se o botão existir.

### 1.2 MongoDB do auditor

Mesmos valores, mudando apenas:

- **Credential Name:** `MongoDB - teste_auditor`
- **User:** `teste_auditor`
- **Password:** `TEST_AUDITOR_PASSWORD`

### 1.3 MongoDB da IA

- **Credential Name:** `MongoDB - teste_ia`
- **User:** `teste_ia`
- **Password:** `TEST_IA_PASSWORD`

### 1.4 MongoDB de auditoria (só insert)

- **Credential Name:** `MongoDB - workflow_audit`
- **User:** `teste_workflow_audit`
- **Password:** `TEST_WORKFLOW_AUDIT_PASSWORD`

Esse é o único usuário que o workflow usa para escrever em `audit_log`.

### 1.5 Credencial do LLM

- Procure **OpenAI** (ou o provedor que você for usar) e crie a credencial.
- **Credential Name:** `OpenAI - LME`
- Cole a chave **somente** no campo de API key da credencial.
- Salve. A chave não deve aparecer em nenhum nó nem no JSON exportado.

## 2. Criar o workflow

No menu lateral, clique em **Workflows** -> **Create Workflow** (ou **Add
workflow**). Renomeie o workflow para `LME - consulta com auditoria`.

Os nomes dos nós abaixo são usados nas expressões. Mantenha exatamente estes
nomes:

| Ordem | Nome do nó | Tipo |
|---|---|---|
| 1 | `Receber pergunta` | Webhook |
| 2 | `Validar e mapear` | Code |
| 3 | `Permitido?` | If |
| 4 | `Escolher perfil` | Switch |
| 5 | `Buscar farmaceutico` | MongoDB |
| 6 | `Buscar auditor` | MongoDB |
| 7 | `Buscar IA` | MongoDB |
| 8 | `Agregar registros` | Aggregate |
| 9 | `Ler regras` | Read/Write Files from Disk |
| 10 | `Agregar regras` | Aggregate |
| 11 | `Montar contexto` | Code |
| 12 | `Responder com LLM` | Basic LLM Chain |
| 13 | `Auditar permitido` | MongoDB |
| 14 | `Responder sucesso` | Respond to Webhook |
| 15 | `Auditar negado` | MongoDB |
| 16 | `Responder negado` | Respond to Webhook |

## 3. Nó 1 — `Receber pergunta`

Adicione um nó **Webhook**.

- **HTTP Method:** `POST`
- **Path:** `lme-consulta`
- **Authentication:** `None` (é um protótipo local; não exponha esta porta na
  internet)
- **Respond:** `Using 'Respond to Webhook' Node`

O corpo esperado é:

```json
{
  "perfil": "teste_farmaceutico_sai",
  "cidade": "Santo Antônio de Jesus",
  "status": "ATIVA",
  "medicamento": "Adalimumabe 40mg"
}
```

`medicamento` é opcional; se não for enviado, a consulta traz todos os
medicamentos daquela cidade/status.

## 4. Nó 2 — `Validar e mapear`

Adicione um nó **Code**.

- **Language:** `JavaScript`
- **Mode:** `Run Once for All Items`
- Apague o conteúdo padrão e cole:

```javascript
// Valida a entrada e decide se o perfil pode ler a view da cidade.
const cidades = {
  'Santo Antônio de Jesus': 'pacientes_sai',
  'Amargosa': 'pacientes_amargosa',
  'Nazaré': 'pacientes_nazare',
  'Cruz das Almas': 'pacientes_cruz',
};

const viewsPermitidas = {
  teste_farmaceutico_sai: ['pacientes_sai'],
  teste_auditor: Object.values(cidades),
  teste_ia: Object.values(cidades),
};

const statusValidos = ['ATIVA', 'VENCIDA', 'PENDENTE', 'CANCELADA'];
const p = $input.first().json;

const view = cidades[p.cidade] || null;
const perfilConhecido = Object.prototype.hasOwnProperty.call(
  viewsPermitidas,
  p.perfil,
);
const permitido =
  Boolean(view) &&
  statusValidos.includes(p.status) &&
  perfilConhecido &&
  viewsPermitidas[p.perfil].includes(view);

const filtro = { cidade: p.cidade, 'lme.status': p.status };
if (p.medicamento) {
  filtro['lme.medicamento'] = p.medicamento;
}

return [
  {
    json: {
      solicitacao_id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
      perfil: p.perfil,
      cidade: p.cidade,
      status: p.status,
      medicamento: p.medicamento || null,
      view,
      permitido,
      motivo: permitido
        ? null
        : view
          ? 'perfil sem permissão para esta view'
          : 'cidade ou status inválido',
      filtro,
      filtroJson: JSON.stringify(filtro),
    },
  },
];
```

> O n8n faz uma verificação para dar uma resposta de negação limpa. A
> autorização real continua sendo a credencial do MongoDB: mesmo que essa
> verificação falhe, o usuário do perfil não consegue ler a view de outra
> cidade.

Conecte a saída de `Receber pergunta` à entrada de `Validar e mapear`.

## 5. Nó 3 — `Permitido?`

Adicione um nó **If**.

- **Conditions:**
  - **Left Value:** `{{ $json.permitido }}`
  - **Operator:** `is true`
  - **Right Value:** deixe vazio
- **Options:** valores padrão.

Conecte `Validar e mapear` -> `Permitido?`.

A saída `true` segue para o nó 4. A saída `false` segue para `Auditar negado`
(nó 15).

## 6. Nó 4 — `Escolher perfil`

Adicione um nó **Switch**.

- **Mode:** `Rules`
- Crie três regras:

| Regra | Left Value | Operator | Right Value | Output Name |
|---|---|---|---|---|
| 1 | `{{ $json.perfil }}` | `equals` | `teste_farmaceutico_sai` | `Farmaceutico` |
| 2 | `{{ $json.perfil }}` | `equals` | `teste_auditor` | `Auditor` |
| 3 | `{{ $json.perfil }}` | `equals` | `teste_ia` | `IA` |

- **Fallback Output:** desligado (a validação do nó 2 já barra perfil
  desconhecido).

Conecte `Permitido?` (saída true) -> `Escolher perfil`.

## 7. Nós 5, 6 e 7 — consulta na view

Adicione três nós **MongoDB**, um para cada saída do Switch. Configure os três
do mesmo jeito, mudando apenas a credencial.

### 7.1 `Buscar farmaceutico` (saída `Farmaceutico`)

- **Credential:** `MongoDB - teste_farmaceutico_sai`
- **Resource:** `Document`
- **Operation:** `Find Documents`
- **Database:** `lme`
- **Collection:** `{{ $json.view }}`
- **Query (JSON Format):** `{{ $json.filtroJson }}`
- **Projection (JSON Format):**

  ```json
  { "_id": 0, "nome": 1, "cidade": 1, "lme": 1, "cpf": 1 }
  ```

- **Limit:** `20`
- **Options:** padrão.

### 7.2 `Buscar auditor` (saída `Auditor`)

Mesma configuração, com:

- **Credential:** `MongoDB - teste_auditor`
- Nome do nó: `Buscar auditor`

### 7.3 `Buscar IA` (saída `IA`)

Mesma configuração, com:

- **Credential:** `MongoDB - teste_ia`
- Nome do nó: `Buscar IA`

> Se a interface reclamar que `{{ $json.filtroJson }}` não é um JSON válido,
> troque o campo **Query (JSON Format)** para o modo **Query Parameters**:
> **Query:** `{ "cidade": $1, "lme.status": $2 }`
> **Query Parameters:** `["{{ $json.cidade }}", "{{ $json.status }}"]`
> Para incluir medicamento, use `"lme.medicamento": $3` e acrescente
> `{{ $json.medicamento }}` na lista (ou deixe a consulta sem esse campo
> quando vier vazio).

### 7.4 Tratamento de erro do MongoDB (recomendado)

Nos três nós MongoDB, abra **Settings** (engrenagem) -> **On Error** e escolha
**Continue (using error output)**, se essa opção existir na sua versão.
Conecte a saída de erro dos três nós ao nó `Auditar negado` (nó 15). Se a opção
não existir, siga sem ela: a validação do nó 2 já impede a consulta fora do
escopo na operação normal.

## 8. Nó 8 — `Agregar registros`

Adicione um nó **Aggregate**.

- **Aggregate:** `All Item Data`
- **Put Output in Field:** `registros`

Conecte as saídas de sucesso dos três nós MongoDB (`Buscar farmaceutico`,
`Buscar auditor`, `Buscar IA`) à entrada de `Agregar registros`. Só um ramo do
Switch executa por requisição, então o Aggregate recebe apenas os registros
daquele perfil.

## 9. Nó 9 — `Ler regras`

Adicione um nó **Read/Write Files from Disk**.

- **Operation:** `Read File(s) from Disk`
- **File(s) Selector:** `/home/node/regras_lme/*.md`
- **Options:** padrão.

Conecte `Agregar registros` -> `Ler regras`. O nó devolve um item por arquivo,
com o conteúdo no campo `data`.

## 10. Nó 10 — `Agregar regras`

Adicione outro nó **Aggregate**.

- **Aggregate:** `All Item Data`
- **Put Output in Field:** `regras`

Conecte `Ler regras` -> `Agregar regras`.

## 11. Nó 11 — `Montar contexto`

Adicione um nó **Code**.

- **Language:** `JavaScript`
- **Mode:** `Run Once for All Items`

Cole:

```javascript
// Junta as regras fictícias com os registros autorizados e monta o prompt v2.
const registros = $('Agregar registros').first().json.registros || [];
const arquivos = $('Agregar regras').first().json.regras || [];
const base = $('Validar e mapear').first().json;

const regras = arquivos
  .map((arquivo) => `# ${arquivo.fileName}\n${arquivo.data}`)
  .join('\n\n');

// Defesa em profundidade: a view já mascara o CPF, mas mascara de novo.
const mascarar = (texto) =>
  texto
    .replace(/\d{3}\.\d{3}\.\d{3}-\d{2}/g, (m) => '***.***.***-' + m.slice(-2))
    .replace(/\b\d{11}\b/g, (m) => '***.***.***-' + m.slice(-2));

const dados = mascarar(JSON.stringify(registros));

const prompt = `Você é um assistente de demonstração para consultas autorizadas de LME.

Siga estas regras em ordem:
1. Permissão: a consulta só foi autorizada para o perfil e a cidade informados.
   Se a permissão não estiver confirmada, recuse sem revelar dados.
2. Fontes: use somente as regras fictícias e os dados abaixo. Não use
   conhecimento externo, não infira fatos e não invente campos ou resultados.
3. Privacidade: nunca revele CPF completo. Se houver CPF, mostre apenas a forma
   mascarada ***.***.***-NN ou omita o campo.
4. Incerteza: se a resposta não estiver nas fontes/dados, escreva
   "Não informado nas fontes/dados consultados."
5. Escopo: as regras são fictícias; não são orientação oficial ou clínica.

Responda sempre neste formato, sem conteúdo fora dele:
Resultado: <resposta curta ou recusa>
Fonte: <documento e/ou campos consultados; ou "nenhuma">
Observação: <limitação relevante; ou "nenhuma">

REGRAS FICTÍCIAS RECUPERADAS:
${regras}

DADOS AUTORIZADOS (CPF já mascarado):
${dados}

PERGUNTA:
perfil=${base.perfil}; cidade=${base.cidade}; status=${base.status}; medicamento=${base.medicamento || 'todos'}
`;

return [
  {
    json: {
      ...base,
      registros,
      prompt,
    },
  },
];
```

Conecte `Agregar regras` -> `Montar contexto`.

> **RAG escolhido:** leitura direta dos cinco arquivos curtos de regras. Isso
> mantém o workflow simples e determinístico. Veja o tradeoff na seção 14.

## 12. Nó 12 — `Responder com LLM`

Adicione um nó **Basic LLM Chain**.

- **Prompt:** `Define below`
- **Prompt (User Message):** `{{ $json.prompt }}`

Conecte `Montar contexto` -> `Responder com LLM`.

Abaixo do nó, no conector **Model**, adicione um nó **OpenAI Chat Model** (ou o
modelo do provedor escolhido):

- **Credential:** `OpenAI - LME`
- **Model:** escolha o modelo disponível na sua conta (por exemplo,
  `gpt-4o-mini`, se ele existir na sua conta).
- **Options:** padrão.

Não cole a chave no nó do modelo; ela fica apenas na credencial.

A resposta do LLM fica no campo `text` da saída do `Responder com LLM`.

## 13. Nós 13 a 16 — auditoria e resposta

### 13.1 `Auditar permitido` (MongoDB)

Adicione um nó **MongoDB**.

- **Credential:** `MongoDB - workflow_audit`
- **Resource:** `Document`
- **Operation:** `Insert Document`
- **Database:** `lme`
- **Collection:** `audit_log`
- **Fields (JSON):**

  ```json
  {
    "solicitacao_id": "{{ $('Montar contexto').item.json.solicitacao_id }}",
    "evento": "consulta_lme_n8n",
    "usuario": "{{ $('Montar contexto').item.json.perfil }}",
    "pergunta": {
      "cidade": "{{ $('Montar contexto').item.json.cidade }}",
      "status": "{{ $('Montar contexto').item.json.status }}",
      "medicamento": "{{ $('Montar contexto').item.json.medicamento }}"
    },
    "view": "{{ $('Montar contexto').item.json.view }}",
    "permitido": true,
    "motivo": null,
    "registros_retornados": {{ $('Montar contexto').item.json.registros.length }},
    "criado_em": "{{ $now.toISO() }}"
  }
  ```

Conecte `Responder com LLM` -> `Auditar permitido`.

> O audit não guarda nome, CPF nem o texto da resposta. Ele registra apenas
> quem pediu, o que foi consultado, quando, a view, o total de registros e se
> foi permitido.

### 13.2 `Responder sucesso` (Respond to Webhook)

Adicione um nó **Respond to Webhook**.

- **Respond With:** `JSON`
- **Response Code:** `200`
- **Response Body:**

  ```json
  {
    "solicitacao_id": "{{ $('Montar contexto').item.json.solicitacao_id }}",
    "permitido": true,
    "resposta": "{{ $('Responder com LLM').item.json.text }}"
  }
  ```

Conecte `Auditar permitido` -> `Responder sucesso`.

### 13.3 `Auditar negado` (MongoDB)

Adicione outro nó **MongoDB**.

- **Credential:** `MongoDB - workflow_audit`
- **Resource:** `Document`
- **Operation:** `Insert Document`
- **Database:** `lme`
- **Collection:** `audit_log`
- **Fields (JSON):**

  ```json
  {
    "solicitacao_id": "{{ $('Validar e mapear').item.json.solicitacao_id }}",
    "evento": "consulta_lme_n8n",
    "usuario": "{{ $('Validar e mapear').item.json.perfil }}",
    "pergunta": {
      "cidade": "{{ $('Validar e mapear').item.json.cidade }}",
      "status": "{{ $('Validar e mapear').item.json.status }}",
      "medicamento": "{{ $('Validar e mapear').item.json.medicamento }}"
    },
    "view": "{{ $('Validar e mapear').item.json.view }}",
    "permitido": false,
    "motivo": "{{ $('Validar e mapear').item.json.motivo }}",
    "registros_retornados": 0,
    "criado_em": "{{ $now.toISO() }}"
  }
  ```

Conecte a saída `false` de `Permitido?` -> `Auditar negado`. Se você configurou
as saídas de erro do MongoDB, conecte-as também a este nó.

### 13.4 `Responder negado` (Respond to Webhook)

Adicione um nó **Respond to Webhook**.

- **Respond With:** `JSON`
- **Response Code:** `403`
- **Response Body:**

  ```json
  {
    "solicitacao_id": "{{ $('Validar e mapear').item.json.solicitacao_id }}",
    "permitido": false,
    "motivo": "{{ $('Validar e mapear').item.json.motivo }}"
  }
  ```

Conecte `Auditar negado` -> `Responder negado`.

## 14. Testar o workflow

1. No topo do workflow, clique em **Save**.
2. Para testar sem ativar, clique em **Listen for test event** no nó Webhook e
   execute o PowerShell:

   ```powershell
   $corpo = @{
     perfil = "teste_farmaceutico_sai"
     cidade = "Santo Antônio de Jesus"
     status = "ATIVA"
     medicamento = "Adalimumabe 40mg"
   } | ConvertTo-Json

   Invoke-RestMethod -Method Post `
     -Uri "http://localhost:5678/webhook-test/lme-consulta" `
     -ContentType "application/json; charset=utf-8" `
     -Body ([Text.Encoding]::UTF8.GetBytes($corpo))
   ```

3. Teste a negação: troque `cidade` para `"Amargosa"` mantendo o perfil
   `teste_farmaceutico_sai`. O retorno deve ser HTTP 403 com
   `"permitido": false`, e um documento deve aparecer em `audit_log`.
4. Depois de validar, clique em **Active** no topo e use a URL de produção
   `http://localhost:5678/webhook/lme-consulta`.
5. Para conferir o audit como auditor:

   ```powershell
   docker compose exec -T mongo mongosh --quiet --eval "db.getSiblingDB('admin').auth(process.env.MONGO_INITDB_ROOT_USERNAME, process.env.MONGO_INITDB_ROOT_PASSWORD); printjson(db.getSiblingDB('lme').audit_log.find().sort({criado_em:-1}).limit(3).toArray())"
   ```

## 15. RAG em memória: por que não usei como caminho principal

O caminho principal lê os cinco arquivos de regras e entrega todos como
contexto. Tradeoff:

- **Vantagens:** determinístico, sem custo de embeddings, funciona sem
  serviço externo, não perde o índice quando o n8n reinicia.
- **Desvantagens:** não faz busca semântica; envia todas as regras em toda
  chamada; não escala se a base crescer muito.

O corpus atual é pequeno (cinco arquivos curtos), então a leitura direta é
suficiente para o protótipo.

Se quiser demonstrar o vector store em memória, a versão 2.47.7 do n8n oferece
os nós **In Memory Vector Store Insert** e **In Memory Vector Store Load**
(experimentais). O caminho seria:

1. um workflow separado de ingestão: **Read/Write Files from Disk** ->
   **Default Data Loader** -> **Recursive Character Text Splitter** ->
   **In Memory Vector Store Insert** com **Embeddings OpenAI**;
2. no workflow de consulta, **In Memory Vector Store Load** (mesmo `Memory
   Key`) -> retriever -> **Basic LLM Chain**.

Desvantagens: os dados ficam em RAM e são perdidos quando o n8n reinicia; é
preciso rodar a ingestão antes de cada consulta (ou após cada restart); há mais
nós, mais pontos de falha e custo de embeddings. Para este trabalho, o ganho
não compensa o risco.

## 16. Exportar e conferir

1. No workflow, clique nos três pontos (**...**) -> **Download** (ou
   **Export**).
2. Salve o arquivo como `n8n/workflow_lme.json` neste repositório.
3. Abra o JSON em um editor e procure por `password`, `apiKey`, `api_key`,
   `Authorization`, `Bearer`, `sk-`. O export do n8n não deve conter segredos,
   mas essa conferência é obrigatória antes de aceitar o arquivo.
4. Se encontrar qualquer segredo, apague o arquivo exportado, remova o valor do
   nó/credencial e exporte de novo.

## 17. Limitações

- O webhook não tem autenticação nesta versão local. Não exponha a porta 5678
  na internet; se precisar, configure **Header Auth** no nó Webhook.
- O LLM recebe dados fictícios de pacientes. Em uso real, isso exigiria
  avaliação de privacidade/LGPD e, preferencialmente, anonimização antes do
  provedor.
- O prompt reduz o risco de resposta inventada, mas não substitui as permissões
  do MongoDB.
- O RPA com Playwright não faz parte desta entrega.
