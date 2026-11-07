import type { CriterionReliability } from '../api.js';
import { t } from '../i18n.js';
import { hrefDialogs, hrefEvaluation } from '../router.js';
import type { Ctx } from '../router.js';
import type { BatchRequest, Criterion, EvaluationSummary, EvaluationView, RawCall, Record as DialogRecord } from '../types.gen.js';
import { diffPanel } from '../ui/evalDiff.js';
import { mountConfirmPanel } from '../ui/confirmPanel.js';
import { openAppealModal } from '../ui/appealModal.js';
import { renderCriteriaTable } from '../ui/criteriaTable.js';
import { badge, banner, errorDetails, errorMessage, fmt, fmtDate, h, heading, rangeOf } from '../ui/dom.js';
import { factsCard } from '../ui/facts.js';
import { checkIcon, crossIcon, scoreRing } from '../ui/icons.js';
import { renderTranscript } from '../ui/transcript.js';
import type { TranscriptView } from '../ui/transcript.js';
import { API_SOURCE, createTranscriptPanel, defaultSource, loadSources, sourceLabel } from '../ui/transcriptPanel.js';

/** Красный бейдж «Грубая ошибка»: по клику прокручивает к критерию с грубой ошибкой (пояснение и подтверждения). */
function grossBadge(view: EvaluationView): HTMLElement {
  const ids = view.checklist.criteria
    .filter((c) => c.kind === 'gross_error' && view.final.items.find((f) => f.criterion_id === c.id)?.final_verdict === 'yes')
    .map((c) => c.id);
  const btn = h('button', { type: 'button', class: 'cqa-badge cqa-badge--bad cqa-badge-btn', title: t.result.grossJump }, t.result.grossBadge);
  btn.addEventListener('click', () => {
    const scope = btn.closest('.cqa-view');
    const details = scope?.querySelector<HTMLDetailsElement>('.cqa-details');
    if (details) details.open = true;
    const rowEls = ids.map((id) => scope?.querySelector<HTMLElement>(`tr[data-criterion="${CSS.escape(id)}"]`) ?? null);
    const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
    rowEls.find((r) => r !== null)?.scrollIntoView({ block: 'center', behavior: reduced ? 'auto' : 'smooth' });
    for (const r of rowEls) {
      if (!r || reduced) continue;
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

const band = (total: number | null): 'good' | 'warn' | 'bad' | 'none' =>
  total === null ? 'none' : total >= 85 ? 'good' : total >= 70 ? 'warn' : 'bad';

function durationOf(record: DialogRecord | null): string | null {
  if (!record || record.channel !== 'voice call') return null;
  const last = [...record.transcript].reverse().find((x) => x.offset_s !== null && x.offset_s !== undefined);
  if (!last || last.offset_s === null || last.offset_s === undefined) return null;
  const sec = Math.round(last.offset_s);
  return `${String(Math.floor(sec / 60)).padStart(2, '0')}:${String(sec % 60).padStart(2, '0')}`;
}

/** «Выгрузить дело»: скачивает RegPack (ZIP) по этой оценке. */
function regpackButton(ctx: Ctx, group: string, cid: string, evaluationId: string, status: HTMLElement): HTMLElement {
  const btn = h('button', { type: 'button', class: 'cqa-btn', id: 'cqa-regpack' }, t.caseTools.regpack);
  btn.addEventListener('click', async () => {
    btn.disabled = true;
    btn.textContent = t.caseTools.regpackBusy;
    try {
      const { blob, name, selfcheckOk } = await ctx.api.regpack(group, cid, evaluationId);
      const url = URL.createObjectURL(blob);
      const a = h('a', { href: url, download: name });
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 10_000);
      status.replaceChildren(selfcheckOk ? banner(t.caseTools.regpackOk, null, 'ok') : banner(t.caseTools.regpackMismatch));
    } catch (e) {
      status.replaceChildren(banner(`${t.caseTools.regpackFail}: ${errorMessage(e)}`, errorDetails(e)));
    } finally {
      btn.disabled = false;
      btn.textContent = t.caseTools.regpack;
    }
  });
  return btn;
}

function pageHeader(
  view: EvaluationView,
  ctx: Ctx,
  record: DialogRecord | null,
  status: HTMLElement,
  transcriptLabel: string | null,
): HTMLElement {
  const ev = view.evaluation;
  const reBtn = h('button', { type: 'button', class: 'cqa-btn cqa-btn--primary', id: 'cqa-reevaluate' }, t.result.reevaluate);
  const source = ev.transcript_source ?? API_SOURCE;
  reBtn.addEventListener('click', () => {
    const req: BatchRequest = {
      group_id: ev.group_id,
      conversation_ids: [ev.conversation_id],
      checklist_id: ev.checklist_id,
      profile: ev.profile,
      mode: ev.mode,
      k: ev.k,
      transcript_source: source === API_SOURCE ? null : source,
    };
    void runAndOpen(ctx, req, status, (busy) => {
      reBtn.disabled = busy;
      reBtn.textContent = busy ? t.result.reevaluating : t.result.reevaluate;
      reBtn.setAttribute('aria-busy', String(busy));
    });
  });
  const subtitle = [ev.conversation_id, record ? (t.channel[record.channel] ?? record.channel) : null, record?.language, durationOf(record)]
    .filter((x): x is string => !!x)
    .join(' · ');
  return h(
    'div',
    { class: 'cqa-page-head' },
    h(
      'div',
      null,
      h('a', { class: 'cqa-link cqa-back', href: hrefDialogs(ev.group_id), 'aria-label': t.nav.dialogs }, `← ${ev.group_id}`),
      h('h1', { class: 'cqa-page-title' }, t.result.title),
      h(
        'p',
        { class: 'cqa-page-subtitle' },
        subtitle,
        transcriptLabel ? [' · ', h('span', { class: 'cqa-tsrc-used', id: 'cqa-transcript-used' }, `${t.transcripts.header}: ${transcriptLabel}`)] : null,
      ),
    ),
    h('div', { class: 'cqa-page-actions' }, reBtn, regpackButton(ctx, ev.group_id, ev.conversation_id, ev.id, status), status),
  );
}

interface ScoreCardOptions {
  view: EvaluationView;
  onJump: (c: Criterion) => void;
  onAppeal: (c: Criterion) => void;
}

function scoreCard(opts: ScoreCardOptions): HTMLElement {
  const { view } = opts;
  const { evaluation: ev, final, checklist, appeals } = view;
  const original = ev.score.total;
  const total = final.score.total;
  const tone = band(total);
  const items = new Map(ev.items.map((i) => [i.criterion_id, i]));
  const finals = new Map(final.items.map((f) => [f.criterion_id, f]));
  const scores = new Map(final.score.items.map((s) => [s.criterion_id, s]));

  const rows: HTMLElement[] = [];
  const lost: { c: Criterion; text: string }[] = [];
  for (const c of checklist.criteria) {
    const sc = scores.get(c.id);
    const it = items.get(c.id);
    const fin = finals.get(c.id);
    let icon: HTMLElement;
    let pts: HTMLElement | string;
    let state: 'ok' | 'part' | 'fail' | 'na';
    if (c.kind === 'gross_error') {
      const found = (fin?.final_verdict ?? it?.verdict) === 'yes';
      state = found ? 'fail' : 'ok';
      pts = found ? t.result.grossBadge : t.common.none;
      if (found) lost.push({ c, text: it?.explanation ?? '' });
    } else if (!sc || !sc.applicable || sc.points === null) {
      state = 'na';
      pts = t.common.na;
    } else {
      const full = sc.points >= sc.max_points;
      state = full ? 'ok' : sc.points > 0 ? 'part' : 'fail';
      pts = h('span', null, h('strong', { class: `cqa-pts cqa-pts--${state}` }, fmt(sc.points)), ` / ${fmt(sc.max_points)}`);
      if (!full) lost.push({ c, text: it?.explanation ?? '' });
    }
    icon = h('span', { class: `cqa-mark cqa-mark--${state}` }, state === 'ok' ? checkIcon() : state === 'na' ? 'N/A' : crossIcon());
    rows.push(h('li', { class: 'cqa-score-row', 'data-criterion': c.id }, icon, h('span', { class: 'cqa-score-title' }, c.title), h('span', { class: 'cqa-score-pts' }, pts)));
  }

  const why = lost.length
    ? lost.map(({ c, text }) => {
        const it = items.get(c.id);
        const hasFragment = !!it && (it.evidence_idx.length > 0 || (it.verdict === 'no' && rangeOf(it.expected_range) !== null));
        const hasOpen = appeals.some((a) => a.criterion_id === c.id && a.status === 'open');
        return h(
          'li',
          { class: 'cqa-why-row', 'data-criterion': c.id },
          h('div', { class: 'cqa-why-text' }, h('strong', null, c.title), h('span', { class: 'cqa-why-expl' }, text)),
          h(
            'div',
            { class: 'cqa-why-actions' },
            h('button', { type: 'button', class: 'cqa-btn cqa-btn--tint cqa-btn--small cqa-jump', disabled: !hasFragment, 'data-has-fragment': String(hasFragment), onclick: () => opts.onJump(c) }, t.result.jumpToFragment),
            !hasFragment ? h('span', { class: 'cqa-muted cqa-no-fragment' }, t.result.noFragment) : null,
            hasOpen
              ? badge(t.result.appealOpen, 'warn')
              : h('button', { type: 'button', class: 'cqa-btn cqa-btn--small', onclick: () => opts.onAppeal(c) }, t.result.appealButton),
          ),
        );
      })
    : [h('li', { class: 'cqa-muted' }, t.result.whyNone)];

  return h(
    'section',
    { class: 'cqa-card cqa-score-card', 'aria-label': t.result.scoreTitle },
    h('h2', { class: 'cqa-card-title' }, t.result.scoreTitle),
    h(
      'div',
      { class: 'cqa-score-top' },
      h(
        'div',
        { class: `cqa-ring cqa-ring--${tone}` },
        total === null ? h('span', { class: 'cqa-total cqa-total--none' }, t.result.notCalculated) : scoreRing(total, fmt(total), '/ 100'),
        original !== total ? h('div', { class: 'cqa-muted cqa-ring-was', title: t.review.totalChange(fmt(original), fmt(total)) }, `${t.result.originalTotal}: ${fmt(original)}`) : null,
        final.score.gross_error ? grossBadge(view) : null,
      ),
      h('ul', { class: 'cqa-score-rows' }, rows),
    ),
    h('h3', { class: 'cqa-why-title' }, t.result.whyTitle),
    h('ul', { class: 'cqa-why' }, why),
  );
}

function detailsBlock(
  view: EvaluationView,
  record: DialogRecord | null,
  history: EvaluationSummary[],
  rawToggle: HTMLElement,
  rawBody: HTMLElement,
  table: HTMLElement,
  transcriptLabel: string | null,
  diff: HTMLElement,
): HTMLElement {
  const { evaluation: ev, final, checklist } = view;
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
  return h(
    'details',
    { class: 'cqa-card cqa-details', open: false },
    h('summary', null, t.result.details),
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
      record ? h('div', null, h('dt', null, t.dialogs.channel), h('dd', null, `${t.channel[record.channel] ?? record.channel} · ${record.language}`)) : null,
      transcriptLabel ? h('div', null, h('dt', null, t.transcripts.header), h('dd', null, transcriptLabel)) : null,
    ),
    historyEl,
    diff,
    h('div', { class: 'cqa-result-actions' }, rawToggle),
    rawBody,
    h('h3', null, t.result.detailsTable),
    h('div', { class: 'cqa-table-wrap', tabindex: '0', role: 'region', 'aria-label': t.result.detailsTable }, table),
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

  const evSource = ev.transcript_source ?? API_SOURCE;
  const isCall = record?.channel === 'voice call';
  const sources = isCall ? await loadSources(ctx.api, ev.conversation_id) : [];
  if (ctx.signal.aborted) return;
  const panel =
    record && isCall
      ? createTranscriptPanel({
          api: ctx.api,
          host: root,
          signal: ctx.signal,
          group: ev.group_id,
          cid: ev.conversation_id,
          sources,
          initial: evSource,
          evaluated: evSource,
          onEvaluate: (source, panelStatus, setBusy) =>
            void runAndOpen(
              ctx,
              {
                group_id: ev.group_id,
                conversation_ids: [ev.conversation_id],
                checklist_id: ev.checklist_id,
                transcript_source: source === API_SOURCE ? null : source,
              },
              panelStatus,
              setBusy,
            ),
        })
      : null;
  const transcript: TranscriptView | null = record && !panel ? renderTranscript(record, { ids: true }) : null;
  const focusEvidence = (idx: number) => void (panel ? panel.focusEvidence(idx) : transcript?.focusEvidence(idx));
  const focusExpected = (range: [number, number]) => void (panel ? panel.focusExpected(range) : transcript?.focusExpected(range));
  const left = h(
    'section',
    { class: 'cqa-card cqa-pane--transcript', 'aria-label': t.result.transcript },
    h('h2', { class: 'cqa-card-title' }, t.result.transcript),
    panel
      ? panel.el
      : transcript
        ? transcript.el
        : banner(t.result.transcriptMissing, recordResult.ok ? null : [errorMessage(recordResult.error)]),
  );
  if (record) {
    left.appendChild(factsCard(ctx.api.facts(ev.group_id, ev.conversation_id, isCall ? evSource : undefined), focusEvidence));
  }

  const appeal = (criterion: Criterion) =>
    openAppealModal(root, {
      api: ctx.api,
      evaluationId: ev.id,
      criterion,
      onSent: () => void render(root, ctx),
    });
  const jump = (c: Criterion) => {
    const it = ev.items.find((i) => i.criterion_id === c.id);
    if (!it) return;
    const first = it.evidence_idx[0];
    const range = it.verdict === 'no' ? rangeOf(it.expected_range) : null;
    if (first !== undefined) focusEvidence(first);
    else if (range) focusExpected(range);
  };
  const reliability: CriterionReliability | null = await ctx.api.criterionReliability().catch(() => null);
  if (ctx.signal.aborted) return;
  const table = renderCriteriaTable({
    view,
    reliability,
    onEvidence: focusEvidence,
    onExpected: focusExpected,
    onAppeal: appeal,
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

  const status = h('div', { class: 'cqa-status', role: 'status' });
  const score = scoreCard({ view, onJump: jump, onAppeal: appeal });
  const transcriptLabel = isCall ? sourceLabel(sources, evSource) : null;
  const header = pageHeader(view, ctx, record, status, transcriptLabel);
  if (isCall) {
    // The call's audio lives in the transcript panel and is re-rendered on a source switch: resolve it at click time.
    const link = h('a', { class: 'cqa-link cqa-audio-jump', href: '#cqa-call-audio' }, t.result.audioJump);
    link.addEventListener('click', (event) => {
      const audio = root.querySelector<HTMLAudioElement>('#cqa-call-audio');
      if (!audio) return;
      event.preventDefault();
      audio.focus({ preventScroll: true });
      audio.scrollIntoView({ block: 'center', behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
    });
    header.appendChild(link);
  }
  const confirmPanel = await mountConfirmPanel(ctx, view);
  root.replaceChildren(header,
    h('div', { class: 'cqa-split' }, score, left),
    confirmPanel,
    detailsBlock(view, record, history, rawToggle, rawBody, table, transcriptLabel, diffPanel(ctx.api, history, ev.id)));
}

/** Диалог без оценок: только транскрипт и кнопка «Оценить». Оценённый диалог открывает последнюю оценку. */
export async function renderTranscriptOnly(root: HTMLElement, ctx: Ctx): Promise<void> {
  const { group, cid } = ctx.params;
  const [record, evaluations] = await Promise.all([ctx.api.record(group, cid), ctx.api.evaluationsFor(cid)]);
  if (ctx.signal.aborted) return;
  const latest = evaluations.reduce<EvaluationSummary | null>(
    (best, e) => (best === null || e.created_at > best.created_at ? e : best),
    null,
  );
  if (latest) {
    // replace, not push: «Назад» must not bounce back into this redirect.
    location.replace(hrefEvaluation(latest.id));
    return;
  }
  const status = h('div', { class: 'cqa-status', role: 'status' });
  const isCall = record.channel === 'voice call';
  if (isCall) {
    // Звонок: транскрипт выбирается переключателем (по умолчанию FreedomSpeech), оценка идёт по выбранному.
    const sources = await loadSources(ctx.api, cid);
    if (ctx.signal.aborted) return;
    const panel = createTranscriptPanel({
      api: ctx.api,
      host: root,
      signal: ctx.signal,
      group,
      cid,
      sources,
      initial: defaultSource(sources),
      onEvaluate: (source, panelStatus, setBusy) =>
        void runAndOpen(
          ctx,
          { group_id: group, conversation_ids: [cid], checklist_id: null, transcript_source: source === API_SOURCE ? null : source },
          panelStatus,
          setBusy,
        ),
    });
    root.replaceChildren(
      heading(cid, badge(t.channel[record.channel] ?? record.channel), badge(record.language), h('a', { class: 'cqa-link', href: hrefDialogs(group) }, `← ${group}`)),
      banner(t.dialogs.transcriptOnly, null, 'info'),
      h('div', { class: 'cqa-card cqa-transcript-only' }, panel.el),
    );
    return;
  }
  const transcript = renderTranscript(record, { ids: true });
  const btn = h('button', { type: 'button', class: 'cqa-btn cqa-btn--primary' }, t.dialogs.evaluateOne);
  btn.addEventListener('click', () => {
    const req: BatchRequest = { group_id: group, conversation_ids: [cid], checklist_id: null };
    void runAndOpen(ctx, req, status, (busy) => {
      btn.disabled = busy;
      btn.textContent = busy ? t.result.reevaluating : t.dialogs.evaluateOne;
      btn.setAttribute('aria-busy', String(busy));
    });
  });
  root.replaceChildren(
    heading(cid, badge(t.channel[record.channel] ?? record.channel), badge(record.language), btn, h('a', { class: 'cqa-link', href: hrefDialogs(group) }, `← ${group}`)),
    banner(t.dialogs.transcriptOnly, null, 'info'),
    status,
    h('div', { class: 'cqa-card cqa-transcript-only' }, transcript.el),
  );
}
