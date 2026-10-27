# AFSESAB — Automação Inteligente de Consultas de LME

**Grupo:** 
**Integrantes:**
- Caio Victor 
- Diogenes 
- Kleber Lucas 
- Carlos Henrique 

## Objetivo
Prototipar uma ferramenta que combine Python, MongoDB, LLM e RPA para apoiar consultas autorizadas de registros de LME por município, medicamento, vigência e status. A entrega usa **somente dados sintéticos**. A integração com o AFSESAB real depende de autorização institucional e validação técnica; até lá, o RPA é simulado.

## Arquitetura
Terminal/CLI → LLM (interpretação de intenção) → backend Python (validação e autorização) → MongoDB e módulo RPA autorizado/simulado → validação, auditoria e resultado.
RAG é opcional para recuperar documentação operacional aprovada. n8n é opcional para orquestração, não obrigatório no MVP.

## Requisitos
- Python 3.10+
- MongoDB local ou instância de desenvolvimento
- Pacotes: `pymongo`, `faker`

## Instalação
```bash
python -m venv .venv
# Linux/macOS
source .venv/bin/activate
# Windows
.venv\\Scripts\\activate
pip install -r requirements.txt
```

Defina a variável de ambiente `MONGODB_URI` com a URI do seu ambiente de teste. Não coloque senhas nem chaves no repositório.

## Gerar e carregar dados fictícios
```bash
python src/seed_mongodb.py
```
O script cria as coleções `cidades`, `pacientes`, `consultas_lme` e `auditoria`, insere registros sintéticos e cria índices de consulta.

## Executar demonstração CLI
```bash
python src/app_cli.py
```
A demonstração usa filtros validados localmente e não chama uma LLM externa nem acessa o AFSESAB. A integração real com uma LLM deve ser implementada por um adaptador que retorne apenas JSON dentro de um esquema permitido. Nunca envie dados identificáveis ou clínicos a um provedor sem aprovação formal.

## Segurança e privacidade
- Dados totalmente sintéticos; não carregar prontuários ou dados reais.
- Autorização aplicada no backend, não apenas no prompt da LLM.
- Privilégio mínimo para contas do MongoDB.
- Não registrar documentos, nomes ou dados clínicos nos logs.
- Segredos em variáveis de ambiente/gerenciador de segredos, nunca em código.
- Revisar LGPD, autorização institucional, retenção e escopo de acesso antes de qualquer uso real.

## Testes e limitações
A pasta `tests/` contém cenários manuais de prompt injection e escalonamento de privilégio. O protótipo de CLI demonstra consultas por município/status/medicamento. Não constitui integração pronta com AFSESAB, nem comprova mitigação até os testes serem executados e seus resultados registrados.

## Entregáveis
- `docs/arquitetura.mmd`: diagrama Mermaid.
- `docs/matriz_papeis.md`: matriz de papéis e regras DENY.
- `docs/plano_testes.md`: ameaças, testes e critérios.
- `src/seed_mongodb.py`: carga sintética e índices.
- `src/app_cli.py`: consulta CLI de demonstração.
