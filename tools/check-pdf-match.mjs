import { readFileSync } from 'node:fs';
const token = readFileSync('../ai-backend/runtime/auth_token', 'utf8').trim();
const H = { 'X-Internal-Auth-Token': token };
const base = 'http://127.0.0.1:8000/api/v1';

const view = await (await fetch(base + '/fictional/view/lme', { headers: H })).json();
for (const id of [1, 22, 26, 50, 77]) {
  const row = view.rows.find(r => Number(r[0]) === id);
  const pdf = await (await fetch(`${base}/fictional/lmes/${id}/pdf`, { headers: H })).arrayBuffer();
  const out = `C:/Users/offsechen1/AppData/Local/Temp/match-${id}.pdf`;
  const { writeFileSync } = await import('node:fs');
  writeFileSync(out, Buffer.from(pdf));
  console.log(`${id} | tabela: ${row[2]} | ${row[1]} | PDF salvo: ${out}`);
}
