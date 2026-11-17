import { readFileSync } from 'node:fs';
const token = readFileSync('../ai-backend/runtime/auth_token', 'utf8').trim();
const r = await fetch('http://127.0.0.1:8000/api/v1/admin/ask', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json', 'X-Internal-Auth-Token': token },
  body: JSON.stringify({ pergunta: 'Liste as LMEs que não foram autorizadas ainda' }),
});
const data = await r.json();
console.log(data.answer);
for (const row of data.rows.slice(0, 3)) console.log(row[0], '|', row[1], '|', row[2]);
