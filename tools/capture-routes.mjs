/**
 * Mapeia rotas específicas do AFSESAB para calibração de seletores.
 * Conecta no Chrome autenticado via CDP. NÃO captura values/texto de pacientes.
 *
 * Uso: node capture-routes.mjs
 */
import { chromium } from 'playwright';
import { mkdirSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';

const ROUTES = [
  'lista-medicamento',
  'lme',
  'cid',
  'consulta-atendimento',
  'parametros-pcdt-list',
];

const outDir = resolve('recon/routes');
mkdirSync(outDir, { recursive: true });

const browser = await chromium.connectOverCDP('http://127.0.0.1:9222');
try {
  const page = browser.contexts().flatMap((c) => c.pages()).find((p) => p.url().includes('afsesab'));
  if (!page) throw new Error('Aba do AFSESAB não encontrada no Chrome.');

  for (const route of ROUTES) {
    await page.goto(`https://afsesab.sesab.ba.gov.br/#/app/${route}`, {
      waitUntil: 'domcontentloaded',
    });
    await page.waitForTimeout(1500); // aguarda renderização Vuetify

    const map = await page.evaluate(() => {
      function cssSelector(el) {
        if (el.id) return `#${CSS.escape(el.id)}`;
        const parts = [];
        let node = el;
        while (node && node !== document.documentElement) {
          let part = node.tagName.toLowerCase();
          const classes = (node.className || '').toString().trim().split(/\s+/).slice(0, 2);
          if (classes.length) part += `.${classes.map((c) => CSS.escape(c)).join('.')}`;
          const parent = node.parentElement;
          if (parent) {
            const sib = [...parent.children].filter((c) => c.tagName === node.tagName);
            if (sib.length > 1) part += `:nth-of-type(${sib.indexOf(node) + 1})`;
          }
          parts.unshift(part);
          node = parent;
        }
        return parts.join(' > ');
      }
      const nodes = [...document.querySelectorAll('input,select,textarea,button')].slice(0, 200);
      return {
        url: location.href,
        capturedAt: new Date().toISOString(),
        // value e textContent são OMITIDOS intencionalmente (LGPD).
        fields: nodes.map((el) => ({
          tag: el.tagName.toLowerCase(),
          type: el.getAttribute('type') || '',
          name: el.getAttribute('name') || '',
          id: el.id || '',
          placeholder: el.getAttribute('placeholder') || '',
          ariaLabel: el.getAttribute('aria-label') || '',
          className: (el.className || '').toString().slice(0, 160),
          selector: cssSelector(el),
        })),
      };
    });

    writeFileSync(resolve(outDir, `${route}.json`), JSON.stringify(map, null, 2), 'utf8');
    console.log(`${route}: ${map.fields.length} campos -> recon/routes/${route}.json`);
  }
} finally {
  await browser.close();
}
