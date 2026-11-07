import { Api } from './api.js';
import { t } from './i18n.js';
import { startRouter } from './router.js';
import type { Ctx, Route, RouteName, View } from './router.js';
import { navIcon } from './ui/icons.js';
import type { NavIcon } from './ui/icons.js';
import { badge, banner, errorDetails, errorMessage, h } from './ui/dom.js';
import { render as renderAnalytics } from './views/analytics.js';
import { render as renderChecklistEditor } from './views/checklist-editor.js';
import { render as renderChecklists } from './views/checklists.js';
import { render as renderDialogs } from './views/dialogs.js';
import { render as renderResult, renderTranscriptOnly } from './views/result.js';
import { render as renderReview } from './views/review.js';

export interface CqaOptions {
  apiBase: string;
}

const notFound: View = async (root) => {
  root.replaceChildren(banner(t.common.notFound, null, 'info'));
};

const views: { [K in RouteName]: View } = {
  dialogs: renderDialogs,
  transcript: renderTranscriptOnly,
  evaluation: renderResult,
  review: renderReview,
  checklists: renderChecklists,
  checklist: renderChecklistEditor,
  analytics: renderAnalytics,
  notfound: notFound,
};

type NavKey = 'dialogs' | 'checklists' | 'review' | 'analytics';

/** К какому пункту меню относится маршрут. */
const NAV_OF: { [K in RouteName]: NavKey | null } = {
  dialogs: 'dialogs',
  transcript: 'dialogs',
  evaluation: 'dialogs',
  review: 'review',
  checklists: 'checklists',
  checklist: 'checklists',
  analytics: 'analytics',
  notfound: null,
};

const NAV_ITEMS: [NavKey, string, NavIcon][] = [
  ['dialogs', '#/dialogs/DEV', 'dialogs'],
  ['checklists', '#/checklists', 'checklists'],
  ['review', '#/review', 'appeals'],
  ['analytics', '#/analytics/DEV', 'analytics'],
];

/** Монтирует приложение в `root`. Встраиваемо (например, веб-ресурс Dynamics 365). Возвращает функцию размонтирования. */
export function mountCqa(root: HTMLElement, opts: CqaOptions): () => void {
  root.classList.add('cqa');
  const api = new Api(opts.apiBase);

  const badgeSlot = h('div', { class: 'cqa-model-badge' });
  const navLinks = new Map<string, HTMLAnchorElement>();
  const nav = h(
    'nav',
    { class: 'cqa-nav', 'aria-label': t.appTitle },
    NAV_ITEMS.map(([key, href, icon]) => {
      const a = h('a', { href, class: 'cqa-nav-link' }, navIcon(icon), h('span', null, t.nav[key]));
      navLinks.set(key, a);
      return a;
    }),
  );
  const main = h('main', { class: 'cqa-main', id: 'cqa-main' });
  root.replaceChildren(
    h(
      'aside',
      { class: 'cqa-sidebar' },
      h('div', { class: 'cqa-brand', title: t.appTitle }, 'CQA'),
      nav,
      badgeSlot,
    ),
    main,
  );

  // Бейдж модели: первый профиль из GET /api/profiles; при ошибке (например, 404) скрыт.
  api
    .profiles()
    .then((profiles) => {
      const p = profiles[0];
      if (p) badgeSlot.replaceChildren(badge(`${t.modelBadge}: ${p.model || p.name}`, 'info', `${p.name} · ${p.provider}`));
    })
    .catch(() => undefined);

  let controller: AbortController | null = null;

  const show = (route: Route) => {
    controller?.abort();
    const current = new AbortController();
    controller = current;
    const active = NAV_OF[route.name];
    for (const [key, a] of navLinks) {
      if (key === active) a.setAttribute('aria-current', 'page');
      else a.removeAttribute('aria-current');
    }
    const container = h('div', { class: 'cqa-view' }, h('p', { class: 'cqa-muted' }, t.common.loading));
    main.replaceChildren(container);
    const ctx: Ctx = {
      api,
      params: route.params,
      signal: current.signal,
      navigate: (hash) => {
        location.hash = hash;
      },
    };
    views[route.name](container, ctx).catch((e: unknown) => {
      if (current.signal.aborted) return;
      container.replaceChildren(banner(errorMessage(e), errorDetails(e)));
    });
  };

  const stop = startRouter(show);
  return () => {
    stop();
    controller?.abort();
    root.replaceChildren();
    root.classList.remove('cqa');
  };
}

const app = document.getElementById('app');
if (app) mountCqa(app, { apiBase: '/api' });
