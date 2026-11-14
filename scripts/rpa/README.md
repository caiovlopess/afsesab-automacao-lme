# RPA — contrato para uma fase futura (não implementado)

**Estado:** apenas contrato e stub. Nada aqui acessa o sistema real, a rede ou
dados de pacientes. O RPA com Playwright continua **fora do escopo** desta
entrega.

## Por que não agora

A sugestão de usar RPA para "dissecar" o sistema real e montar uma cópia de
teste foi considerada e **não executada** nesta entrega:

1. **Escopo:** a entrega usa somente dados fictícios e não acessa o AFSESAB real.
2. **Autorização:** automatizar um sistema de terceiros sem autorização escrita
   pode violar termos de uso, direitos autorais e a LGPD.
3. **Dados de saúde:** uma cópia do sistema real aumentaria o risco de expor
   dados de pacientes.
4. **Evidência:** sem tempo de implementar, testar e documentar, um RPA frágil
   seria pior do que a ausência declarada.

## O que existe

| Arquivo | Conteúdo |
|---|---|
| `contrato.py` | Interface `AdaptadorRPA`, formato de entrada/saída e um `AdaptadorMock` com dados fictícios. |
| `README.md` | Este documento: contrato, pré-requisitos e regras de segurança. |

O `AdaptadorMock` existe só para mostrar como um adaptador futuro se encaixa. Ele
não usa Playwright, não abre navegador e não faz requisições.

```powershell
python scripts/rpa/contrato.py
```

## Contrato

Entrada (`ConsultaRPA`):

| Campo | Obrigatório | Observação |
|---|---|---|
| `perfil` | sim | mesmo perfil usado na consulta atual |
| `cidade` | sim | cidade autorizada para o perfil |
| `status` | sim | `ATIVA`, `SUSPENSA` ou `CANCELADA` |
| `medicamento` | não | filtro opcional |

Saída (`ResultadoRPA`), no mesmo formato de `scripts/consulta_ia.py`:

| Campo | Tipo | Observação |
|---|---|---|
| `permitido` | `bool` | resultado da autorização |
| `total` | `int` | quantidade de registros retornados |
| `registros` | `list[dict]` | dados já mascarados; nunca CPF completo |
| `motivo` | `str` | explicação curta, inclusive para negação |

Um adaptador real deve devolver **exatamente** esses campos, para que o restante
do fluxo (auditoria, LLM e resposta) não precise mudar.

## Pré-requisitos para uma fase futura

- [ ] Autorização **escrita** do responsável pelo sistema.
- [ ] Ambiente de **homologação**, nunca produção.
- [ ] Contas de teste dedicadas, sem dados reais de pacientes.
- [ ] Limite de requisições e tratamento de erro/timeout.
- [ ] Registro em `audit_log` para tentativas permitidas e negadas.
- [ ] Revisão de LGPD, retenção e anonimização.
- [ ] Credenciais fora do código (`.env` local ou cofre), nunca no repositório.
- [ ] Testes com dados fictícios antes de qualquer execução real.

## Regras de segurança

- **Nunca** rodar contra produção com dados reais.
- **Nunca** gravar credenciais, cookies ou tokens no repositório.
- **Nunca** contornar CAPTCHA, autenticação ou limite de acesso.
- **Nunca** copiar a base real para o ambiente de teste.
- A autorização continua sendo do MongoDB; o RPA não substitui roles nem views.
- Se qualquer pré-requisito faltar, o adaptador deve recusar a execução.

## Não objetivos

- Implementar Playwright ou qualquer automação de navegador.
- Reproduzir o sistema real.
- Servir de prova de que o fluxo real funciona.
