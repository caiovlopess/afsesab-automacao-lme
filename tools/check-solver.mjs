import { readFileSync, writeFileSync } from 'node:fs';
const token = readFileSync('../ai-backend/runtime/auth_token', 'utf8').trim();
const base = 'http://127.0.0.1:8000/api/v1';
const H = { 'X-Internal-Auth-Token': token };
let session = '';

async function req(path, opts = {}) {
  const headers = { ...H, ...(opts.headers || {}) };
  const r = await fetch(base + path, { ...opts, headers });
  return [r.status, await r.json().catch(() => ({}))];
}

const [, login] = await req('/auth/login', {
  method: 'POST', headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ username: 'henriquecarvalho', password: '3246Hz!@#Hz' }),
});
session = login.session_token;
const SH = { ...H, 'X-Session-Token': session, 'Content-Type': 'application/json' };
console.log('login:', login.perfil, '| sessao:', session.slice(0, 8));

const [, before] = await req('/fictional/view/lme', { headers: H });
const target = before.rows.find(r => String(r[5]).toLowerCase() === 'pendente');
console.log('status antes (ID ' + target[0] + '):', target[5]);

const [st, changed] = await req(`/fictional/lmes/${target[0]}/status`, {
  method: 'POST', headers: SH,
  body: JSON.stringify({ status: 'autorizada', motivo: 'teste automatizado' }),
});
console.log('alterar status:', st, changed.status);

const [, after] = await req('/fictional/view/lme', { headers: H });
const updated = after.rows.find(r => Number(r[0]) === Number(target[0]));
console.log('status depois:', updated[5]);

const [, audit] = await req('/fictional/audit', { headers: SH });
console.log('auditoria:', audit[0]?.acao, '|', audit[0]?.detalhes);

const r = await fetch(base + '/fictional/audit/export?formato=csv', { headers: SH });
console.log('export auditoria:', r.status, (await r.arrayBuffer()).byteLength, 'bytes');

const [, alerts] = await req('/admin/audit', {
  method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}',
});
console.log('alertas:', alerts.total);

for (const q of ['Arlindo', 'CID E11']) {
  const [, res] = await req('/admin/ask', {
    method: 'POST', headers: SH, body: JSON.stringify({ pergunta: q }),
  });
  console.log(`busca "${q}":`, res.intent, '| linhas:', res.rows?.length);
}

let t = Date.now();
await req('/admin/insights', { method: 'POST', headers: SH, body: '{"foco":"geral"}' });
console.log('insights 1:', Date.now() - t, 'ms');
t = Date.now();
await req('/admin/insights', { method: 'POST', headers: SH, body: '{"foco":"geral"}' });
console.log('insights 2 (cache):', Date.now() - t, 'ms');

const [, rag] = await req('/analyze-context', {
  method: 'POST', headers: SH,
  body: JSON.stringify({
    drugs: ['metformina'], dosages: ['850 mg'], cid10: ['E11'], clinicalTerms: ['diabetes'],
    safeText: 'metformina 850 mg E11 diabetes', capturedAt: new Date().toISOString(), source: 'afsesab',
  }),
});
console.log('RAG:', rag.sources?.[0], '| passos:', rag.passos?.length);
