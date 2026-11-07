/* Separate from index.htm so script-src 'self' needs no unsafe-inline. */
(() => {
  'use strict';
  const root = document.getElementById('cqa-d365');
  const status = document.getElementById('cqa-d365-status');
  document.body.style.margin = '0';
  status.className = 'cqa';
  status.style.display = 'none';
  status.style.minHeight = '0';
  let unmount;
  let generation = 0;
  let shownPolicy = false;

  // Bootstrap messages cannot depend on a module that CSP may prevent loading.
  function banner(target, message) {
    const box = document.createElement('p');
    box.className = 'cqa-banner cqa-banner--error';
    box.setAttribute('role', 'alert');
    box.style.overflowWrap = 'anywhere';
    box.style.gridColumn = '1 / -1';
    box.textContent = message;
    target.replaceChildren(box);
    target.hidden = false;
  }

  function onPolicy(event) {
    const directive = event.effectiveDirective;
    if (shownPolicy || !['connect-src', 'font-src', 'media-src'].includes(directive)) return;
    shownPolicy = true;
    let origin = event.blockedURI;
    status.style.display = 'block';
    try { origin = new URL(origin).origin; } catch { /* CSP also reports data: and inline. */ }
    banner(status, `Политика CSP блокирует ${directive} для ${origin}. Администратору Dynamics 365 нужно разрешить этот источник в ${directive}.`);
  }

  function stop() {
    generation += 1;
    unmount?.();
    unmount = undefined;
    window.removeEventListener('securitypolicyviolation', onPolicy);
  }

  async function start() {
    stop();
    const current = generation;
    shownPolicy = false;
    status.hidden = true;
    status.replaceChildren();
    status.style.display = 'none';
    window.addEventListener('securitypolicyviolation', onPolicy);
    const params = new URLSearchParams(location.search);
    let options;
    try {
      options = JSON.parse(params.get('data') || '{}');
    } catch {
      banner(root, 'Не удалось открыть CQA: параметр data содержит некорректный JSON. Укажите объект с apiBase и, при необходимости, route.');
      return;
    }
    if (!options || typeof options.apiBase !== 'string' || !options.apiBase.trim()) {
      banner(root, 'Не удалось открыть CQA: в параметре data отсутствует адрес API apiBase. Пример: {"apiBase":"https://cqa.example.com/api"}.');
      return;
    }
    if (options.route !== undefined && (typeof options.route !== 'string' || !options.route.startsWith('#/'))) {
      banner(root, 'Не удалось открыть CQA: route должен быть строкой маршрута, например #/dialogs/DEV.');
      return;
    }
    try {
      const { mountCqa } = await import('./dist/main.js');
      if (current !== generation) return;
      // Set the hash before subscribing: assigning it inside mountCqa otherwise
      // queues a second initial route render and duplicates its API requests.
      if (!location.hash && options.route) history.replaceState(null, '', `${location.pathname}${location.search}${options.route}`);
      unmount = mountCqa(root, {
        apiBase: options.apiBase.trim(),
        route: options.route,
        record: { id: params.get('id') || undefined, typename: params.get('typename') || undefined },
      });
    } catch {
      if (current !== generation) return;
      root.classList.add('cqa');
      banner(root, 'Не удалось загрузить модуль CQA. Проверьте загрузку dist/main.js, MIME text/javascript и разрешение script-src в политике CSP организации.');
    }
  }

  window.addEventListener('pagehide', stop);
  window.addEventListener('pageshow', (event) => { if (event.persisted) void start(); });
  void start();
})();
