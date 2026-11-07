// node scripts/d365_harness/run_checks.cjs --python <python> --out <outside-repo-dir> [--post]
// Start the API on :8806 with CQA_ALLOWED_ORIGINS=http://127.0.0.1:8807 first.
// --post requires that API's store to be a disposable COPY, never the shared store.
const { chromium } = require('C:/Users/sydyk/AppData/Local/npm-cache/_npx/606f4d49f911e2b4/node_modules/playwright-core/index.js');
const assert = require('node:assert/strict');
const { spawn } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const args = process.argv.slice(2);
const option = (name, fallback) => args.includes(name) ? args[args.indexOf(name) + 1] : fallback;
const python = option('--python', 'python');
const output = path.resolve(option('--out', path.join(os.tmpdir(), 'cqa-d365-shots')));
const api = 'http://127.0.0.1:8806';
const host = 'http://127.0.0.1:8807';
const routes = ['#/dialogs/DEV', '#/evaluation/p1-ru-001-132ab7e5', '#/evaluation/p4-ru-003-3c6c365a', '#/review', '#/checklists', '#/checklists/chat', '#/analytics/DEV'];
const failures = [];
const results = [];
let mediaOrigin = option('--media-origin', '');
fs.mkdirSync(output, { recursive: true });

async function serve(profile, port = 8807) {
  const child = spawn(python, [path.join(__dirname, 'serve_package.py'), '--profile', profile, '--port', String(port), '--media-origin', mediaOrigin], { stdio: ['ignore', 'pipe', 'pipe'] });
  await new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error('Rig startup timeout')), 15000);
    child.stdout.on('data', (chunk) => {
      if (chunk.toString().includes('Rig ready')) { clearTimeout(timer); resolve(); }
    });
    child.stderr.on('data', (chunk) => process.stderr.write(chunk));
    child.on('error', reject);
    child.on('exit', (code) => { clearTimeout(timer); reject(new Error(`Rig exited ${code}`)); });
  });
  return child;
}

async function stop(child) {
  if (child.exitCode !== null) return;
  await new Promise((resolve) => { child.once('exit', resolve); child.kill(); });
}

async function instrument(page) {
  await page.addInitScript(() => {
    window.cqaAudit = { violations: [], fetches: [], hashListeners: [] };
    const audit = window.cqaAudit;
    const add = window.addEventListener;
    const remove = window.removeEventListener;
    window.addEventListener = function(type, fn, options) {
      if (type === 'hashchange' && !audit.hashListeners.includes(fn)) audit.hashListeners.push(fn);
      return add.call(this, type, fn, options);
    };
    window.removeEventListener = function(type, fn, options) {
      if (type === 'hashchange') audit.hashListeners = audit.hashListeners.filter((item) => item !== fn);
      return remove.call(this, type, fn, options);
    };
    add.call(window, 'securitypolicyviolation', (event) => audit.violations.push({ directive: event.effectiveDirective, blocked: event.blockedURI }));
    const fetch = window.fetch;
    window.fetch = function(input, options) {
      audit.fetches.push({ url: String(input), method: options?.method || 'GET' });
      return fetch.call(this, input, options);
    };
  });
}

async function loaded(page) {
  await page.waitForFunction(() => document.querySelector('iframe')?.contentWindow?.location.href.includes('/cqa_/index.htm'));
  const frame = page.frames().find((f) => f.url().startsWith(`${host}/cqa_/index.htm`));
  await page.waitForLoadState('networkidle');
  assert(frame, 'CQA iframe loaded');
  await frame.locator('.cqa-main').waitFor();
  await frame.waitForFunction(() => !document.querySelector('.cqa-loading'));
  await frame.evaluate(() => document.fonts.ready);
  return frame;
}

async function auditFrame(frame, profile, width) {
  const audit = await frame.evaluate(() => ({
    fetches: window.cqaAudit.fetches,
    violations: window.cqaAudit.violations,
    listeners: window.cqaAudit.hashListeners.length,
    width: innerWidth,
    scrollWidth: document.documentElement.scrollWidth,
    logo: [...document.querySelectorAll('.cqa-brand img')].every((img) => img.complete && img.naturalWidth > 0),
    logoCount: document.querySelectorAll('.cqa-brand img').length,
    fonts: [...document.fonts].map((f) => ({ family: f.family, status: f.status })),
    hint: document.getElementById('cqa-d365-status').textContent,
  }));
  assert.equal(audit.width, width);
  assert.equal(audit.scrollWidth, width, `scrollWidth ${audit.scrollWidth} != ${width}`);
  assert.equal(audit.listeners, 1, 'exactly one hashchange listener');
  assert(audit.logoCount > 0 && audit.logo, 'logo loaded');
  assert(audit.fonts.every((f) => f.status === 'loaded'), 'all declared fonts loaded');
  assert(audit.fetches.length > 0 && audit.fetches.every((f) => f.url.startsWith(`${api}/api/`)), 'API fetches cross-origin to :8806');
  if (profile === 'strict-no-api') {
    assert(audit.violations.length > 0, 'connect-src blocked API');
    assert(audit.violations.every((v) => v.directive === 'connect-src' && new URL(v.blocked).origin === api), 'only expected connect-src/API violations');
    assert.deepEqual([...new Set(audit.violations.map((v) => v.blocked))].sort(), [...new Set(audit.fetches.map((f) => f.url))].sort(), 'every attempted API URL blocked, no unexpected violations');
    assert(audit.hint.includes('connect-src') && audit.hint.includes(api), 'readable CSP hint names directive and origin');
  } else {
    assert.deepEqual(audit.violations, [], 'no CSP violations');
  }
  return audit;
}

function problemChecks(problems, profile) {
  assert(!problems.some((p) => /CORS|Access-Control-Allow-Origin/i.test(p)), `No CORS errors: ${problems.join('\n')}`);
  if (profile === 'strict-no-api') {
    assert(problems.every((p) => p.includes(api) && (p.includes('connect-src') || (p.startsWith('Fetch API cannot load') && p.includes('Content Security Policy')))), `Unexpected console messages: ${problems.join('\n')}`);
  } else {
    assert.deepEqual(problems, [], 'clean iframe console');
  }
}

async function runCase(label, fn) {
  try {
    const result = await fn();
    results.push({ label, ...result });
    console.log(JSON.stringify({ label, status: 'PASS', ...result }));
  } catch (error) {
    failures.push({ label, error: error.message });
    console.error(JSON.stringify({ label, status: 'FAIL', error: error.message }));
  }
}

(async () => {
  const browser = await chromium.launch();
  try {
    if (!mediaOrigin) {
      const response = await fetch(`${api}/api/datasets/DEV/conversations/p4-ru-003`);
      assert(response.ok, 'audio record available for server-side CSP configuration');
      const record = await response.json();
      if (record.audio_url) mediaOrigin = new URL(record.audio_url).origin;
    }
    for (const profile of ['default', 'strict-no-api', 'strict-api']) {
      const server = await serve(profile);
      try {
        for (const width of [1440, 1024, 390]) {
          for (const [index, route] of routes.entries()) {
            await runCase(`${profile} ${width} ${route}`, async () => {
              const page = await browser.newPage({ viewport: { width, height: width === 390 ? 844 : 900 }, locale: 'ru-RU' });
              const problems = [];
              const headers = [];
              const responses = [];
              page.on('console', (message) => { if (['error', 'warning'].includes(message.type())) problems.push(message.text()); });
              page.on('pageerror', (error) => problems.push(error.message));
              page.on('response', (response) => {
                if (response.url().startsWith(`${host}/cqa_/`)) headers.push({ url: response.url(), csp: response.headers()['content-security-policy'], mime: response.headers()['content-type'], status: response.status() });
                if (response.url().startsWith(`${api}/api/`)) responses.push(response.status());
              });
              try {
                await instrument(page);
                await page.goto(`${host}/host.html?route=${encodeURIComponent(route)}`);
                const frame = await loaded(page);
                if (width !== 1024) await page.screenshot({ path: path.join(output, `${profile}.${index}.${width}.png`), fullPage: true });
                const audit = await auditFrame(frame, profile, width);
                problemChecks(problems, profile);
                assert(headers.length > 0 && headers.every((h) => h.csp?.includes('frame-ancestors') && h.status === 200), 'CSP response header on every package resource');
                for (const h of headers) {
                  if (new URL(h.url).pathname.endsWith('.js')) assert(h.mime.startsWith('text/javascript'));
                  if (new URL(h.url).pathname.endsWith('.htm')) assert(h.mime.startsWith('text/html'));
                  if (new URL(h.url).pathname.endsWith('.svg')) assert(h.mime.startsWith('image/svg+xml'));
                }
                if (profile === 'strict-no-api') assert.equal(responses.length, 0, 'blocked fetches never reach API');
                else assert(responses.length > 0 && responses.every((s) => s >= 200 && s < 300), 'successful cross-origin API responses');
                return { scrollWidth: audit.scrollWidth, iframeWidth: audit.width, fetches: audit.fetches.length, responses: responses.length, violations: audit.violations, hashListeners: audit.listeners, fonts: audit.fonts, csp: headers[0].csp, console: problems };
              } finally { await page.close(); }
            });
          }
        }

        await runCase(`${profile} remount-3x`, async () => {
          const page = await browser.newPage();
          try {
            await instrument(page);
            await page.goto(`${host}/host.html?route=${encodeURIComponent('#/checklists')}`);
            let frame = await loaded(page);
            const counts = [];
            const listeners = [];
            for (let cycle = 0; cycle < 4; cycle += 1) {
              const audit = await frame.evaluate(() => ({ requests: window.cqaAudit.fetches.map((f) => f.url).sort(), listeners: window.cqaAudit.hashListeners.length }));
              counts.push(audit.requests);
              assert.equal(audit.listeners, 1);
              const after = await frame.evaluate(() => {
                window.dispatchEvent(new PageTransitionEvent('pagehide'));
                return window.cqaAudit.hashListeners.length;
              });
              assert.equal(after, 0, 'pagehide removes router listener');
              listeners.push([audit.listeners, after]);
              if (cycle < 3) {
                await page.evaluate(() => {
                  const old = document.querySelector('iframe');
                  const next = old.cloneNode(false);
                  old.replaceWith(next);
                });
                frame = await loaded(page);
              }
            }
            counts.slice(1).forEach((count) => assert.deepEqual(count, counts[0], 'same requests on every remount'));
            assert.equal(new Set(counts[0]).size, counts[0].length, 'no duplicate initial requests');
            return { requestUrlsPerMount: counts, hashListenersBeforeAfterPagehide: listeners };
          } finally { await page.close(); }
        });

        if (profile !== 'default') {
          await runCase(`${profile} frame-ancestors foreign :8808`, async () => {
            const foreign = await serve(profile, 8808);
            const page = await browser.newPage();
            const problems = [];
            page.on('console', (m) => { if (m.type() === 'error') problems.push(m.text()); });
            try {
              const response = await page.request.get(`${host}/cqa_/index.htm`);
              assert(response.headers()['content-security-policy'].includes(`frame-ancestors ${host}`));
              await page.goto('http://127.0.0.1:8808/host.html', { waitUntil: 'networkidle' });
              assert(problems.some((p) => p.includes('frame-ancestors')), 'browser reports enforced frame-ancestors');
              assert(!page.frames().some((f) => f.url().startsWith(`${host}/cqa_/index.htm`)), 'foreign iframe did not load');
              return { refused: true, console: problems, header: response.headers()['content-security-policy'] };
            } finally { await page.close(); await stop(foreign); }
          });
        }

        if (profile === 'strict-api') {
          for (const [name, data, message] of [['invalid', '{broken', 'некорректный JSON'], ['missing', '{}', 'отсутствует адрес API']]) {
            await runCase(`${name} data banner`, async () => {
              const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
              try {
                await page.goto(`${host}/host.html?data=${encodeURIComponent(data)}`, { waitUntil: 'networkidle' });
                const frame = page.frames().find((f) => f.url().startsWith(`${host}/cqa_/index.htm`));
                assert((await frame.locator('[role=alert]').innerText()).includes(message));
                const screenshot = path.join(output, `${name}.data.390.png`);
                await page.screenshot({ path: screenshot });
                return { screenshot };
              } finally { await page.close(); }
            });
          }
          await runCase('module import failure banner', async () => {
            const page = await browser.newPage();
            try {
              await page.route('**/dist/main.js', (route) => route.abort());
              await page.goto(`${host}/host.html`, { waitUntil: 'networkidle' });
              const frame = page.frames().find((f) => f.url().startsWith(`${host}/cqa_/index.htm`));
              assert((await frame.locator('[role=alert]').innerText()).includes('Не удалось загрузить модуль CQA'));
              return { banner: true };
            } finally { await page.close(); }
          });
          if (args.includes('--post')) {
            await runCase('iframe create appeal then review', async () => {
              const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
              const problems = [];
              page.on('console', (m) => { if (['error', 'warning'].includes(m.type())) problems.push(m.text()); });
              try {
                await instrument(page);
                await page.goto(`${host}/host.html?route=${encodeURIComponent(routes[1])}`);
                const frame = await loaded(page);
                await frame.getByRole('button', { name: 'Оспорить оценку', exact: true }).first().click();
                const comment = `D365 iframe acceptance ${Date.now()}`;
                await frame.locator('dialog textarea').fill(comment);
                const sent = page.waitForResponse((r) => r.url() === `${api}/api/appeals` && r.request().method() === 'POST');
                await frame.locator('dialog button[type=submit]').click();
                assert.equal((await sent).status(), 200);
                await frame.locator('dialog').waitFor({ state: 'detached' });
                await frame.evaluate(() => { location.hash = '#/review'; });
                await frame.getByText(comment, { exact: false }).waitFor();
                assert((await frame.locator('[data-appeal]').count()) > 0);
                problemChecks(problems, profile);
                assert.deepEqual(await frame.evaluate(() => window.cqaAudit.violations), []);
                const screenshot = path.join(output, 'appeal.review.1440.png');
                await page.screenshot({ path: screenshot });
                return { comment, screenshot, console: problems };
              } finally { await page.close(); }
            });
          }
        }
      } finally { await stop(server); }
    }
  } finally { await browser.close(); }
  const summary = { passed: results.length, failures, output, results };
  fs.writeFileSync(path.join(output, 'results.json'), JSON.stringify(summary, null, 2));
  console.log(JSON.stringify({ passed: results.length, failed: failures.length, output }));
  process.exitCode = failures.length ? 1 : 0;
})().catch((error) => { console.error(error); process.exitCode = 1; });
