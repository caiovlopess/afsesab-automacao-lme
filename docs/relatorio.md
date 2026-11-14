# Relatório — Automação de consultas de LME (protótipo acadêmico)

**Disciplina:** ______________________

**Data:** ____ / ____ / ______

| Integrante | Nome completo | Matrícula |
|---|---|---|
| 1 | Caio Victor ______________________ | ____________ |
| 2 | Diogenes ________________________ | ____________ |
| 3 | Kleber Lucas _____________________ | ____________ |
| 4 | Carlos Henrique __________________ | ____________ |

## 1. Objetivo e escopo

O trabalho prototipa uma consulta autorizada de LME por cidade, medicamento e
status. A entrega usa **apenas dados fictícios** e não acessa o sistema real da
AFSESAB. O escopo desta versão é demonstrar a separação entre autorização no
banco (com usuários autenticados no MongoDB), recuperação de regras, resposta de
um LLM e auditoria. RPA com Playwright **não** faz parte desta entrega.

## 2. O que já funciona (comprovado)

- **MongoDB em Docker** com 10.000 pacientes fictícios em quatro cidades
  (`scripts/gerar_dados.py`).
- **Views por cidade** que filtram o município, omitem `_id` e mascaram o CPF no
  formato `***.***.***-NN` (`scripts/seguranca.js`).
- **Roles e usuários de teste** com privilégio mínimo. O farmacêutico lê apenas
  `pacientes_sai`; o auditor lê as quatro views e o `audit_log`; a IA lê as views
  e insere auditoria; o usuário de workflow só insere em `audit_log`.
- **Testes de segurança:** 4 testes executados com `OK`, cobrindo leitura da
  coleção original, views fora do escopo, `audit_log` e máscara de CPF
  (`docs/evidencias/` e `docs/plano_testes.md`).
- **Camada Python de consulta** (`scripts/consulta_ia.py`): conecta com o usuário
  do perfil (nunca root), consulta somente a view, valida tipos e grava cada
  tentativa em `audit_log` com o usuário `teste_workflow_audit`.
- **Testes de integração:** 5 testes executados com `OK`, provando consulta
  permitida com CPF mascarado, negação de outra cidade e da coleção original,
  registro da negação, ausência de CPF completo e rejeição de status enviado como
  objeto (`{"$ne": null}`) — `docs/evidencias/integracao.txt`.
- **Comparação de índices** com `explain("executionStats")`: as duas consultas
  passam de `COLLSCAN` para `IXSCAN`, com redução de `docsExamined`
  (`docs/evidencias/consulta_cidade_status_vigencia.txt` e
  `consulta_medicamento_status.txt`).
- **Prompt v2** com recusa sem permissão, uso exclusivo do contexto recuperado,
  proibição de CPF completo e formato fixo (`prompts/`).
- **Dataset sintético de fine-tuning** com 300 exemplos, 270 de treino e 30 de
  teste (`finetuning/`).

## 3. O que falta

- **Workflow do n8n:** o guia está pronto (`docs/guia_n8n.md`), mas o JSON
  exportado (`n8n/workflow_lme.json`) ainda não foi gerado. Por isso os casos
  C6–C8 de `docs/casos_de_teste.md` estão `PENDENTE`.
- **Latência e custo reais:** `scripts/medir_latencia.py` está implementado e foi
  validado com um servidor local, mas a medição do webhook real depende do
  workflow ativo. O arquivo `docs/evidencias/latencia.txt` ainda não existe.
- **Fine-tuning:** os scripts e o notebook estão prontos; o treino no Colab e a
  comparação base vs. ajustado ainda não foram executados. `finetuning/resultados.md`
  permanece `PENDENTE`.
- **RPA (Playwright):** fora da entrega. Não foi implementado nem executado, e
  não há integração com o sistema real. Existe apenas um contrato de integração
  com dados fictícios (`scripts/rpa/`); os pré-requisitos estão na seção 7.
- **Autenticação do webhook:** a versão local não tem autenticação; é um
  protótipo e não deve ser exposto na internet.

## 4. O que mudou na arquitetura desde 27/10

A versão anterior era uma CLI Python (`src/app_cli.py`) com carga em
`src/seed_mongodb.py`, coleções `cidades`, `pacientes`, `consultas_lme` e
`auditoria`, e RPA simulado. O código antigo foi descartado.

A versão atual:

- substitui a CLI antiga (`src/app_cli.py`) por **Docker Compose** com MongoDB e
  n8n, mantendo uma camada Python de referência (`scripts/consulta_ia.py`);
- usa **views + roles do MongoDB** como fronteira de autorização, em vez de
  confiar apenas na validação da aplicação;
- separa a **auditoria** em um usuário que só faz `insert`, inclusive para
  tentativas negadas;
- adiciona uma **camada Python** (`consulta_ia.py`) que simula o que o n8n fará e
  serve de referência testável;
- adiciona **prompts versionados** e um **dataset de fine-tuning**;
- usa **dados fictícios** no lugar de qualquer dado do sistema real.

O RPA deixou de ser simulado e passou a constar explicitamente como pendência.

## 5. Segurança e privacidade

O MongoDB **não possui os comandos SQL `GRANT` e `DENY`**. O equivalente é:

- `createRole`/`updateRole` com **privilégios mínimos** por banco, coleção ou
  view (por exemplo, apenas `find` em `pacientes_sai`);
- **views** que aplicam o filtro de cidade e mascaram o CPF antes de expor o
  dado;
- usuários separados para consulta, auditoria e workflow;
- `audit_log` como coleção separada, com `insert` para o workflow e `find` para
  o auditor.

A autorização é aplicada pelo banco, não pelo prompt. Se o LLM for induzido a
pedir outra cidade, a credencial do perfil continua sem permissão para ler a view
correspondente. Os testes verificam o código de erro 13 (`Unauthorized`) e a
presença do evento negado no `audit_log`. O CPF é mascarado na view e novamente
na saída da camada Python. Nenhuma senha ou chave real está no repositório; o
`.env` é ignorado e o `.env.example` só tem placeholders.

## 6. Principais riscos

- **Privacidade/LGPD:** o protótipo usa dados fictícios, mas um uso real exigiria
  base legal, retenção, anonimização e revisão antes de enviar dados a um
  provedor de LLM.
- **Prompt injection:** o prompt reduz o risco, mas não é controle de segurança;
  a proteção real é o escopo do banco. O caso C8 ainda não foi executado.
- **n8n sem autenticação:** a porta 5678 não deve ser exposta; em produção seria
  necessário Header Auth/OAuth e HTTPS.
- **Cobertura de testes:** 30 exemplos de fine-tuning e uma carga de 10.000
  registros não representam produção; os tempos de `explain` variam por máquina.
- **Dependência de serviços:** o workflow depende de MongoDB, n8n e do provedor
  de LLM; falhas externas precisam de tratamento e auditoria.
- **RPA ausente:** a automação do sistema real não foi entregue e continua sendo
  o maior item de trabalho futuro. A seção 7 explica por que ela não entrou nesta
  versão e o que seria necessário antes de tentar.

## 7. Trabalhos futuros: RPA (não implementado)

Foi sugerido usar RPA para "dissecar" o sistema real e montar uma cópia de teste,
de modo que as validações rodassem contra um fluxo mais próximo do real. A ideia
foi **deliberadamente não executada** nesta entrega, por quatro motivos:

1. **Escopo:** a entrega foi definida com dados fictícios e sem acesso ao sistema
   real; incluir RPA exigiria refazer o escopo e a validação.
2. **Autorização:** automatizar um sistema de terceiros sem autorização escrita
   pode violar termos de uso, direitos autorais e a LGPD. "Testar na produção",
   mesmo entre aspas, pode gerar efeitos reais.
3. **Dados de saúde:** uma cópia do sistema real aumentaria o risco de expor
   dados de pacientes; o protótipo atual não corre esse risco.
4. **Evidência:** não haveria tempo de implementar, testar e documentar o RPA com
   o mesmo rigor dos outros itens; um RPA frágil seria pior do que a ausência
   declarada.

O que ficou pronto é apenas o **contrato de integração**, em
`scripts/rpa/README.md` e `scripts/rpa/contrato.py`:

- o adaptador recebe `perfil`, `cidade`, `status` e `medicamento`;
- devolve os mesmos campos da consulta atual (`permitido`, `total`, `registros`,
  `motivo`), para que o restante do fluxo não mude;
- há um adaptador **mock** que devolve dados fictícios e não acessa rede nem
  navegador.

Para uma fase futura, os pré-requisitos são: autorização formal do responsável
pelo sistema, ambiente de homologação, contas de teste, limite de requisições,
auditoria de permitidos e negados e revisão de LGPD. O RPA **nunca** deve rodar
contra a produção com dados reais, e nenhuma credencial deve ficar no código.

## 8. Contribuição individual

Preencha de 3 a 5 linhas por integrante, descrevendo o que cada um fez:

```text
Caio Victor:
_______________________________________________________________
_______________________________________________________________
_______________________________________________________________

Diogenes:
_______________________________________________________________
_______________________________________________________________
_______________________________________________________________

Kleber Lucas:
_______________________________________________________________
_______________________________________________________________
_______________________________________________________________

Carlos Henrique:
_______________________________________________________________
_______________________________________________________________
_______________________________________________________________
```

## 9. Evidências

- `docs/evidencias/integracao.txt` — 5 testes de integração `OK`.
- `docs/evidencias/consulta_cidade_status_vigencia.txt` — `explain` antes/depois.
- `docs/evidencias/consulta_medicamento_status.txt` — `explain` antes/depois.
- `docs/casos_de_teste.md` — C1–C5 executados; C6–C8 `PENDENTE`.
- `docs/checklist_entrega.md` — status item a item.
- `finetuning/resultados.md` — `PENDENTE` até a execução no Colab.
