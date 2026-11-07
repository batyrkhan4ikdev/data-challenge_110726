import { t } from '../i18n.js';
import { hrefEvaluation } from '../router.js';
import type { Ctx } from '../router.js';
import type { BreakdownRow, GroupAnalytics } from '../types.gen.js';
import { fmt, h } from '../ui/dom.js';

function kpi(label: string, value: string, hint?: string, tone = ''): HTMLElement {
  return h(
    'div',
    { class: `cqa-card cqa-kpi ${tone}` },
    h('div', { class: 'cqa-kpi-label' }, label),
    h('div', { class: 'cqa-kpi-value' }, value),
    hint ? h('div', { class: 'cqa-muted cqa-kpi-hint' }, hint) : null,
  );
}

function barTone(pct: number | null): string {
  return pct === null ? 'none' : pct >= 85 ? 'good' : pct >= 70 ? 'warn' : 'bad';
}

function breakdown(title: string, rows: BreakdownRow[], label: (k: string) => string): HTMLElement {
  return h(
    'section',
    { class: 'cqa-card' },
    h('h2', { class: 'cqa-card-title' }, title),
    h(
      'table',
      { class: 'cqa-table' },
      h('thead', null, h('tr', null, [t.analytics.colKey, t.analytics.colCount, t.analytics.colMean].map((x, i) => h('th', { scope: 'col', class: i ? 'cqa-num' : '' }, x)))),
      h('tbody', null, rows.map((r) => h('tr', null, h('td', null, label(r.key)), h('td', { class: 'cqa-num' }, String(r.count)), h('td', { class: 'cqa-num' }, fmt(r.mean_total))))),
    ),
  );
}

export async function render(root: HTMLElement, ctx: Ctx): Promise<void> {
  const group = ctx.params.group;
  const data: GroupAnalytics = await ctx.api.analytics(group);
  if (ctx.signal.aborted) return;

  const head = h(
    'div',
    { class: 'cqa-page-head' },
    h('div', null, h('h1', { class: 'cqa-page-title' }, t.analytics.title), h('p', { class: 'cqa-page-subtitle' }, t.analytics.subtitle(group))),
  );
  if (data.evaluated === 0) {
    root.replaceChildren(head, h('div', { class: 'cqa-card cqa-empty cqa-muted' }, t.analytics.empty));
    return;
  }

  const slots = data.criteria.reduce((n, c) => n + c.applicable + c.na, 0);
  const naTotal = data.criteria.reduce((n, c) => n + c.na, 0);
  const naShare = slots ? (naTotal / slots) * 100 : 0;

  const kpis = h(
    'div',
    { class: 'cqa-kpis' },
    kpi(t.analytics.kpiEvaluated, String(data.evaluated), t.analytics.kpiOf(data.dialogs)),
    kpi(t.analytics.kpiMean, data.mean_total === null ? t.common.none : `${fmt(data.mean_total)} / 100`, undefined, `cqa-kpi--${barTone(data.mean_total)}`),
    kpi(t.analytics.kpiGross, String(data.gross_error_count), undefined, data.gross_error_count ? 'cqa-kpi--bad' : ''),
    kpi(t.analytics.kpiNa, `${fmt(Math.round(naShare * 10) / 10)} %`),
  );

  const criteria = h(
    'section',
    { class: 'cqa-card' },
    h('h2', { class: 'cqa-card-title' }, t.analytics.criteria),
    h(
      'ul',
      { class: 'cqa-bars' },
      data.criteria.map((c) =>
        h(
          'li',
          { class: 'cqa-bar-row', 'data-criterion': c.criterion_id },
          h('div', { class: 'cqa-bar-label' }, h('strong', null, c.title), h('span', { class: 'cqa-muted' }, t.analytics.criteriaHint(c.applicable, c.yes, c.no, c.na))),
          h(
            'div',
            { class: 'cqa-bar', role: 'img', 'aria-label': `${c.title}: ${fmt(c.mean_pct)} %` },
            h('div', { class: `cqa-bar-fill cqa-bar-fill--${barTone(c.mean_pct)}`, style: `width:${c.mean_pct ?? 0}%` }),
          ),
          h('span', { class: 'cqa-bar-value' }, c.mean_pct === null ? t.common.none : `${fmt(c.mean_pct)} %`),
        ),
      ),
    ),
  );

  const max = Math.max(1, ...data.histogram.map((b) => b.count));
  const hist = h(
    'section',
    { class: 'cqa-card' },
    h('h2', { class: 'cqa-card-title' }, t.analytics.histogram),
    h(
      'div',
      { class: 'cqa-hist' },
      data.histogram.map((b, i) =>
        h(
          'div',
          { class: 'cqa-hist-col' },
          h('span', { class: 'cqa-hist-count' }, String(b.count)),
          h('div', { class: `cqa-hist-bar cqa-hist-bar--${i}`, style: `height:${(b.count / max) * 100}%` }),
          h('span', { class: 'cqa-hist-label' }, b.label),
        ),
      ),
    ),
  );

  // Ссылка на оценку: ведёт в карточку последней оценки диалога.
  const grossList = h(
    'section',
    { class: 'cqa-card' },
    h('h2', { class: 'cqa-card-title' }, t.analytics.grossList),
    data.gross_error_ids.length
      ? h('ul', { class: 'cqa-gross-list' }, data.gross_error_ids.map((id) => h('li', null, h('a', { class: 'cqa-link', href: '#', 'data-cid': id }, id))))
      : h('p', { class: 'cqa-muted' }, t.analytics.grossNone),
  );
  for (const a of Array.from(grossList.querySelectorAll<HTMLAnchorElement>('a[data-cid]'))) {
    const cid = a.dataset.cid ?? '';
    a.addEventListener('click', (e: Event) => {
      e.preventDefault();
      void ctx.api.evaluationsFor(cid).then((list) => {
        const latest = list[0];
        if (latest) ctx.navigate(hrefEvaluation(latest.id));
      });
    });
  }

  root.replaceChildren(
    head,
    kpis,
    h('div', { class: 'cqa-analytics-grid' }, criteria, h('div', null, hist, breakdown(t.analytics.byChannel, data.by_channel, (k) => t.channel[k] ?? k), breakdown(t.analytics.byLanguage, data.by_language, (k) => k))),
    grossList,
  );
}
