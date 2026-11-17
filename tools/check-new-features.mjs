import { readFileSync } from 'node:fs';
const token = readFileSync('../ai-backend/runtime/auth_token', 'utf8').trim();
const H = { 'X-Internal-Auth-Token': token, 'Content-Type': 'application/json' };
const base = 'http://127.0.0.1:8000/api/v1';

async function post(path, body) {
  const r = await fetch(base + path, { method: 'POST', headers: H, body: JSON.stringify(body) });
  return [r.status, await r.json()];
}
async function get(path) {
  const r = await fetch(base + path, { headers: H });
  return [r.status, await r.json()];
}

const views = ['rel_comprometimento', 'pedido', 'rel_autorizada_faturada', 'entrada', 'ajuste_vinculo', 'paciente_ext', 'paciente_insulina'];
for (const k of views) {
  const [, v] = await get('/fictional/view/' + k);
  console.log(`${k}: ${v.columns.join('|')} -> ${JSON.stringify(v.rows[0])}`);
}

console.log('\n--- perguntas ---');
for (const q of ['Qual o fornecedor de Salvador?', 'Liste as LMEs que não foram autorizadas ainda']) {
  const [status, r] = await post('/admin/ask', { pergunta: q });
  console.log(status, q, '=>', r.answer, '| linhas:', r.rows.length, '| colunas:', r.columns.join(','));
}

console.log('\n--- cadastro ---');
const [st, med] = await post('/fictional/medicamentos', {
  nome: 'Teste API', principio: 'Principio Teste', apresentacao: 'Comprimido 10 mg',
});
console.log(st, med);
const [, after] = await get('/fictional/view/medicamento');
console.log('medicamentos no catalogo:', after.rows.length, 'ultimo:', after.rows[0]);

console.log('\n--- RAG local (tempo) ---');
const t0 = Date.now();
const [, rag] = await post('/analyze-context', {
  drugs: ['metformina'], dosages: ['850 mg'], cid10: ['E11'], clinicalTerms: ['diabetes'],
  safeText: 'metformina 850 mg E11 diabetes', capturedAt: new Date().toISOString(), source: 'afsesab',
});
console.log('ms:', Date.now() - t0, '| fonte:', rag.sources[0], '| passos:', rag.passos.length, '| exemplo:', rag.exemplo.slice(0, 60));
