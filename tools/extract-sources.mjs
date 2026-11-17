/**
 * Extrai os sourcesContent do source map para recon/src/.
 * Reconstrói a árvore original de componentes Vue do AFSESAB.
 *
 * AVISO: conteúdo obtido somente para engenharia reversa/calibração local.
 * Não redistribuir. Nenhum dado de paciente é extraído aqui.
 */
import { readFileSync, mkdirSync, writeFileSync } from 'node:fs';
import { resolve, dirname, join } from 'node:path';

const mapFile = process.argv[2] ?? 'recon/js/app.dbea79aabac70650bd7f.js.map';
const map = JSON.parse(readFileSync(mapFile, 'utf8'));
const outRoot = resolve('recon/src');

function safePath(source) {
  let p = source.replace(/^webpack:\/\/\/\.?\/?/, '').replace(/^webpack:\/\/\//, '');
  p = p.split('?')[0];
  p = p.replace(/^[a-zA-Z]:/, '').replace(/^(\.\.\/)+/, '');
  const parts = p.split('/').filter((s) => s && s !== '.' && s !== '..');
  if (parts[0] === 'static' && parts[1] === 'js') return null; // bundle raiz
  if (parts.includes('node_modules')) return null; // dependências de terceiros
  // Sanitiza nomes de arquivos no Windows (alguns sources são padrões regex).
  const clean = parts.map((s) =>
    s.replace(/[<>:"/\\|?*]/g, '_').replace(/\s+\.*$/, '').slice(0, 180),
  ).filter(Boolean);
  if (!clean.length) return null;
  return join(outRoot, ...clean);
}

let written = 0;
const collisions = new Map();
for (let i = 0; i < map.sources.length; i += 1) {
  const target = safePath(map.sources[i]);
  if (!target) continue;
  let finalPath = target;
  if (collisions.has(target)) {
    const n = collisions.get(target) + 1;
    collisions.set(target, n);
    finalPath = `${target}.${n}`;
  } else {
    collisions.set(target, 0);
  }
  mkdirSync(dirname(finalPath), { recursive: true });
  writeFileSync(finalPath, map.sourcesContent[i] ?? '', 'utf8');
  written += 1;
}
console.log(`${written} arquivos extraidos para ${outRoot}`);
