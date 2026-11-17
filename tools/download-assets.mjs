/** Baixa CSS e source maps referenciadas nos bundles. */
import { chromium } from 'playwright';
import { mkdirSync, writeFileSync, existsSync } from 'node:fs';
import { resolve, basename } from 'node:path';

mkdirSync(resolve('recon/js'), { recursive: true });
mkdirSync(resolve('recon/css'), { recursive: true });

const browser = await chromium.connectOverCDP('http://127.0.0.1:9222');
try {
  const page = browser.contexts().flatMap((c) => c.pages()).find((p) => p.url().includes('afsesab'));
  if (!page) throw new Error('Aba AFSESAB não encontrada');
  await page.reload({ waitUntil: 'networkidle' }).catch(() => {});

  const urls = await page.evaluate(() =>
    [...new Set(performance.getEntriesByType('resource').map((r) => r.name))]
  );

  const targets = [
    ...urls.filter((u) => u.startsWith('https://afsesab.sesab.ba.gov.br/static/js/') && u.endsWith('.js')),
    ...urls.filter((u) => u.startsWith('https://afsesab.sesab.ba.gov.br/static/css/') && u.endsWith('.css')),
  ];

  for (const url of targets) {
    const isMap = url.endsWith('.js');
    const list = isMap ? [url, `${url}.map`] : [url];
    for (const target of list) {
      const response = await page.request.get(target);
      if (!response.ok()) {
        console.log(`INDISPONIVEL ${response.status()} ${target}`);
        continue;
      }
      const name = basename(new URL(target).pathname).replace(/[^\w.-]/g, '_');
      const dir = isMap ? 'js' : 'css';
      const out = resolve('recon', dir, name);
      if (existsSync(out)) continue;
      const body = await response.body();
      writeFileSync(out, body);
      console.log(`OK ${dir}/${name} (${(body.length / 1024).toFixed(0)} KB)`);
    }
  }
} finally {
  await browser.close();
}
