# Recon do AFSESAB — 2026-11-16

Material obtido do Chrome autenticado (CDP `127.0.0.1:9222`) para calibração do AF Copilot.
Uso exclusivo de engenharia reversa local. **Não redistribuir.**

## Artefatos

| Pasta/arquivo | Conteúdo |
| --- | --- |
| `dom-map.json` | 63 elementos do dashboard (CSS/XPath, iframes, bundles) |
| `routes/*.json` | 5 telas mapeadas (campos, sem `value`/texto de paciente) |
| `js/app.*.js`, `js/vendor.*.js`, `js/manifest.*.js` | bundles minificados (2,7 MB / 3,8 MB / <1 KB) |
| `js/*.js.map` | **source maps com 1359 módulos** (app 21 MB, vendor 15,8 MB) |
| `css/app.*.css` | CSS da SPA (303 KB) |
| `src/` | **1356 arquivos extraídos** (320 `.vue`), incluindo `src/`, `i18n/`, `router/`, `store/`, `interceptors/`, `plugins/` |

## Tecnologia identificada

- Vue 2 + Vuetify 1.x + Vuex + vue-router (hash mode `#/app/...`), webpack 3.
- BaseService (`vue-prodeb`) com API em `/api/v1/...`.
- Filtros sem `name`/`id`: identificação por `label`/`placeholder` (i18n `pt-BR`).

## Rotas principais

`#/app/dashboard`, `#/app/lista-medicamento`, `#/app/lme`, `#/app/cid`,
`#/app/parametros-pcdt-list`, `#/app/consulta-atendimento`.

## Campos calibrados

**ListaMedicamentoList** (`v-model` reais, via source map):
- `queryFilter.nome` — label `Lista`
- `queryFilter.codigo_simpas` — `Código Simpas`
- `queryFilter.procedimento_id` / `searchProcedimento` — `Medicamento/Descrição Resumida Simpas` (v-autocomplete)
- `queryFilter.programa_saude_id` — `Programa`

**Endpoints:** `GET /api/v1/lista-medicamento/get-lista-medicamento`,
`GET /api/v1/lista-medicamento/get-medicamentos-by-lista`,
`GET /api/v1/comunicados/carrossel`, `GET /api/v1/lmes/get-qtd-aguardando-avaliacao`.

## LGPD — campos bloqueados no REA

Confirmados na tela LME: `CPF`, `CNS`, `Nome do Paciente`, `Prontuário`, `APAC`, `CNES`.
O preload do Electron **não lê `.value`** desses campos (`PII_FIELD_RE` em
`desktop-client/src/main/rea/webview-preload.ts`).
