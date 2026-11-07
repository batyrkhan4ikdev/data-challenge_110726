import { t } from '../i18n.js';
import { hrefDialogs, hrefEvaluation } from '../router.js';
import type { Ctx } from '../router.js';
import type { BatchRequest, EvaluationSummary, EvaluationView, RawCall, Record as DialogRecord } from '../types.gen.js';
import { openAppealModal } from '../ui/appeal-modal.js';
import { renderCriteriaTable } from '../ui/criteria-table.js';
import { badge, banner, errorDetails, errorMessage, fmt, fmtDate, h, heading } from '../ui/dom.js';
import { renderTranscript } from '../ui/transcript.js';

/** Красный бейдж «Грубая ошибка»: по клику прокручивает к критерию с грубой ошибкой (пояснение и подтверждения). */
function grossBadge(view: EvaluationView): HTMLElement {
  const ids = view.checklist.criteria
    .filter((c) => c.kind === 'gross_error' && view.final.items.find((f) => f.criterion_id === c.id)?.final_verdict === 'yes')
    .map((c) => c.id);
  const btn = h('button', { type: 'button', class: 'cqa-badge cqa-badge--bad cqa-badge-btn', title: t.result.grossJump }, t.result.grossBadge);
  btn.addEventListener('click', () => {
    const scope = btn.closest('.cqa-view');
    const rowEls = ids.map((id) => scope?.querySelector<HTMLElement>(`tr[data-criterion="${CSS.escape(id)}"]`) ?? null);
    rowEls.find((r) => r !== null)?.scrollIntoView({ block: 'center', behavior: 'smooth' });
    for (const r of rowEls) {
      if (!r) continue;
      r.classList.remove('is-flash');
      void r.offsetWidth;
      r.classList.add('is-flash');
    }
  });
  return btn;
}

function summaryTotal(s: EvaluationSummary): HTMLElement {
  const changed = s.final_total !== s.total;
  return h('span', null, fmt(s.total), changed ? ` → ${fmt(s.final_total)}` : '');
}

function rawPanel(calls: RawCall[]): HTMLElement {
  if (!calls.length) return h('p', { class: 'cqa-muted' }, t.result.rawEmpty);
  return h(
    'div',
    { class: 'cqa-raw' },
    calls.map((call, i) =>
      h(
        'details',
        { class: 'cqa-raw-call', open: i === 0 },
        h(
          'summary',
          null,
          `#${i + 1} · ${call.model} · ${fmt(call.seconds)} ${t.result.seconds} · ${call.criterion_ids.join(', ')}`,
        ),
        h('h3', null, t.result.rawMessages),
        call.messages.map((m) =>
          h(
            'div',
            { class: 'cqa-raw-message' },
            h('span', { class: 'cqa-badge cqa-badge--info' }, String(m.role ?? '')),
            h('pre', null, typeof m.content === 'string' ? m.content : JSON.stringify(m.content, null, 2)),
          ),
        ),
        h('h3', null, t.result.rawResponse),
        h('pre', { class: 'cqa-raw-response' }, call.response_text),
      ),
    ),
  );
}

/** Запускает переоценку и переходит к новой оценке; ошибки показывает в `status`. */
async function runAndOpen(
  ctx: Ctx,
  req: BatchRequest,
  status: HTMLElement,
  setBusy: (busy: boolean) => void,
): Promise<void> {
  const cid = req.conversation_ids[0];
  setBusy(true);
  status.replaceChildren(h('span', { class: 'cqa-muted' }, t.result.reevaluating));
  try {
    const job = await ctx.api.runBatch(req, (j) => status.replaceChildren(h('span', { class: 'cqa-muted' }, `${t.result.reevaluating} ${j.done}/${j.total}`)), ctx.signal);
    if (ctx.signal.aborted) return;
    const failure = job.failed[cid];
    const evalId = job.evaluation_ids[job.evaluation_ids.length - 1];
    if (failure || !evalId) {
      status.replaceChildren(banner(t.result.reevaluateFailed, failure ? [failure] : null));
      setBusy(false);
      return;
    }
    ctx.navigate(hrefEvaluation(evalId));
  } catch (e) {
    status.replaceChildren(banner(errorMessage(e), errorDetails(e)));
    setBusy(false);
  }
}

function header(view: EvaluationView, ctx: Ctx, record: DialogRecord | null, rawToggle: HTMLElement): HTMLElement {
  const { evaluation: ev, final, checklist } = view;
  const original = ev.score.total;
  const finalTotal = final.score.total;
  const totalText =
    finalTotal === null && original === null
      ? t.result.notCalculated
      : original !== finalTotal
        ? `${fmt(original)} → ${fmt(finalTotal)}`
        : fmt(finalTotal);

  const status = h('div', { class: 'cqa-status' });
  const reBtn = h(
    'button',
    { type: 'button', class: 'cqa-btn cqa-btn--primary', id: 'cqa-reevaluate' },
    t.result.reevaluate,
  );
  reBtn.addEventListener('click', () =>
    void runAndOpen(
      ctx,
      {
        group_id: ev.group_id,
        conversation_ids: [ev.conversation_id],
        checklist_id: ev.checklist_id,
        profile: ev.profile,
        mode: ev.mode,
        k: ev.k,
      },
      status,
      (busy) => (reBtn.disabled = busy),
    ),
  );

  return h(
    'div',
    { class: 'cqa-card cqa-result-header' },
    h(
      'div',
      { class: 'cqa-result-title' },
      h('a', { class: 'cqa-link', href: hrefDialogs(ev.group_id), 'aria-label': t.nav.dialogs }, `← ${ev.group_id}`),
      h('h1', null, ev.conversation_id),
      record ? badge(t.channel[record.channel] ?? record.channel, 'neutral') : null,
      record ? badge(record.language, 'neutral') : null,
      final.score.gross_error ? grossBadge(view) : null,
    ),
    h(
      'div',
      { class: 'cqa-result-total' },
      h('span', { class: 'cqa-muted' }, `${t.result.total}: `),
      h('strong', { class: finalTotal === null ? 'cqa-total cqa-total--none' : 'cqa-total', title: original !== finalTotal ? `${t.review.totalChange(fmt(original), fmt(finalTotal))}` : undefined }, totalText),
      finalTotal === null && original === null ? null : h('span', { class: 'cqa-muted' }, ' / 100'),
    ),
    h(
      'div',
      { class: 'cqa-sections-totals' },
      h('span', { class: 'cqa-muted' }, `${t.result.sections}: `),
      final.score.sections.map((s) => h('span', { class: 'cqa-chip', title: s.title }, `${s.title}: `, h('strong', null, fmt(s.total)))),
    ),
    h(
      'dl',
      { class: 'cqa-meta' },
      h('div', null, h('dt', null, t.result.checklist), h('dd', null, `${checklist.name} · v${ev.checklist_version}`)),
      h('div', null, h('dt', null, t.result.profile), h('dd', null, ev.profile)),
      h('div', null, h('dt', null, t.result.model), h('dd', null, ev.model)),
      h('div', null, h('dt', null, `${t.result.mode} / ${t.result.k}`), h('dd', null, `${ev.mode} / ${ev.k}`)),
      h(
        'div',
        null,
        h('dt', null, t.result.usage),
        h('dd', null, `${ev.usage.prompt_tokens + ev.usage.completion_tokens} ${t.result.tokens} · ${ev.usage.calls} ${t.result.calls} · ${fmt(ev.usage.seconds)} ${t.result.seconds}`),
      ),
      h('div', null, h('dt', null, t.result.created), h('dd', null, fmtDate(ev.created_at))),
    ),
    h('div', { class: 'cqa-result-actions' }, reBtn, rawToggle, status),
  );
}

export async function render(root: HTMLElement, ctx: Ctx): Promise<void> {
  const view = await ctx.api.evaluation(ctx.params.id);
  if (ctx.signal.aborted) return;
  const ev = view.evaluation;

  const [recordResult, history] = await Promise.all([
    ctx.api.record(ev.group_id, ev.conversation_id).then(
      (r) => ({ ok: true as const, record: r }),
      (e: unknown) => ({ ok: false as const, error: e }),
    ),
    ctx.api.evaluationsFor(ev.conversation_id).catch(() => [] as EvaluationSummary[]),
  ]);
  if (ctx.signal.aborted) return;
  const record = recordResult.ok ? recordResult.record : null;

  const transcript = record ? renderTranscript(record, { ids: true }) : null;
  const left = h(
    'aside',
    { class: 'cqa-pane cqa-pane--transcript', 'aria-label': t.result.transcript },
    transcript
      ? transcript.el
      : banner(t.result.transcriptMissing, recordResult.ok ? null : [errorMessage(recordResult.error)]),
  );

  const table = renderCriteriaTable({
    view,
    onEvidence: (idx) => transcript?.focusEvidence(idx),
    onExpected: (range) => transcript?.focusExpected(range),
    onAppeal: (criterion) =>
      openAppealModal(root, {
        api: ctx.api,
        evaluationId: ev.id,
        criterion,
        onSent: () => void render(root, ctx),
      }),
  });

  // Панель «Вызовы модели»: загружается при первом открытии.
  const rawBody = h('div', { class: 'cqa-card cqa-raw-panel' });
  rawBody.hidden = true;
  let rawLoaded = false;
  const rawToggle = h('button', { type: 'button', class: 'cqa-btn', 'aria-expanded': 'false', id: 'cqa-raw-toggle' }, t.result.rawCalls);
  rawToggle.addEventListener('click', async () => {
    rawBody.hidden = !rawBody.hidden;
    rawToggle.textContent = rawBody.hidden ? t.result.rawCalls : t.result.rawHide;
    rawToggle.setAttribute('aria-expanded', String(!rawBody.hidden));
    if (!rawBody.hidden && !rawLoaded) {
      rawBody.replaceChildren(h('span', { class: 'cqa-muted' }, t.common.loading));
      try {
        rawBody.replaceChildren(rawPanel(await ctx.api.raw(ev.id)));
        rawLoaded = true;
      } catch (e) {
        rawBody.replaceChildren(banner(errorMessage(e), errorDetails(e)));
      }
    }
  });

  const historyEl = h(
    'div',
    { class: 'cqa-history' },
    h('span', { class: 'cqa-muted' }, `${t.result.history}: `),
    history.map((s) =>
      h(
        'a',
        { class: `cqa-chip cqa-history-item${s.id === ev.id ? ' is-current' : ''}`, href: hrefEvaluation(s.id), 'aria-current': s.id === ev.id ? 'true' : null },
        `${s.checklist_id} v${s.checklist_version} · `,
        summaryTotal(s),
        s.gross_error ? ' ⚠' : '',
        h('span', { class: 'cqa-muted' }, ` · ${fmtDate(s.created_at)}`),
      ),
    ),
  );

  root.replaceChildren(
    header(view, ctx, record, rawToggle),
    rawBody,
    historyEl,
    h('div', { class: 'cqa-split' }, left, h('div', { class: 'cqa-pane cqa-pane--criteria' }, table)),
  );
}

/** Диалог без оценок: только транскрипт и кнопка «Оценить». */
export async function renderTranscriptOnly(root: HTMLElement, ctx: Ctx): Promise<void> {
  const { group, cid } = ctx.params;
  const record = await ctx.api.record(group, cid);
  if (ctx.signal.aborted) return;
  const transcript = renderTranscript(record, { ids: true });
  const status = h('div', { class: 'cqa-status' });
  const btn = h('button', { type: 'button', class: 'cqa-btn cqa-btn--primary' }, t.dialogs.evaluateOne);
  btn.addEventListener('click', () =>
    void runAndOpen(ctx, { group_id: group, conversation_ids: [cid], checklist_id: null }, status, (busy) => (btn.disabled = busy)),
  );
  root.replaceChildren(
    heading(cid, badge(t.channel[record.channel] ?? record.channel), badge(record.language), btn, h('a', { class: 'cqa-link', href: hrefDialogs(group) }, `← ${group}`)),
    banner(t.dialogs.transcriptOnly, null, 'info'),
    status,
    h('div', { class: 'cqa-card cqa-transcript-only' }, transcript.el),
  );
}
