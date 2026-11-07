import { t } from '../i18n.js';
import type { Criterion, EvaluationView, FinalItem, Item, ScoreItem } from '../types.gen.js';
import { badge, fmt, h, rangeOf, stepDescription, verdictLabel, verdictTone } from './dom.js';

export interface CriteriaTableOptions {
  view: EvaluationView;
  onEvidence: (idx: number) => void;
  onExpected: (range: [number, number]) => void;
  onAppeal: (criterion: Criterion) => void;
}

function verdictChip(c: Criterion | undefined, verdict: string): HTMLElement {
  const desc = stepDescription(c, verdict);
  const label = c?.kind === 'gross_error' && verdict === 'yes' ? `${t.common.yes} (${t.result.grossFound})` : verdictLabel(verdict);
  return badge(label, verdictTone(c, verdict), desc ?? undefined);
}

/** original → решение (причина) → итог, для строк с решённой апелляцией. */
function chain(c: Criterion, fin: FinalItem): HTMLElement {
  const d = fin.decision;
  if (!d) return verdictChip(c, fin.final_verdict);
  const action = d.action === 'confirm' ? t.result.confirmed : t.result.changedTo(verdictLabel(d.new_verdict ?? ''));
  return h(
    'div',
    { class: 'cqa-chain' },
    verdictChip(c, fin.original_verdict),
    h('span', { class: 'cqa-chain-arrow', 'aria-hidden': 'true' }, '→'),
    h('span', { class: 'cqa-chain-decision' }, `${action} (${d.reason})`),
    h('span', { class: 'cqa-chain-arrow', 'aria-hidden': 'true' }, '→'),
    h('span', { class: 'cqa-chain-final' }, `${t.result.final}: `, verdictChip(c, fin.final_verdict)),
  );
}

function pointsCell(score: ScoreItem | undefined): HTMLElement {
  if (!score || !score.applicable || score.points === null) return h('td', { class: 'cqa-num' }, t.common.none);
  const eff = score.effective_points;
  return h(
    'td',
    { class: 'cqa-num', title: eff === null ? undefined : `${t.result.effective}: ${fmt(eff)}` },
    `${fmt(score.points)} / ${fmt(score.max_points)}`,
  );
}

function evidenceCell(item: Item | undefined, opts: CriteriaTableOptions): HTMLElement {
  const cell = h('td', { class: 'cqa-evidence' });
  if (!item) return cell;
  for (const idx of item.evidence_idx) {
    cell.appendChild(
      h('button', { type: 'button', class: 'cqa-link cqa-evidence-link', onclick: () => opts.onEvidence(idx) }, t.result.evidenceLabel(idx)),
    );
  }
  const range = item.verdict === 'no' ? rangeOf(item.expected_range) : null;
  if (range) {
    cell.appendChild(
      h('button', { type: 'button', class: 'cqa-link cqa-expected-link', onclick: () => opts.onExpected(range) }, t.result.expectedHere),
    );
  }
  return cell;
}

function votesBadge(item: Item | undefined, k: number): HTMLElement | null {
  if (k <= 1 || !item?.votes) return null;
  const text = Object.entries(item.votes)
    .map(([verdict, n]) => `${verdictLabel(verdict)}×${n}`)
    .join(' · ');
  return badge(`${t.result.votes}: ${text}`, 'info');
}

export function renderCriteriaTable(opts: CriteriaTableOptions): HTMLElement {
  const { view } = opts;
  const { checklist, evaluation, final, appeals } = view;
  const items = new Map(evaluation.items.map((i) => [i.criterion_id, i]));
  const finals = new Map(final.items.map((f) => [f.criterion_id, f]));
  const scores = new Map(final.score.items.map((s) => [s.criterion_id, s]));
  const sections = new Map(checklist.sections.map((s) => [s.id, s.title]));

  const body = h('tbody');
  for (const c of checklist.criteria) {
    const item = items.get(c.id);
    const fin = finals.get(c.id);
    const hasOpen = appeals.some((a) => a.criterion_id === c.id && a.status === 'open');
    const grossFound = c.kind === 'gross_error' && (fin?.final_verdict ?? item?.verdict) === 'yes';
    const tone = grossFound ? 'cqa-row--gross' : '';

    const verdictCell = h('td', { class: 'cqa-verdict' });
    if (!item) verdictCell.appendChild(h('span', { class: 'cqa-muted' }, t.result.noItem));
    else if (fin?.decision) verdictCell.appendChild(chain(c, fin));
    else verdictCell.appendChild(verdictChip(c, item.verdict));
    if (item?.verdict === 'na' && item.na_reason) {
      verdictCell.appendChild(h('div', { class: 'cqa-na-reason' }, item.na_reason));
    }

    const warnings = item?.warnings ?? [];
    const explain = h(
      'td',
      { class: 'cqa-explanation' },
      item?.explanation ?? '',
      votesBadge(item, evaluation.k),
      warnings.length ? badge('⚠', 'warn', warnings.join('\n')) : null,
    );

    const action = hasOpen
      ? badge(t.result.appealOpen, 'warn')
      : h(
          'button',
          { type: 'button', class: 'cqa-btn cqa-btn--small', onclick: () => opts.onAppeal(c), 'data-criterion': c.id },
          t.result.appeal,
        );

    body.appendChild(
      h(
        'tr',
        { class: `cqa-row ${tone}`, 'data-criterion': c.id },
        h('td', { class: 'cqa-section' }, c.section_id ? (sections.get(c.section_id) ?? c.section_id) : t.checklists.noSection),
        h(
          'td',
          { class: 'cqa-title' },
          h(
            'div',
            { class: 'cqa-title-text' },
            c.title,
            c.kind === 'gross_error'
              ? grossFound
                ? badge(t.checklists.grossError, 'bad')
                : badge(t.result.kindGross, 'neutral')
              : null,
          ),
          h('div', { class: 'cqa-muted cqa-id' }, c.id),
        ),
        verdictCell,
        pointsCell(scores.get(c.id)),
        explain,
        evidenceCell(item, opts),
        h('td', { class: 'cqa-actions' }, action),
      ),
    );
  }

  return h(
    'table',
    { class: 'cqa-table cqa-criteria' },
    h(
      'thead',
      null,
      h(
        'tr',
        null,
        [
          t.result.colSection,
          t.result.colTitle,
          t.result.colVerdict,
          t.result.colPoints,
          t.result.colExplanation,
          t.result.colEvidence,
          t.result.colActions,
        ].map((label) => h('th', { scope: 'col' }, label)),
      ),
    ),
    body,
  );
}
