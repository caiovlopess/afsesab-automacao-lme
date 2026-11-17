import { chromium } from 'playwright';
const browser = await chromium.connectOverCDP('http://127.0.0.1:9223');
try {
  const pages = browser.contexts().flatMap((c) => c.pages());
  for (const p of pages) {
    p.on('console', (m) => console.log(`[${p.url().slice(0, 40)}] console.${m.type()}: ${m.text().slice(0, 300)}`));
    p.on('pageerror', (e) => console.log(`[${p.url().slice(0, 40)}] pageerror: ${e.message.slice(0, 300)}`));
  }
  const portal = pages.find((p) => p.url().includes('afsesab'));
  const sidebar = pages.find((p) => p.url().startsWith('af://'));
  await portal.reload({ waitUntil: 'domcontentloaded' });
  await sidebar.reload({ waitUntil: 'domcontentloaded' });
  await portal.waitForTimeout(3000);
  await sidebar.waitForTimeout(2000);
  console.log('\nREA:', await portal.evaluate(() => typeof window.__AF_REA__));
  console.log('badge:', await sidebar.evaluate(() => document.getElementById('backend-badge')?.textContent));
  console.log('afDesktop:', await sidebar.evaluate(() => typeof window.afDesktop));
} finally {
  await browser.close();
}
