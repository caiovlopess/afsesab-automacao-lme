# Matriz de papéis e permissões

Todos os acessos usam apenas dados fictícios. As permissões são aplicadas por
roles do MongoDB (`createRole`), não pelos comandos SQL `GRANT`/`DENY`. Os
perfis de consulta recebem acesso somente às views por cidade, nunca à coleção
original `pacientes`.

## Perfis implementados

| Usuário de teste | Role | Pode | Não pode |
|---|---|---|---|
| `teste_farmaceutico_sai` | `farmaceutico_sai` | `find` em `pacientes_sai` | Ler as demais views, `pacientes` ou `audit_log`; escrever |
| `teste_auditor` | `auditor` | `find` nas quatro views por cidade e em `audit_log` | Ler `pacientes`; escrever |
| `teste_ia` | `ia_leitura` | `find` nas quatro views por cidade; `insert` em `audit_log` | Ler `audit_log`; ler `pacientes`; alterar dados existentes |
| `teste_workflow_audit` | `workflow_audit` | `insert` em `audit_log` | Ler `audit_log`; acessar views ou `pacientes` |
| `root` (Docker) | `root` | Administração local do MongoDB | Ser usado em consultas de rotina |

## Views por cidade

`scripts/seguranca.js` cria as views abaixo sobre `pacientes`:

| View | Cidade |
|---|---|
| `pacientes_sai` | Santo Antônio de Jesus |
| `pacientes_amargosa` | Amargosa |
| `pacientes_nazare` | Nazaré |
| `pacientes_cruz` | Cruz das Almas |

As views omitem `_id`, mantêm `nome`, `cidade` e `lme` e mascaram o CPF no
formato `***.***.***-NN`. A coleção original continua guardando o CPF completo,
por isso apenas o administrador local deve acessá-la.

## Negações verificadas

`scripts/testes_seguranca.py` confirma automaticamente:

- leitura da coleção original `pacientes` por todos os perfis de teste;
- leitura de views fora do escopo do farmacêutico;
- leitura de `audit_log` pelos perfis que só podem inserir (`ia_leitura` e
  `workflow_audit`);
- leitura de qualquer view ou de `pacientes` pelo perfil de workflow;
- formato do CPF mascarado nas views permitidas.

As permissões de escrita não são concedidas aos perfis de consulta; por isso, a
tentativa de escrita é negada pela ausência da ação no role.

## Limitações

- As senhas ficam no `.env` local, ignorado pelo Git. O `.env.example` contém
  apenas placeholders.
- O MongoDB do protótipo escuta em `localhost:27018` e não deve ser exposto.
- O escopo por cidade é garantido pela view e pelo role do MongoDB. Se uma API
  for adicionada, ela deve repetir a validação de identidade e cidade.
- As instruções do prompt da LLM não substituem as permissões do banco.
- Em produção, integrar com a identidade institucional e revisar retenção,
  auditoria e LGPD antes de qualquer uso com dados reais.
