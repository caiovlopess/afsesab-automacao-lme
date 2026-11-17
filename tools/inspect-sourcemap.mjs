import { readFileSync } from 'node:fs';

const file = process.argv[2] ?? 'recon/js/app.dbea79aabac70650bd7f.js.map';
const map = JSON.parse(readFileSync(file, 'utf8'));
console.log('version:', map.version);
console.log('sources:', map.sources.length);
console.log('sourcesContent:', map.sourcesContent?.length ?? 0);
console.log('\n--- primeiros 120 sources ---');
console.log(map.sources.slice(0, 120).join('\n'));
