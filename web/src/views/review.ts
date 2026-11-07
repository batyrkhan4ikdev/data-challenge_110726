import { t } from '../i18n.js';
import { hrefEvaluation } from '../router.js';
import type { Ctx } from '../router.js';
import type { AppealQueueItem, EvaluationView, Record as DialogRecord } from '../types.gen.js';
import { allowedVerdicts, badge, banner, errorDetails, errorMessage, fmt, h, heading, rangeOf, verdictLabel, verdictTone } from '../ui/dom.js';
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
  const status = h('div', { class: 'cqa-status' });
  const allowed = allowedVerdicts(criterion);

  let fragment: HTMLElement | null = null;
  if (loaded.record) {
    const range = fragmentRange(item, loaded.record.transcript.length);
    const tr = renderTranscript(loaded.record, { range, audio: false });
    tr.highlight(item.evidence_idx, item.verdict === 'no' ? rangeOf(item.expected_range) : null);
    fragment = h('div', { class: 'cqa-fragment' }, h('h3', null, t.review.fragment), tr.el);
  }

  const action = { confirm: true };
  const newVerdict = h(
    'select',
    { class: 'cqa-input', 'aria-label': t.review.newVerdict },
    allowed.map((v) => h('option', { value: v }, verdictLabel(v))),
  );
  newVerdict.hidden = true;
  const reason = h('textarea', {
    class: 'cqa-input cqa-textarea',
    rows: 2,
    required: true,
    placeholder: t.review.reasonPlaceholder,
    'aria-label': t.review.reason,
  });
  const submit = h('button', { type: 'submit', class: 'cqa-btn cqa-btn--primary' }, t.review.submit);

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
          newVerdict.hidden = action.confirm;
        },
      }),
      h('span', null, label),
    );

  const form = h(
    'form',
    {
      class: 'cqa-form cqa-decision',
      novalidate: true,
      onsubmit: async (e: Event) => {
        e.preventDefault();
        status.replaceChildren();
        if (!reason.value.trim()) {
          status.appendChild(banner(t.common.reasonRequired));
          reason.focus();
          return;
        }
        submit.disabled = true;
        try {
          const result = await ctx.api.decide(appeal.id, {
            action: action.confirm ? 'confirm' : 'change',
            new_verdict: action.confirm ? null : newVerdict.value,
            reason: reason.value.trim(),
          });
          const before = loaded.view?.evaluation.score.total;
          status.replaceChildren(
            banner(
              t.review.decided,
              [before === undefined ? fmt(result.final.score.total) : t.review.totalChange(fmt(before), fmt(result.final.score.total))],
              'ok',
            ),
          );
          form.hidden = true;
          el.classList.add('is-resolved');
          onResolved();
        } catch (err) {
          status.replaceChildren(banner(errorMessage(err), errorDetails(err)));
          submit.disabled = false;
        }
      },
    },
    h('h3', null, t.review.decision),
    h('div', { class: 'cqa-radios' }, radio('confirm', t.review.confirm), radio('change', t.review.change), newVerdict),
    h('label', { class: 'cqa-field' }, h('span', { class: 'cqa-field-label' }, t.review.reason), reason),
    submit,
  );

  const el = h(
    'article',
    { class: 'cqa-card cqa-appeal', 'data-appeal': appeal.id },
    h(
      'div',
      { class: 'cqa-appeal-head' },
      h('strong', null, `${criterion.id} · ${criterion.title}`),
      h('a', { class: 'cqa-link', href: hrefEvaluation(q.evaluation_id) }, `${q.conversation_id} — ${t.review.openDialog}`),
    ),
    h(
      'div',
      { class: 'cqa-appeal-cols' },
      h(
        'div',
        null,
        h('p', null, h('span', { class: 'cqa-muted' }, `${t.review.original}: `), badge(verdictLabel(item.verdict), verdictTone(criterion, item.verdict))),
        h('p', null, h('span', { class: 'cqa-muted' }, `${t.review.explanation}: `), item.explanation),
        h('p', { class: 'cqa-appeal-comment' }, h('span', { class: 'cqa-muted' }, `${t.review.comment}: `), appeal.comment),
        status,
        form,
      ),
      fragment,
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

  let open = queue.length;
  const count = h('span', { class: 'cqa-muted' }, t.review.count(open));
  const list = h('div', { class: 'cqa-appeals' });
  const empty = h('p', { class: 'cqa-muted cqa-empty' }, t.review.empty);
  empty.hidden = open > 0;

  const onResolved = () => {
    open -= 1;
    count.textContent = t.review.count(open);
    empty.hidden = open > 0;
  };
  list.append(...queue.map((q, i) => card(ctx, q, loaded[i], onResolved)));
  root.replaceChildren(heading(t.review.title, count), list, empty);
}
