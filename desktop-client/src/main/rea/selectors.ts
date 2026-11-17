/**
 * Seletores calibrados do AFSESAB (Vuetify 1.x).
 *
 * Fonte: engenharia reversa via CDP/Playwright em 2026-11-16.
 * Dumps: tools/recon/dom-map.json e tools/recon/routes/*.json
 *
 * O portal não usa `name`/`id` estáveis nos filtros — a identificação é feita
 * por `placeholder`/`aria-label`. Por isso o REA captura `label` e `value`.
 */

export const PORTAL_BASE = 'https://afsesab.sesab.ba.gov.br/#/app/';

export const PORTAL_ROUTES = {
  dashboard: 'dashboard',
  /** Busca de medicamentos (CEAF). */
  medicamentos: 'lista-medicamento',
  /** LME — contém CPF/CNS/Nome do Paciente/Prontuário (bloqueados no REA). */
  lme: 'lme',
  cid: 'cid',
  pcdt: 'parametros-pcdt-list',
  atendimento: 'consulta-atendimento',
} as const;

/** Rótulos reais encontrados nos filtros — usados para calibração/depuração. */
export const SEARCH_FIELD_HINTS = {
  medicamentos: ['Lista', 'Código Simpas', 'Medicamento/Descrição Resumida Simpas', 'Programa'],
  lme: ['Status', 'CID', 'Medicamentos', 'Paciente com LME de:', 'Estabelecimento Avaliador', 'Avaliador'],
  cid: ['Código ou Descrição', 'Status'],
  pcdt: ['Patologia', 'CID', 'Medicamento', 'Critérios Obrigatório', 'Soma dos Critérios:*'],
} as const;

/**
 * `v-model`s reais da tela ListaMedicamentoList (extraídos do source map).
 * Úteis para casar valores capturados com o que o usuárioDigitou no portal.
 */
export const QUERY_FIELD_MODELS = {
  lista: 'queryFilter.nome',
  codigoSimpas: 'queryFilter.codigo_simpas',
  medicamento: 'queryFilter.procedimento_id',
  medicamentoBusca: 'searchProcedimento',
  programa: 'queryFilter.programa_saude_id',
} as const;

/** Endpoints confirmados no código-fonte (BaseService + rota). */
export const API_ENDPOINTS = {
  listaMedicamentos: 'GET /api/v1/lista-medicamento/get-lista-medicamento',
  medicamentosPorLista: 'GET /api/v1/lista-medicamento/get-medicamentos-by-lista',
  comunicadosCarrossel: 'GET /api/v1/comunicados/carrossel',
  lmesAguardando: 'GET /api/v1/lmes/get-qtd-aguardando-avaliacao',
} as const;

/** Campos proibidos (LGPD) confirmados na tela LME. */
export const BLOCKED_FIELD_LABELS = [
  'CPF', 'CNS', 'Nome do Paciente', 'Prontuário', 'APAC', 'CNES',
] as const;
