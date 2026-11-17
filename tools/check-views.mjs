/** Valida que as 47 telas do clone têm títulos/colunas distintos. */
import { readFileSync } from 'node:fs';

const token = readFileSync('../ai-backend/runtime/auth_token', 'utf8').trim();
const source = readFileSync('../desktop-client/src/clone/app.js', 'utf8');
const keys = [...source.matchAll(/\['([a-z_0-9]+)',\s*'/g)].map(m => m[1]);
console.log('views no menu:', keys.length);

const seen = new Map();
let distinct = 0;
for (const key of keys) {
  const r = await fetch(`http://127.0.0.1:8000/api/v1/fictional/view/${key}`, {
    headers: { 'X-Internal-Auth-Token': token },
  });
  if (!r.ok) { console.log('ERRO', key, r.status); continue; }
  const v = await r.json();
  const sig = v.title + '::' + v.columns.join('|');
  if (!seen.has(sig)) { seen.set(sig, []); distinct += 1; }
  seen.get(sig).push(key);
  console.log(`${key.padEnd(24)} -> ${v.title} (${v.columns.length} col, ${v.rows.length} linhas)`);
}
console.log(`\nAssinaturas distintas: ${distinct}/${keys.length}`);
for (const [sig, ks] of seen) if (ks.length > 1) console.log('REPETIDO:', sig, ks);
