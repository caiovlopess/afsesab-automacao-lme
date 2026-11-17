/**
 * REA / Playwright — mapeamento de estrutura do AFSESAB via CDP.
 *
 * Conecta a um Chrome JÁ AUTENTICADO (remote debugging) e gera:
 *   recon/dom-map.json  -> seletores CSS/XPath, iframes, bundles JS
 *   recon/js/*.js       -> cópia dos bundles para análise de calibração
 *
 * PRIVACIDADE: captura apenas estrutura (tags, ids, classes, names,
 * placeholders). NUNCA captura `value` de campos nem texto de pacientes.
 *
 * Uso:
 *   node playwright-capture.mjs [cdpUrl] [portalUrl]
 * Padrão: http://127.0.0.1:9222  e  https://afsesab.sesab.ba.gov.br/#/
 */

import { chromium } from 'playwright';
import { mkdirSync, writeFileSync } from 'node:fs';
import { resolve, basename } from 'node:path';

const cdpUrl = process.argv[2] ?? 'http://127.0.0.1:9222';
const portalUrl = process.argv[3] ?? 'https://afsesab.sesab.ba.gov.br/#/';
const outDir = resolve('recon');
const jsDir = resolve(outDir, 'js');

mkdirSync(jsDir, { recursive: true });

async function main() {
  const browser = await chromium.connectOverCDP(cdpUrl);
  try {
    const contexts = browser.contexts();
    let page = contexts.flatMap((c) => c.pages()).find((p) => p.url().includes('afsesab'));
    if (!page) {
      page = await contexts[0].newPage();
      await page.goto(portalUrl, { waitUntil: 'domcontentloaded' });
    } else {
      await page.bringToFront();
    }

    const domMap = await page.evaluate(() => {
      // Helpers precisam existir DENTRO do contexto do navegador.
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
            const siblings = [...parent.children].filter((c) => c.tagName === node.tagName);
            if (siblings.length > 1) part += `:nth-of-type(${siblings.indexOf(node) + 1})`;
          }
          parts.unshift(part);
          node = parent;
        }
        return parts.join(' > ');
      }

      function xpath(el) {
        const segments = [];
        let node = el;
        while (node && node.nodeType === 1) {
          let s = node.tagName.toLowerCase();
          const parent = node.parentElement;
          if (parent) {
            const same = [...parent.children].filter((c) => c.tagName === node.tagName);
            if (same.length > 1) s += `[${same.indexOf(node) + 1}]`;
          }
          segments.unshift(s);
          node = parent;
        }
        return '/' + segments.join('/');
      }

      const interactive = [...document.querySelectorAll(
        'input,select,textarea,button,a[href],[role=button],[role=combobox]'
      )].slice(0, 300);

      const assets = performance.getEntriesByType('resource')
        .map((r) => r.name)
        .filter((url) => /\.js(\?|$)/i.test(url));

      return {
        url: location.href,
        title: document.title,
        capturedAt: new Date().toISOString(),
        frames: [...document.querySelectorAll('iframe')].map((f) => f.src).filter(Boolean),
        elements: interactive.map((el) => ({
          tag: el.tagName.toLowerCase(),
          selector: cssSelector(el),
          xpath: xpath(el),
          name: el.getAttribute('name') || '',
          id: el.id || '',
          type: el.getAttribute('type') || el.getAttribute('role') || '',
          placeholder: el.getAttribute('placeholder') || '',
          ariaLabel: el.getAttribute('aria-label') || '',
          // value é intencionalmente OMITIDO (LGPD).
        })),
        jsAssets: [...new Set(assets)],
      };
    });

    writeFileSync(resolve(outDir, 'dom-map.json'), JSON.stringify(domMap, null, 2), 'utf8');

    let saved = 0;
    for (const url of domMap.jsAssets.slice(0, 40)) {
      try {
        const response = await page.request.get(url);
        if (!response.ok()) continue;
        const name = basename(new URL(url).pathname) || `bundle-${saved}.js`;
        writeFileSync(resolve(jsDir, name.replace(/[^\w.-]/g, '_')), await response.body());
        saved += 1;
      } catch {
        // asset indisponível — segue para o próximo
      }
    }

    console.log(`Mapa salvo: recon/dom-map.json (${domMap.elements.length} elementos)`);
    console.log(`Bundles salvos: ${saved} em recon/js/`);
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  console.error('Falha na captura:', error.message);
  process.exitCode = 1;
});
