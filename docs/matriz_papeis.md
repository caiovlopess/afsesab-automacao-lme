# Matriz de papéis e regras DENY

| Papel | Pode | Não pode | Ponto de enforcement |
|---|---|---|---|
| Administrador técnico | Gerir índices, disponibilidade, backups e contas técnicas | Consultar dados clínicos por padrão; usar conta compartilhada | Permissões MongoDB e auditoria; acesso excepcional aprovado |
| Profissional autorizado | Consultar dados mínimos dos municípios sob seu escopo | Consultar outro município, alterar permissões ou exportar sem autorização | Backend valida identidade, município e operação |
| Auditor | Consultar eventos de auditoria e métricas | Ler conteúdo clínico completo sem autorização específica | Coleção de auditoria separada e projeções limitadas |
| Agente de IA / LLM | Propor filtros a partir de pergunta; resumir resultados mínimos autorizados | Acessar credenciais, executar comandos livres, alterar dados ou ampliar escopo | Ferramentas allowlist + validação de esquema no backend |
| Processo RPA | Consultar telas autorizadas usando conta institucional restrita | Burlar autenticação, reutilizar sessão alheia ou extrair além do escopo | Conta dedicada, limites, logs e aprovação institucional |

## DENY explícito
- Negar usuário desconhecido ou sem autenticação.
- Negar cidade fora do escopo do profissional.
- Negar campos sensíveis sem necessidade/permissão.
- Negar filtros com operadores inesperados, `$where`, pipelines livres ou nomes de campos arbitrários.
- Negar operações de escrita para perfis de consulta.
- Negar exportação em massa sem aprovação e auditoria.
- Negar acesso da LLM a segredos, credenciais e ferramentas administrativas.

**Observação:** esta matriz é um rascunho acadêmico. Em produção, integrar com identidade institucional e permissões efetivas do MongoDB; não confiar apenas em papéis codificados no exemplo CLI.
