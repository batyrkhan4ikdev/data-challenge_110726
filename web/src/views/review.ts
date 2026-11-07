import { t } from '../i18n.js';
import { DEFAULT_GROUP, hrefDialogs, hrefEvaluation } from '../router.js';
import type { Ctx } from '../router.js';
import type { AppealQueueItem, EvaluationView, Record as DialogRecord } from '../types.gen.js';
import { allowedVerdicts, badge, banner, errorDetails, errorMessage, fmt, h, rangeOf, verdictLabel, verdictTone } from '../ui/dom.js';
import { acceptButton, reviewerInput, statsLine } from '../ui/confirmPanel.js';
import { renderTranscript } from '../ui/transcript.js';

interface Loaded {
  view: EvaluationView | null;
  record: DialogRecord | null;
}

/** Окно вокруг evidence_idx[0] (±3) или expected_range (±1); границы обрезаются по транскрипту. */
function fragmentRange(item: AppealQueueItem['item'], turns: number): [number, number] {
  const last = Math.max(0, turns - 1);
  const clamp = (n: number) => Math.min(last, Math.max(0, n));
  const first = item.evidence_idx[0];
  if (first !== undefined) return [clamp(first - 3), clamp(first + 3)];
  const range = rangeOf(item.expected_range);
  if (range) return [clamp(range[0] - 1), clamp(range[1] + 1)];
  return [0, clamp(6)];
}

async function loadFor(ctx: Ctx, q: AppealQueueItem, views: Map<string, Promise<Loaded>>): Promise<Loaded> {
  let pending = views.get(q.evaluation_id);
  if (!pending) {
    pending = (async () => {
      try {
        const view = await ctx.api.evaluation(q.evaluation_id);
        const record = await ctx.api.record(view.evaluation.group_id, view.evaluation.conversation_id).catch(() => null);
        return { view, record };
      } catch {
        return { view: null, record: null };
      }
    })();
    views.set(q.evaluation_id, pending);
  }
  return pending;
}

function card(ctx: Ctx, q: AppealQueueItem, loaded: Loaded, onResolved: () => void): HTMLElement {
  const { appeal, criterion, item } = q;
  const base = `cqa-appeal-${appeal.id}`;
  const titleId = `${base}-title`;
  const reasonErrorId = `${base}-reason-error`;
  const allowed = allowedVerdicts(criterion);
  const dialogHref = hrefEvaluation(q.evaluation_id);

  // Доказательство: фрагмент транскрипта вокруг evidence/expected_range.
  let evidence: HTMLElement | null = null;
  if (loaded.record) {
    const range = fragmentRange(item, loaded.record.transcript.length);
    const tr = renderTranscript(loaded.record, { range, audio: false });
    tr.highlight(item.evidence_idx, item.verdict === 'no' ? rangeOf(item.expected_range) : null);
    evidence = h(
      'section',
      { class: 'cqa-appeal-evidence', 'aria-labelledby': `${base}-fragment` },
      h('h3', { id: `${base}-fragment` }, t.review.fragment),
      h('div', { class: 'cqa-fragment', tabindex: '0', role: 'region', 'aria-label': t.review.fragment }, tr.el),
    );
  }

  const context = h(
    'div',
    { class: 'cqa-appeal-context' },
    h(
      'p',
      { class: 'cqa-appeal-verdict' },
      h('span', { class: 'cqa-field-label' }, t.review.original),
      badge(verdictLabel(item.verdict), verdictTone(criterion, item.verdict)),
    ),
    h('div', { class: 'cqa-appeal-text' }, h('h3', null, t.review.explanation), h('p', null, item.explanation)),
    h('div', { class: 'cqa-appeal-text cqa-appeal-comment' }, h('h3', null, t.review.comment), h('p', null, appeal.comment)),
  );

  // Форма решения.
  const action = { confirm: true };
  let busy = false;
  const newVerdict = h(
    'select',
    { class: 'cqa-input', id: `${base}-verdict` },
    allowed.map((v) => h('option', { value: v }, verdictLabel(v))),
  );
  newVerdict.value = allowed.find((v) => v !== item.verdict) ?? allowed[0] ?? '';
  const verdictField = h(
    'label',
    { class: 'cqa-field cqa-appeal-newverdict', for: newVerdict.id },
    h('span', { class: 'cqa-field-label' }, t.review.newVerdict),
    newVerdict,
  );
  verdictField.hidden = true;
  const reason = h('textarea', {
    class: 'cqa-input cqa-textarea',
    id: `${base}-reason`,
    rows: 3,
    required: true,
    placeholder: t.review.reasonPlaceholder,
  });
  const errors = h('div', { id: reasonErrorId, class: 'cqa-form-errors' });
  const submit = h('button', { type: 'submit', class: 'cqa-btn cqa-btn--primary' }, t.review.submit);
  const status = h('div', { class: 'cqa-status', role: 'status' });

  const setInvalid = (invalid: boolean) => {
    if (invalid) {
      reason.setAttribute('aria-invalid', 'true');
      reason.setAttribute('aria-describedby', reasonErrorId);
    } else {
      reason.removeAttribute('aria-invalid');
      reason.removeAttribute('aria-describedby');
    }
  };
  const setBusy = (on: boolean) => {
    busy = on;
    submit.disabled = on;
    submit.textContent = on ? t.review.saving : t.review.submit;
    if (on) submit.setAttribute('aria-busy', 'true');
    else submit.removeAttribute('aria-busy');
  };
  reason.addEventListener('input', () => {
    if (reason.getAttribute('aria-invalid') === 'true' && reason.value.trim()) {
      errors.replaceChildren();
      setInvalid(false);
    }
  });

  const radio = (value: 'confirm' | 'change', label: string) =>
    h(
      'label',
      { class: 'cqa-radio' },
      h('input', {
        type: 'radio',
        name: `action-${appeal.id}`,
        value,
        checked: value === 'confirm',
        onchange: () => {
          action.confirm = value === 'confirm';
          verdictField.hidden = action.confirm;
        },
      }),
      h('span', null, label),
    );

  const stateBadge = badge(t.review.open, 'warn');

  const form = h(
    'form',
    {
      class: 'cqa-form cqa-decision',
      novalidate: true,
      'aria-labelledby': `${base}-decision`,
      onsubmit: async (e: Event) => {
        e.preventDefault();
        if (busy) return;
        errors.replaceChildren();
        if (!reason.value.trim()) {
          errors.appendChild(banner(t.common.reasonRequired));
          setInvalid(true);
          reason.focus();
          return;
        }
        setInvalid(false);
        setBusy(true);
        try {
          const result = await ctx.api.decide(appeal.id, {
            action: action.confirm ? 'confirm' : 'change',
            new_verdict: action.confirm ? null : newVerdict.value,
            reason: reason.value.trim(),
          });
          const before = loaded.view?.evaluation.score.total;
          const summary = h(
            'div',
            { class: 'cqa-banner cqa-banner--ok cqa-appeal-result', tabindex: '-1' },
            h('strong', null, t.review.decided),
            h('p', null, action.confirm ? t.review.decidedConfirm : t.review.decidedChange(verdictLabel(newVerdict.value))),
            h(
              'p',
              { class: 'cqa-appeal-total' },
              before === undefined ? fmt(result.final.score.total) : t.review.totalChange(fmt(before), fmt(result.final.score.total)),
            ),
            h('a', { class: 'cqa-link', href: dialogHref }, t.review.backToDialog),
          );
          status.replaceChildren(summary);
          form.remove();
          el.classList.add('is-resolved');
          stateBadge.className = 'cqa-badge cqa-badge--good';
          stateBadge.textContent = t.review.resolved;
          summary.focus();
          onResolved();
        } catch (err) {
          setBusy(false);
          errors.replaceChildren(banner(errorMessage(err), errorDetails(err)));
        }
      },
    },
    h('h3', { id: `${base}-decision` }, t.review.decision),
    h('fieldset', { class: 'cqa-radios', 'aria-labelledby': `${base}-decision` }, radio('confirm', t.review.confirm), radio('change', t.review.change)),
    verdictField,
    h('label', { class: 'cqa-field', for: reason.id }, h('span', { class: 'cqa-field-label' }, t.review.reason), reason),
    errors,
    h('div', { class: 'cqa-decision-actions' }, submit),
  );

  // Порядок DOM = порядок чтения: критерий → пояснение/комментарий → фрагмент → решение.
  const el = h(
    'article',
    { class: 'cqa-card cqa-appeal', 'data-appeal': appeal.id, 'aria-labelledby': titleId },
    h(
      'header',
      { class: 'cqa-appeal-head' },
      h('h2', { id: titleId, class: 'cqa-appeal-title' }, `${criterion.id} · ${criterion.title}`),
      stateBadge,
      h('a', { class: 'cqa-link cqa-appeal-dialog', href: dialogHref }, `${q.conversation_id} — ${t.review.openDialog}`),
    ),
    h(
      'div',
      { class: evidence ? 'cqa-appeal-cols' : 'cqa-appeal-cols cqa-appeal-cols--single' },
      context,
      evidence,
      h('div', { class: 'cqa-appeal-decision' }, status, form),
    ),
  );
  return el;
}

export async function render(root: HTMLElement, ctx: Ctx): Promise<void> {
  const queue = await ctx.api.appeals('open');
  if (ctx.signal.aborted) return;
  const views = new Map<string, Promise<Loaded>>();
  const loaded = await Promise.all(queue.map((q) => loadFor(ctx, q, views)));
  if (ctx.signal.aborted) return;

  const title = h('h1', { class: 'cqa-page-title' }, t.review.title);
  if (!queue.length) {
    root.replaceChildren(
      h('div', { class: 'cqa-page-head' }, h('div', null, title)),
      h(
        'section',
        { class: 'cqa-card cqa-review-empty', 'aria-labelledby': 'cqa-review-empty-title' },
        h('h2', { id: 'cqa-review-empty-title' }, t.review.empty),
        h('p', { class: 'cqa-muted' }, t.review.emptyHint),
        h('a', { class: 'cqa-btn', href: hrefDialogs(DEFAULT_GROUP) }, t.review.toDialogs),
      ),
    );
    return;
  }

  let open = queue.length;
  const count = h('p', { class: 'cqa-page-subtitle' }, t.review.count(open));
  const onResolved = () => {
    open -= 1;
    count.textContent = t.review.count(open);
    void stats.refresh();
  };
  const cards = queue.map((q, i) => card(ctx, q, loaded[i], onResolved));
  const list = h('div', { class: 'cqa-appeals' }, cards);

  // Подтверждения (issue #44): отдельно от апелляций, на итог не влияют.
  const reviewer = reviewerInput();
  const stats = statsLine(ctx);
  const accepts = queue.map((q, i) => {
    const a = acceptButton(ctx, q.evaluation_id, () => reviewer.value.trim(), () => void stats.refresh());
    cards[i].querySelector('.cqa-appeal-head')?.appendChild(a.el);
    return a;
  });
  const strip = h(
    'div',
    { class: 'cqa-review-strip' },
    h('label', { class: 'cqa-inline' }, h('span', null, t.confirm.reviewer), reviewer),
    stats.el,
    h('p', { class: 'cqa-muted cqa-keys-hint' }, t.confirm.keysHint),
  );

  let focused = -1;
  const focus = (i: number) => {
    focused = Math.max(0, Math.min(cards.length - 1, i));
    cards.forEach((c, n) => c.classList.toggle('is-focused', n === focused));
    cards[focused].scrollIntoView({ block: 'nearest' });
  };
  const onKey = (e: KeyboardEvent) => {
    const el = e.target as HTMLElement | null;
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    if (el && (el.isContentEditable || ['INPUT', 'TEXTAREA', 'SELECT'].includes(el.tagName))) return;
    if (e.key === 'j') focus(focused + 1);
    else if (e.key === 'k') focus(focused < 0 ? 0 : focused - 1);
    else if (e.key === 'a' && focused >= 0) accepts[focused].run();
    else if (e.key === 'o' && focused >= 0) cards[focused].querySelector<HTMLElement>('.cqa-appeal-decision input, .cqa-appeal-decision textarea')?.focus();
    else return;
    e.preventDefault();
  };
  document.addEventListener('keydown', onKey);
  ctx.signal.addEventListener('abort', () => document.removeEventListener('keydown', onKey));

  root.replaceChildren(h('div', { class: 'cqa-page-head' }, h('div', null, title, count)), strip, list);
}
