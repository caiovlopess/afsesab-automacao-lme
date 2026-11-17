/** Lista TODOS os recursos carregados pela SPA e verifica source maps. */
import { chromium } from 'playwright';
import { readFileSync, readdirSync } from 'node:fs';
import { resolve } from 'node:path';

const browser = await chromium.connectOverCDP('http://127.0.0.1:9222');
try {
  const page = browser.contexts().flatMap((c) => c.pages()).find((p) => p.url().includes('afsesab'));
  if (!page) throw new Error('Aba AFSESAB não encontrada');
  await page.reload({ waitUntil: 'networkidle' }).catch(() => {});

  const resources = await page.evaluate(() =>
    [...new Set(performance.getEntriesByType('resource').map((r) => r.name))].sort()
  );

  const byExt = {};
  for (const url of resources) {
    const path = new URL(url).pathname;
    const ext = (path.split('.').pop() || '(sem extensão)').split('?')[0];
    byExt[ext] = (byExt[ext] || 0) + 1;
  }
  console.log('--- recursos por extensão ---');
  console.log(byExt);
  console.log('\n--- CSS / map / fontes / imagens ---');
  console.log(resources.filter((u) => /\.(css|map|woff2?|ttf|eot|svg|png|jpg)(\?|$)/i.test(u)).join('\n'));
  console.log('\n--- todos os URLs ---');
  console.log(resources.join('\n'));
} finally {
  await browser.close();
}

console.log('\n--- sourceMappingURL nos bundles ---');
for (const f of readdirSync('recon/js')) {
  const src = readFileSync(resolve('recon/js', f), 'utf8');
  const match = src.match(/\/\/# sourceMappingURL=.*$/m);
  console.log(`${f}: ${match ? match[0] : 'nenhum'}`);
}
