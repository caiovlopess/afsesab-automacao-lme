# Workflow do n8n

Esta pasta guarda o workflow exportado da interface do n8n. O guia completo
para montar o fluxo está em [`../docs/guia_n8n.md`](../docs/guia_n8n.md).

## Como importar

1. No n8n, abra **Workflows**.
2. Clique nos três pontos no canto superior direito -> **Import from File**.
3. Selecione o `workflow_lme.json` desta pasta.
4. Abra o workflow importado e revise cada nó MongoDB:
   - `Buscar farmaceutico` -> credencial `MongoDB - teste_farmaceutico_sai`
   - `Buscar auditor` -> credencial `MongoDB - teste_auditor`
   - `Buscar IA` -> credencial `MongoDB - teste_ia`
   - `Auditar permitido` e `Auditar negado` -> credencial
     `MongoDB - workflow_audit`
5. Selecione a credencial do LLM no nó do modelo (ex.: `OpenAI - LME`).
6. Confirme que o caminho `/home/node/regras_lme/*.md` existe dentro do
   container:

   ```powershell
   docker compose exec n8n ls /home/node/regras_lme
   ```

7. Clique em **Save** e faça um teste com o webhook conforme o guia.

## Regras de segurança

- O JSON exportado **não deve conter** senhas, API keys, tokens ou cabeçalhos
  `Authorization`. Credenciais do n8n são armazenadas no banco do próprio n8n e
  aparecem no export apenas por referência (nome/id).
- Antes de aceitar o arquivo exportado, procure por `password`, `apiKey`,
  `api_key`, `Authorization`, `Bearer` e `sk-`.
- O arquivo `.env` não é versionado. Mantenha as senhas apenas nele e nas
  credenciais do n8n.
- Se um segredo aparecer no JSON, remova o valor da credencial/nó, exporte de
  novo e não faça commit do arquivo antigo.

## Arquivo esperado

- `workflow_lme.json` — exportado pelo usuário após montar o fluxo; ainda não
  existe nesta pasta.

> PENDENTE: o usuário deve montar o workflow seguindo `docs/guia_n8n.md`,
> exportar o JSON para esta pasta e avisar para a conferência de segredos.
