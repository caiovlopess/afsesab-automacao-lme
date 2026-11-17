# desktop-client (Electron + TypeScript)

Wrapper desktop que exibe o AFSESAB em 70% da tela (BrowserView) e o copiloto em 30% (Sidebar).

## Segurança

| Control | Valor |
| --- | --- |
| `contextIsolation` | `true` (Main, Sidebar e BrowserView) |
| `nodeIntegration` | `false` |
| `sandbox` | `true` |
| Origem permitida | apenas `https://afsesab.sesab.ba.gov.br` |
| Protocolo da Sidebar | `af://af-desktop` (standard + secure, CORS restrito no backend) |
| Token local | lido de `../ai-backend/runtime/auth_token`, nunca no código |
| Sanitização LGPD | no **Main**, antes de qualquer `fetch` |

O REA (`src/main/rea/webview-preload.ts`) é passivo: usa `MutationObserver`,
`selectionchange`, `input` e `change` sem modificar o DOM do portal. O modo inspeção
usa `executeJavaScript` para ler seletores CSS/XPath (finalidade acadêmica/debug).

## Rodar

```bash
npm install
npm run dev        # compila (tsc + copy-assets) e abre o Electron
```

Variáveis de ambiente opcionais:

- `AF_BACKEND_URL` — padrão `http://127.0.0.1:8000`
- `AF_INTERNAL_TOKEN_PATH` — caminho alternativo para o token local

> **Importante:** inicie o `ai-backend` antes do cliente para que o arquivo de token exista.

## Calibração dos seletores após login

1. Faça login no AFSESAB no painel esquerdo.
2. No painel direito, clique em **Inspecionar estrutura da tela**.
3. O JSON com `cssSelectors`, `xpath` e `frames` aparece na área de análise.
4. Ajuste `PII_PATTERNS`/`CLINICAL_LEXICON` e os seletores em
   `src/main/rea/webview-preload.ts` conforme os campos reais do portal.
5. Alternativamente, use `../tools/playwright-capture.mjs` para gerar um dump
   completo conectando-se ao Chrome já autenticado via CDP.

### Seletores já calibrados via source map

O portal expõe `.js.map`; o código-fonte original foi extraído para
`../tools/recon/src/` (1356 arquivos, 320 `.vue`). Os `v-model`s reais da tela
`ListaMedicamentoList` estão em `src/main/rea/selectors.ts`:

| Campo | `v-model` |
| --- | --- |
| Lista | `queryFilter.nome` |
| Código Simpas | `queryFilter.codigo_simpas` |
| Medicamento | `queryFilter.procedimento_id` / `searchProcedimento` |
| Programa | `queryFilter.programa_saude_id` |

Campos LGPD da tela LME (`CPF`, `CNS`, `Nome do Paciente`, `Prontuário`,
`APAC`, `CNES`) são **bloqueados na origem** — o REA nem lê o `.value`.
