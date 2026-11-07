
const { chromium } = require("C:/Users/sydyk/AppData/Local/npm-cache/_npx/606f4d49f911e2b4/node_modules/playwright-core/index.js");
(async () => {
  const b = await chromium.launch();
  const routes = [["dialogs", "#/dialogs/DEV"], ["result-chat", "#/evaluation/p1-ru-001-132ab7e5"], ["result-call", "#/evaluation/p4-ru-003-3c6c365a"], ["review", "#/review"], ["checklists", "#/checklists"], ["checklist-editor", "#/checklists/chat"], ["analytics", "#/analytics/DEV"]];
  for (const [vw, vh, tag] of [[1440, 900, 'desktop'], [390, 844, 'mobile']]) {
    const p = await b.newPage({ viewport: { width: vw, height: vh }, locale: 'ru-RU' });
    for (const [n, h] of routes) {
      await p.goto('http://127.0.0.1:8791/' + h, { waitUntil: 'networkidle' });
      await p.waitForTimeout(800);
      await p.screenshot({ path: "C:/Users/sydyk/Downloads/data_challenge/docs/redesign/baseline" + '/' + n + '.' + tag + '.png', fullPage: tag === 'desktop' });
    }
    await p.close();
  }
  await b.close();
})();
