/** Extrai rotas e endpoints dos bundles para calibração (análise estática). */
import { readFileSync } from 'node:fs';

const file = process.argv[2] ?? 'recon/js/app.dbea79aabac70650bd7f.js';
const src = readFileSync(file, 'utf8');

const uniq = (arr) => [...new Set(arr)];
const matchAll = (re) => [...src.matchAll(re)].map((m) => m[1]).filter(Boolean);

console.log('--- rotas SPA (path:"...") ---');
console.log(uniq(matchAll(/path:"([^"]{1,120})"/g)).slice(0, 120).join('\n'));

console.log('\n--- endpoints API ---');
console.log(uniq(matchAll(/"(\/?api\/[A-Za-z0-9_\-/${}.]+)"/g)).slice(0, 120).join('\n'));

console.log('\n--- termos de domínio (contexto) ---');
for (const term of ['medicamento', 'principio', 'lme', 'ime', 'ceaf', 'cid', 'dispensa', 'pcdt']) {
  const count = (src.match(new RegExp(term, 'gi')) || []).length;
  console.log(`${term}: ${count}`);
}

console.log('\n--- possíveis bases de API ---');
console.log(uniq(matchAll(/(https?:\/\/[^"'\s]{6,120})/g)).slice(0, 40).join('\n'));
