import { t } from '../i18n.js';
import { hrefDialogs, hrefTranscript } from '../router.js';
import type { Ctx } from '../router.js';
import type { BreakdownRow, DriftMetric, DriftReport, GroupAnalytics } from '../types.gen.js';
import { banner, errorDetails, errorMessage, fmt, h } from '../ui/dom.js';
import type { Child } from '../ui/dom.js';

function kpi(label: string, value: Child, hint?: string, tone = ''): HTMLElement {
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

/** Пока данные грузятся: подписи KPI уже известны, вместо чисел спокойные статичные плашки (не нули). */
function skeleton(): HTMLElement[] {
  const block = (cls: string) => h('span', { class: `cqa-skel ${cls}`, 'aria-hidden': 'true' });
  return [
    h('p', { class: 'cqa-loading', role: 'status' }, t.common.loading),
    h(
      'div',
      { class: 'cqa-kpis' },
      [t.analytics.kpiEvaluated, t.analytics.kpiMean, t.analytics.kpiGross, t.analytics.kpiNa].map((label) =>
        h('div', { class: 'cqa-card cqa-kpi' }, h('div', { class: 'cqa-kpi-label' }, label), block('cqa-skel--value')),
      ),
    ),
    h(
      'div',
      { class: 'cqa-analytics-grid', 'aria-hidden': 'true' },
      h('div', { class: 'cqa-card' }, block('cqa-skel--title'), [1, 2, 3, 4].map(() => block('cqa-skel--row'))),
      h('div', { class: 'cqa-card' }, block('cqa-skel--title'), block('cqa-skel--chart')),
    ),
  ];
}

function breakdown(title: string, rows: BreakdownRow[], label: (k: string) => string): HTMLElement {
  return h(
    'section',
    { class: 'cqa-card cqa-breakdown' },
    h('h2', { class: 'cqa-card-title' }, title),
    h(
      'div',
      { class: 'cqa-table-wrap', tabindex: '0', role: 'region', 'aria-label': title },
      h(
        'table',
        { class: 'cqa-table' },
        h('thead', null, h('tr', null, [t.analytics.colKey, t.analytics.colCount, t.analytics.colMean].map((x, i) => h('th', { scope: 'col', class: i ? 'cqa-num' : '' }, x)))),
        h('tbody', null, rows.map((r) => h('tr', null, h('td', null, label(r.key)), h('td', { class: 'cqa-num' }, String(r.count)), h('td', { class: 'cqa-num' }, fmt(r.mean_total))))),
      ),
    ),
  );
}

const DRIFT_GROUPS = ['DEV', 'PROD', 'PART2'];

function driftRow(label: string, m: DriftMetric, withKs: boolean, id?: string): HTMLElement {
  const d = t.analytics.drift;
  const tone = m.verdict === 'drift' ? 'bad' : m.verdict === 'watch' ? 'warn' : m.verdict === 'stable' ? 'good' : '';
  const num = (x: number | null, digits: number) => (x === null ? t.common.none : x.toFixed(digits).replace('.', ','));
  return h(
    'tr',
    { 'data-drift': id ?? label },
    h('td', { title: id ?? undefined }, label),
    h('td', { class: 'cqa-num' }, `${m.n_baseline} / ${m.n_window}`),
    h('td', { class: 'cqa-num' }, num(m.psi, 3)),
    h('td', { class: 'cqa-num' }, withKs ? num(m.ks, 3) : '—'),
    h('td', { class: 'cqa-num' }, withKs ? (m.ks_p === null ? t.common.none : m.ks_p < 0.001 ? '< 0,001' : num(m.ks_p, 3)) : '—'),
    h('td', null, m.verdict ? h('span', { class: `cqa-badge cqa-badge--${tone}` }, d[m.verdict]) : d.none),
  );
}

/** `failure` — база не загрузилась: вместо таблицы ошибка, выбор базы остаётся, чтобы вернуться. */
function driftCard(drift: DriftReport, group: string, baseline: string, onBaseline: (b: string) => void, failure: unknown = null): HTMLElement {
  const d = t.analytics.drift;
  const select = h(
    'select',
    { class: 'cqa-select', id: 'cqa-drift-baseline', 'aria-label': d.baselineLabel },
    h('option', { value: '', selected: !baseline }, d.halves),
    DRIFT_GROUPS.filter((g) => g !== group).map((g) => h('option', { value: g, selected: g === baseline }, d.against(g))),
  ) as HTMLSelectElement;
  select.addEventListener('change', () => onBaseline(select.value));
  const rows = [driftRow(d.total, drift.total, true), ...drift.criteria.map((c) => driftRow(c.title, c.metric, false, c.criterion_id))];
  return h(
    'section',
    { class: 'cqa-card cqa-drift', id: 'cqa-drift' },
    h('h2', { class: 'cqa-card-title' }, d.title),
    h('p', { class: 'cqa-muted' }, d.intro),
    h('div', { class: 'cqa-drift-controls' }, h('label', { for: 'cqa-drift-baseline' }, `${d.baselineLabel}: `), select),
    failure
      ? banner(d.baselineFailed(baseline), [errorMessage(failure), ...(errorDetails(failure) ?? [])], 'error', true)
      : [
          h('p', { class: 'cqa-muted' }, drift.mode === 'groups' ? d.modeGroups(drift.baseline_label, drift.window_label) : d.modeHalves),
          h('p', { class: 'cqa-muted' }, d.thresholds),
          drift.enough_data ? null : banner(d.tooFew(drift.min_n, drift.total.n_baseline, drift.total.n_window), null, 'info'),
          h(
            'div',
            { class: 'cqa-table-wrap', tabindex: '0', role: 'region', 'aria-label': d.title },
            h(
              'table',
              { class: 'cqa-table' },
              h('thead', null, h('tr', null, [d.colWhat, d.colN, d.colPsi, d.colKs, d.colKsP, d.colVerdict].map((x, i) => h('th', { scope: 'col', class: i && i < 5 ? 'cqa-num' : '' }, x)))),
              h('tbody', null, rows),
            ),
          ),
        ],
  );
}

function content(data: GroupAnalytics, group: string, baseline: string, onBaseline: (b: string) => void, driftFailure: unknown = null): HTMLElement[] {
  const slots = data.criteria.reduce((n, c) => n + c.applicable + c.na, 0);
  const naTotal = data.criteria.reduce((n, c) => n + c.na, 0);
  const naShare = slots ? (naTotal / slots) * 100 : 0;

  const kpis = h(
    'div',
    { class: 'cqa-kpis' },
    kpi(t.analytics.kpiEvaluated, String(data.evaluated), t.analytics.kpiOf(data.dialogs)),
    kpi(
      t.analytics.kpiMean,
      data.mean_total === null ? t.common.none : [fmt(data.mean_total), h('span', { class: 'cqa-kpi-unit' }, ' / 100')],
      undefined,
      `cqa-kpi--${barTone(data.mean_total)}`,
    ),
    kpi(t.analytics.kpiGross, String(data.gross_error_count), undefined, data.gross_error_count ? 'cqa-kpi--bad' : ''),
    kpi(t.analytics.kpiNa, `${fmt(Math.round(naShare * 10) / 10)} %`),
  );

  // Полоса декоративна (aria-hidden): значение читается из видимой подписи справа.
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
          h('div', { class: 'cqa-bar', 'aria-hidden': 'true' }, h('div', { class: `cqa-bar-fill cqa-bar-fill--${barTone(c.mean_pct)}`, style: `width:${c.mean_pct ?? 0}%` })),
          h('span', { class: 'cqa-bar-value' }, c.mean_pct === null ? t.common.none : `${fmt(c.mean_pct)} %`),
        ),
      ),
    ),
  );

  // Цвет диапазона дублируется подписью диапазона и числом над столбцом; для чтения с экрана — одна строка.
  const max = Math.max(1, ...data.histogram.map((b) => b.count));
  const hist = h(
    'section',
    { class: 'cqa-card' },
    h('h2', { class: 'cqa-card-title' }, t.analytics.histogram),
    h('p', { class: 'cqa-muted cqa-hist-note' }, t.analytics.histNote),
    h(
      'div',
      { class: 'cqa-hist', role: 'img', 'aria-label': t.analytics.histAria(data.histogram.map((b) => t.analytics.histRange(b.label, b.count)).join('; ')) },
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

  // Маршрут диалога сам открывает последнюю оценку (renderTranscriptOnly), поэтому href настоящий и без лишнего запроса.
  const grossList = h(
    'section',
    { class: 'cqa-card' },
    h('h2', { class: 'cqa-card-title' }, t.analytics.grossList),
    data.gross_error_ids.length
      ? h('ul', { class: 'cqa-gross-list' }, data.gross_error_ids.map((id) => h('li', null, h('a', { href: hrefTranscript(group, id), 'data-cid': id }, id))))
      : h('p', { class: 'cqa-muted' }, t.analytics.grossNone),
  );

  return [
    kpis,
    h('div', { class: 'cqa-analytics-grid' }, criteria, h('div', null, hist, breakdown(t.analytics.byChannel, data.by_channel, (k) => t.channel[k] ?? k), breakdown(t.analytics.byLanguage, data.by_language, (k) => k))),
    grossList,
    ...(data.drift ? [driftCard(data.drift, group, baseline, onBaseline, driftFailure)] : []),
  ];
}

export async function render(root: HTMLElement, ctx: Ctx): Promise<void> {
  const group = ctx.params.group;
  const head = h(
    'div',
    { class: 'cqa-page-head' },
    h('div', null, h('h1', { class: 'cqa-page-title' }, t.analytics.title), h('p', { class: 'cqa-page-subtitle' }, t.analytics.subtitle(group))),
  );

  let baseline = '';
  // Последние успешно загруженные данные: если не загрузилась только база дрейфа, остальное остаётся на экране.
  let last: GroupAnalytics | null = null;
  const onBaseline = (b: string) => {
    baseline = b;
    void load();
  };
  let seq = 0;
  const load = async (): Promise<void> => {
    const mine = ++seq;
    if (!last) root.replaceChildren(head, ...skeleton());
    let data: GroupAnalytics;
    try {
      data = await ctx.api.analytics(group, baseline || undefined);
    } catch (e) {
      if (ctx.signal.aborted || mine !== seq) return;
      if (baseline && last) {
        root.replaceChildren(head, ...content(last, group, baseline, onBaseline, e));
        return;
      }
      const alert = banner(errorMessage(e), errorDetails(e));
      alert.append(h('div', { class: 'cqa-analytics-retry' }, h('button', { type: 'button', class: 'cqa-btn', onclick: () => void load() }, t.analytics.retry)));
      root.replaceChildren(head, alert);
      return;
    }
    if (ctx.signal.aborted || mine !== seq) return;
    if (data.evaluated === 0) {
      root.replaceChildren(
        head,
        h('div', { class: 'cqa-card cqa-empty' }, h('p', { class: 'cqa-muted' }, t.analytics.empty), h('a', { href: hrefDialogs(group) }, t.analytics.toDialogs)),
      );
      return;
    }
    last = data;
    root.replaceChildren(head, ...content(data, group, baseline, onBaseline));
  };
  await load();
}
