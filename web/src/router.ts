import type { Api } from './api.js';

/** Контекст, который получает каждое представление. */
export interface Ctx {
  api: Api;
  params: Record<string, string>;
  navigate: (hash: string) => void;
  /** Срабатывает при уходе с маршрута: остановить опросы и отложенные обновления. */
  signal: AbortSignal;
}

export type View = (root: HTMLElement, ctx: Ctx) => Promise<void>;

export type RouteName = 'dialogs' | 'transcript' | 'evaluation' | 'review' | 'checklists' | 'checklist' | 'analytics' | 'notfound';

export interface Route {
  name: RouteName;
  params: Record<string, string>;
}

export const DEFAULT_GROUP = 'DEV';

export function parseHash(hash: string): Route {
  const path = hash.replace(/^#\/?/, '');
  const parts = path.split('/').filter((p) => p !== '').map(decodeURIComponent);
  const [head, a, b] = parts;
  switch (head) {
    case undefined:
    case 'dialogs':
      if (a && b) return { name: 'transcript', params: { group: a, cid: b } };
      return { name: 'dialogs', params: { group: a || DEFAULT_GROUP } };
    case 'evaluation':
      return a ? { name: 'evaluation', params: { id: a } } : { name: 'notfound', params: {} };
    case 'review':
      return { name: 'review', params: {} };
    case 'checklists':
      return a ? { name: 'checklist', params: { id: a } } : { name: 'checklists', params: {} };
    case 'analytics':
      return { name: 'analytics', params: { group: a || DEFAULT_GROUP } };
    default:
      return { name: 'notfound', params: {} };
  }
}

export const hrefDialogs = (group: string) => `#/dialogs/${encodeURIComponent(group)}`;
export const hrefTranscript = (group: string, cid: string) =>
  `#/dialogs/${encodeURIComponent(group)}/${encodeURIComponent(cid)}`;
export const hrefAnalytics = (group: string) => `#/analytics/${encodeURIComponent(group)}`;
export const hrefEvaluation = (id: string) => `#/evaluation/${encodeURIComponent(id)}`;
export const hrefChecklist = (id: string) => `#/checklists/${encodeURIComponent(id)}`;

/** Подписывается на hashchange, сразу вызывает обработчик. Возвращает функцию отписки. */
export function startRouter(onRoute: (route: Route) => void): () => void {
  const handler = () => onRoute(parseHash(location.hash));
  window.addEventListener('hashchange', handler);
  handler();
  return () => window.removeEventListener('hashchange', handler);
}
