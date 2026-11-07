import type { Api } from '../api.js';
import { t } from '../i18n.js';
import type { Criterion, EvaluationSummary, EvaluationView } from '../types.gen.js';
import { badge, banner, errorDetails, errorMessage, fmt, fmtDate, h, verdictLabel, verdictTone } from './dom.js';

interface Side {
  verdict: string | null;
  finalVerdict: string | null;
  points: number | null;
  explanation: string;
  decision: string | null;
  criterion: Criterion | undefined;
}

function side(view: EvaluationView, id: string): Side {
  const item = view.evaluation.items.find((i) => i.criterion_id === id);
  const fin = view.final.items.find((i) => i.criterion_id === id);
  const score = view.final.score.items.find((i) => i.criterion_id === id);
  const d = fin?.decision;
  const decision = d
    ? `${t.caseTools.diffAppeal}: ${d.action === 'confirm' ? t.result.confirmed : t.result.changedTo(verdictLabel(d.new_verdict ?? ''))} (${d.reason})`
    : null;
  return {
    verdict: item?.verdict ?? null,
    finalVerdict: fin?.final_verdict ?? item?.verdict ?? null,
    points: score && score.applicable ? score.points : null,
    explanation: item?.explanation ?? '',
    decision,
    criterion: view.checklist.criteria.find((c) => c.id === id),
  };
}

function cell(s: Side, c: Criterion | undefined): HTMLElement {
  if (s.finalVerdict === null) return h('td', { class: 'cqa-muted' }, t.caseTools.diffCriterionMissing);
  const rawDiffers = s.verdict !== null && s.verdict !== s.finalVerdict;
  return h(
    'td',
    null,
    rawDiffers ? [badge(verdictLabel(s.verdict ?? ''), verdictTone(c, s.verdict ?? ''), t.caseTools.diffRaw), ' → '] : null,
    badge(verdictLabel(s.finalVerdict), verdictTone(c, s.finalVerdict)),
    ` ${t.caseTools.diffPoints}: ${fmt(s.points)}`,
    s.decision ? h('div', { class: 'cqa-muted' }, s.decision) : null,
    s.explanation ? h('div', { class: 'cqa-diff-expl' }, s.explanation) : null,
  );
}

const changed = (a: Side, b: Side) => a.finalVerdict !== b.finalVerdict || a.verdict !== b.verdict || a.points !== b.points;

function versionLine(label: string, v: EvaluationView): HTMLElement {
  const ev = v.evaluation;
  return h(
    'div',
    null,
    h('strong', null, `${label}: `),
    `${t.caseTools.diffChecklist} ${v.checklist.name} v${ev.checklist_version} · ${fmtDate(ev.created_at)} · ${t.caseTools.diffTotal}: `,
    h('strong', null, fmt(v.final.score.total)),
  );
}

export function renderDiff(before: EvaluationView, after: EvaluationView): HTMLElement {
  const ids: string[] = [];
  for (const v of [before, after]) {
    for (const c of v.checklist.criteria) if (!ids.includes(c.id)) ids.push(c.id);
  }
  const rows: HTMLElement[] = [];
  const same: string[] = [];
  for (const id of ids) {
    const a = side(before, id);
    const b = side(after, id);
    const c = b.criterion ?? a.criterion;
    if (changed(a, b)) {
      rows.push(h('tr', { class: 'cqa-row cqa-diff-changed' }, h('td', null, c?.title ?? id, h('div', { class: 'cqa-muted cqa-id' }, id)), cell(a, a.criterion ?? c), cell(b, b.criterion ?? c)));
    } else {
      same.push(c?.title ?? id);
    }
  }
  return h(
    'div',
    { class: 'cqa-diff-result' },
    versionLine(t.caseTools.diffBefore, before),
    versionLine(t.caseTools.diffAfter, after),
    h('p', null, h('strong', null, t.caseTools.diffChanged(rows.length))),
    rows.length
      ? h(
          'div',
          { class: 'cqa-table-wrap' },
          h(
            'table',
            { class: 'cqa-table cqa-diff' },
            h('thead', null, h('tr', null, [t.result.colTitle, t.caseTools.diffBefore, t.caseTools.diffAfter].map((l) => h('th', { scope: 'col' }, l)))),
            h('tbody', null, rows),
          ),
        )
      : h('p', { class: 'cqa-muted' }, t.caseTools.diffNoChanges),
    same.length ? h('details', { class: 'cqa-diff-same' }, h('summary', null, t.caseTools.diffUnchanged(same.length)), h('ul', null, same.map((s) => h('li', null, s)))) : null,
  );
}

const label = (s: EvaluationSummary) => `${s.checklist_id} v${s.checklist_version} · ${fmt(s.final_total)} · ${fmtDate(s.created_at)}`;

/** Блок «Сравнение оценок»: выбор двух оценок диалога из истории и их дифф. */
export function diffPanel(api: Api, history: EvaluationSummary[], currentId: string): HTMLElement {
  const box = h('section', { class: 'cqa-diff-panel' }, h('h3', null, t.caseTools.diffTitle));
  if (history.length < 2) {
    box.appendChild(h('p', { class: 'cqa-muted' }, t.caseTools.diffNeedTwo));
    return box;
  }
  const sorted = [...history].sort((x, y) => x.created_at.localeCompare(y.created_at));
  const found = sorted.findIndex((s) => s.id === currentId);
  const pos = found < 0 ? sorted.length - 1 : found;
  const afterDefault = sorted[pos]!;
  const beforeDefault = sorted[pos > 0 ? pos - 1 : 1]!;
  const select = (name: string, value: string) =>
    h(
      'select',
      { class: 'cqa-select', 'aria-label': name, id: `cqa-diff-${name === t.caseTools.diffBefore ? 'before' : 'after'}` },
      sorted.map((s) => h('option', { value: s.id, selected: s.id === value }, label(s))),
    ) as HTMLSelectElement;
  const beforeSel = select(t.caseTools.diffBefore, beforeDefault.id);
  const afterSel = select(t.caseTools.diffAfter, afterDefault.id);
  const out = h('div', { class: 'cqa-diff-out', role: 'status' });
  const run = h('button', { type: 'button', class: 'cqa-btn', id: 'cqa-diff-run' }, t.caseTools.diffRun);
  run.addEventListener('click', async () => {
    if (beforeSel.value === afterSel.value) {
      out.replaceChildren(banner(t.caseTools.diffSame, null, 'info'));
      return;
    }
    out.replaceChildren(h('span', { class: 'cqa-muted' }, t.common.loading));
    try {
      const [b, a] = await Promise.all([api.evaluation(beforeSel.value), api.evaluation(afterSel.value)]);
      out.replaceChildren(renderDiff(b, a));
    } catch (e) {
      out.replaceChildren(banner(errorMessage(e), errorDetails(e)));
    }
  });
  box.append(
    h('p', { class: 'cqa-muted' }, t.caseTools.diffHint),
    h('div', { class: 'cqa-diff-controls' }, `${t.caseTools.diffBefore}: `, beforeSel, ` ${t.caseTools.diffAfter}: `, afterSel, ' ', run),
    out,
  );
  return box;
}
