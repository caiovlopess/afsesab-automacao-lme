/**
 * Sidebar Renderer — interação com o copiloto.
 * Toda comunicação com o backend passa pela API exposta no preload (Main),
 * nunca por fetch direto (o token local fica confinado ao Main).
 */

// Tipos inferidos da API global (evita `exports` no JS do navegador).
type AnalysisResponse = Awaited<ReturnType<Window['afDesktop']['analyzeContext']>>;
type InspectionResult = Awaited<ReturnType<Window['afDesktop']['inspectStructure']>>;
type ValidationResponse = Awaited<ReturnType<Window['afDesktop']['validatePrescription']>>;
type SanitizedContext = Parameters<Window['afDesktop']['analyzeContext']>[0];

function el<T extends HTMLElement>(id: string): T {
  const node = document.getElementById(id);
  if (!node) throw new Error(`Elemento #${id} não encontrado.`);
  return node as T;
}

const contextView = el<HTMLDivElement>('context-view');
const ctxStatus = el<HTMLSpanElement>('ctx-status');
const btnAnalyze = el<HTMLButtonElement>('btn-analyze');
const btnInspect = el<HTMLButtonElement>('btn-inspect');
const analysisResult = el<HTMLDivElement>('analysis-result');
const rxFile = el<HTMLInputElement>('rx-file');
const rxFileName = el<HTMLSpanElement>('rx-file-name');
const btnValidate = el<HTMLButtonElement>('btn-validate');
const validationResult = el<HTMLDivElement>('validation-result');
const logBox = el<HTMLDivElement>('log');
const btnInsights = el<HTMLButtonElement>('btn-insights');
const btnAudit = el<HTMLButtonElement>('btn-audit');
const insightsResult = el<HTMLDivElement>('insights-result');
let insightsFoco = 'geral';
const askInput = el<HTMLInputElement>('ask-input');
const btnAsk = el<HTMLButtonElement>('btn-ask');
const askResult = el<HTMLDivElement>('ask-result');

let currentContext: SanitizedContext | null = null;
let rxBytes: ArrayBuffer | null = null;
let rxName = '';

function log(message: string): void {
  const time = new Date().toLocaleTimeString('pt-BR');
  logBox.textContent = `[${time}] ${message}\n${logBox.textContent}`.slice(0, 4000);
}

function renderLists(target: HTMLElement, sections: Array<{ title: string; items: string[] }>): void {
  target.replaceChildren();
  for (const section of sections) {
    if (!section.items.length) continue;
    const heading = document.createElement('h3');
    heading.textContent = section.title;
    target.appendChild(heading);
    const list = document.createElement('ul');
    const items = section.items.length ? section.items : ['Nada identificado.'];
    for (const item of items) {
      const li = document.createElement('li');
      li.textContent = item;
      list.appendChild(li);
    }
    target.appendChild(list);
  }
}

function renderMessage(target: HTMLElement, message: string): void {
  const p = document.createElement('div');
  p.textContent = message;
  target.replaceChildren(p);
}

/* ------------------------------------------------------------------ */

window.afDesktop.onContext((context) => {
  currentContext = context;
  contextView.textContent = JSON.stringify(context, null, 2);
  ctxStatus.textContent = `${context.drugs.length} fármaco(s) · ${context.cid10.length} CID · ${context.clinicalTerms.length} termo(s)`;
  ctxStatus.className = 'badge badge--ok';
  btnAnalyze.disabled = false;
  log('Contexto recebido e sanitizado.');
});

window.afDesktop.onStatus((message) => log(message));

btnAnalyze.addEventListener('click', async () => {
  if (!currentContext) return;
  btnAnalyze.disabled = true;
  renderMessage(analysisResult, 'Consultando protocolos indexados…');
  try {
    const result: AnalysisResponse = await window.afDesktop.analyzeContext(currentContext);
    renderLists(analysisResult, [
      { title: 'Critérios de inclusão', items: result.inclusionCriteria },
      { title: 'Exames obrigatórios (LME/IME)', items: result.requiredExams },
      { title: 'Alertas de dispensação', items: result.dispensingAlerts },
      { title: 'Fontes', items: result.sources },
      { title: 'Como fazer', items: result.passos },
      { title: 'Exemplo', items: [result.exemplo] },
    ]);
    log('Análise RAG concluída.');
  } catch (error) {
    renderMessage(analysisResult, `Erro: ${(error as Error).message}`);
    log(`Falha na análise: ${(error as Error).message}`);
  } finally {
    btnAnalyze.disabled = false;
  }
});

btnAudit.addEventListener('click', async () => {
  btnAudit.disabled = true;
  renderMessage(insightsResult, 'Procurando problemas na base…');
  try {
    const result = await window.afDesktop.auditBase();
    renderLists(insightsResult, result.achados.map((item) => ({
      title: `[${item.severidade}] ${item.titulo}`,
      items: [item.detalhe],
    })));
    log(`Auditoria: ${result.total} achado(s).`);
  } catch (error) {
    renderMessage(insightsResult, `Erro: ${(error as Error).message}`);
  } finally {
    btnAudit.disabled = false;
  }
});

btnAsk.addEventListener('click', async () => {
  const pergunta = askInput.value.trim();
  if (!pergunta) return;
  btnAsk.disabled = true;
  renderMessage(askResult, 'Consultando a base…');
  try {
    const result = await window.afDesktop.askAdmin(pergunta);
    renderLists(askResult, [
      { title: result.answer, items: [] },
      { title: `Resultados · ${result.intent}`, items: [] },
    ]);
    const table = document.createElement('div');
    const head = document.createElement('div');
    head.className = 'ask-head';
    head.textContent = result.columns.join(' | ');
    table.appendChild(head);
    for (const row of result.rows.slice(0, 30)) {
      const line = document.createElement('div');
      line.className = 'ask-row';
      line.textContent = row.join(' | ');
      table.appendChild(line);
    }
    askResult.appendChild(table);
  } catch (error) {
    renderMessage(askResult, `Erro: ${(error as Error).message}`);
  } finally {
    btnAsk.disabled = false;
  }
});

document.querySelectorAll<HTMLButtonElement>('.chip').forEach((chip) => {
  chip.addEventListener('click', () => {
    document.querySelectorAll('.chip').forEach((c) => c.classList.remove('chip--active'));
    chip.classList.add('chip--active');
    insightsFoco = chip.dataset.foco ?? 'geral';
  });
});

btnInsights.addEventListener('click', async () => {
  btnInsights.disabled = true;
  renderMessage(insightsResult, 'Analisando indicadores da base…');
  try {
    const result = await window.afDesktop.getAdminInsights(insightsFoco);
    renderLists(insightsResult, [
      { title: `Resumo · ${result.periodo} · ${result.model}`, items: [result.resumo] },
      { title: 'Insights', items: result.insights },
      { title: 'Alertas', items: result.alertas.length ? result.alertas : ['Nenhum alerta crítico.'] },
      { title: 'Ações recomendadas', items: result.acoes },
    ]);
    log(`Insights gerados (${result.model}).`);
  } catch (error) {
    renderMessage(insightsResult, `Erro: ${(error as Error).message}`);
  } finally {
    btnInsights.disabled = false;
  }
});

btnInspect.addEventListener('click', async () => {
  btnInspect.disabled = true;
  renderMessage(analysisResult, 'Mapeando estrutura da tela…');
  try {
    const result: InspectionResult = await window.afDesktop.inspectStructure();
    renderMessage(analysisResult, JSON.stringify(result, null, 2));
    log(`Inspeção concluída: ${result.cssSelectors.length} elementos mapeados.`);
  } catch (error) {
    renderMessage(analysisResult, `Erro: ${(error as Error).message}`);
  } finally {
    btnInspect.disabled = false;
  }
});

rxFile.addEventListener('change', () => {
  const file = rxFile.files?.[0];
  if (!file) return;
  rxName = file.name;
  rxFileName.textContent = `${file.name} (${(file.size / 1024 / 1024).toFixed(2)} MB)`;
  file.arrayBuffer().then((buffer) => {
    rxBytes = buffer;
    btnValidate.disabled = false;
  });
});

btnValidate.addEventListener('click', async () => {
  if (!rxBytes) return;
  btnValidate.disabled = true;
  renderMessage(validationResult, 'Extraindo dados da receita/LME…');
  try {
    const result: ValidationResponse = await window.afDesktop.validatePrescription(
      rxName,
      rxBytes,
      currentContext,
    );
    const extracted = result.extracted;
    renderLists(validationResult, [
      {
        title: 'Dados extraídos',
        items: [
          `Princípio ativo: ${extracted.activeIngredient || '—'}`,
          `Concentração: ${extracted.concentration || '—'}`,
          `Posologia: ${extracted.posology || '—'}`,
          `CID: ${extracted.cid || '—'}`,
          `Emissão: ${extracted.issueDate || '—'}`,
        ],
      },
      { title: `Inconsistências (${result.status})`, items: result.inconsistencies },
    ]);
    log(`Validação concluída: ${result.status}.`);
  } catch (error) {
    renderMessage(validationResult, `Erro: ${(error as Error).message}`);
    log(`Falha na validação: ${(error as Error).message}`);
  } finally {
    btnValidate.disabled = false;
  }
});
