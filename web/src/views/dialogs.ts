import { t } from '../i18n.js';
import { DEFAULT_GROUP, hrefDialogs, hrefEvaluation, hrefTranscript } from '../router.js';
import type { Ctx } from '../router.js';
import type { BatchRequest, ChecklistSummary, ConversationSummary, Job } from '../types.gen.js';
import { badge, banner, errorDetails, errorMessage, fmt, h, heading } from '../ui/dom.js';

function totalCell(row: ConversationSummary): HTMLElement {
  const l = row.latest;
  if (!l) return h('td', { class: 'cqa-num cqa-muted' }, t.dialogs.notEvaluated);
  const changed = l.final_total !== l.total;
  return h(
    'td',
    { class: 'cqa-num' },
    fmt(l.total),
    changed ? h('span', { class: 'cqa-chain-arrow' }, ' → ') : null,
    changed ? h('strong', null, fmt(l.final_total)) : null,
  );
}

export async function render(root: HTMLElement, ctx: Ctx): Promise<void> {
  let group = ctx.params.group;
  let rows: ConversationSummary[] = [];
  const selected = new Set<string>();
  let checklists: ChecklistSummary[] = [];
  let running = false;

  const groupInput = h('input', { class: 'cqa-input', type: 'text', value: group, 'aria-label': t.dialogs.group, size: 10 });
  const channelFilter = h(
    'select',
    { class: 'cqa-input', 'aria-label': t.dialogs.channel, onchange: () => drawRows() },
    h('option', { value: '' }, `${t.dialogs.channel}: ${t.dialogs.all}`),
    h('option', { value: 'agent chat' }, t.channel['agent chat']),
    h('option', { value: 'voice call' }, t.channel['voice call']),
  );
  const langFilter = h(
    'select',
    { class: 'cqa-input', 'aria-label': t.dialogs.language, onchange: () => drawRows() },
    h('option', { value: '' }, `${t.dialogs.language}: ${t.dialogs.all}`),
    ['RU', 'KZ', 'EN'].map((l) => h('option', { value: l }, l)),
  );
  const checklistSelect = h('select', { class: 'cqa-input', 'aria-label': t.dialogs.checklist }, h('option', { value: '' }, t.dialogs.byChannel));
  const modeSelect = h(
    'select',
    { class: 'cqa-input', 'aria-label': t.dialogs.mode },
    h('option', { value: '' }, t.dialogs.modeDefault),
    h('option', { value: 'single' }, t.dialogs.modeSingle),
    h('option', { value: 'per_criterion' }, t.dialogs.modePerCriterion),
  );
  const kInput = h('input', { class: 'cqa-input cqa-input--num', type: 'number', min: '1', max: '9', placeholder: t.dialogs.kDefault, 'aria-label': t.dialogs.k });
  const evaluateBtn = h('button', { type: 'button', class: 'cqa-btn cqa-btn--primary', onclick: () => void evaluate() }, t.dialogs.evaluate);
  const selectedLabel = h('span', { class: 'cqa-muted' });
  const countLabel = h('span', { class: 'cqa-muted' });
  const notices = h('div', { class: 'cqa-notices' });
  const progress = h('div', { class: 'cqa-progress-wrap' });
  const tbody = h('tbody');
  const allBox = h('input', { type: 'checkbox', 'aria-label': t.dialogs.selectAll, onchange: () => toggleAll(allBox.checked) });
  const grossOnly = h('input', { type: 'checkbox', 'aria-label': t.dialogs.grossOnly, onchange: () => drawRows() });

  function visibleRows(): ConversationSummary[] {
    return rows.filter(
      (r) =>
        (!channelFilter.value || r.channel === channelFilter.value) &&
        (!langFilter.value || r.language === langFilter.value) &&
        (!grossOnly.checked || r.latest?.gross_error === true),
    );
  }

  function updateSelection(): void {
    selectedLabel.textContent = t.dialogs.selected(selected.size);
    evaluateBtn.disabled = running || selected.size === 0;
    const vis = visibleRows();
    const n = vis.filter((r) => selected.has(r.conversation_id)).length;
    allBox.checked = vis.length > 0 && n === vis.length;
    allBox.indeterminate = n > 0 && n < vis.length;
  }

  function toggleAll(on: boolean): void {
    for (const r of visibleRows()) {
      if (on) selected.add(r.conversation_id);
      else selected.delete(r.conversation_id);
    }
    drawRows();
  }

  function drawRows(): void {
    const vis = visibleRows();
    tbody.replaceChildren(
      ...vis.map((r) =>
        h(
          'tr',
          { 'data-cid': r.conversation_id, class: selected.has(r.conversation_id) ? 'is-selected' : '' },
          h(
            'td',
            { class: 'cqa-check-cell' },
            h('input', {
              type: 'checkbox',
              checked: selected.has(r.conversation_id),
              'aria-label': r.conversation_id,
              onchange: (e: Event) => {
                if ((e.target as HTMLInputElement).checked) selected.add(r.conversation_id);
                else selected.delete(r.conversation_id);
                drawRows();
              },
            }),
          ),
          h(
            'td',
            null,
            h(
              'a',
              { class: 'cqa-link', href: r.latest ? hrefEvaluation(r.latest.id) : hrefTranscript(group, r.conversation_id) },
              r.conversation_id,
            ),
          ),
          h('td', null, t.channel[r.channel] ?? r.channel),
          h('td', null, r.language),
          h('td', { class: 'cqa-num' }, String(r.turns)),
          totalCell(r),
          h('td', null, r.latest?.gross_error ? badge(t.dialogs.gross, 'bad') : null),
        ),
      ),
    );
    if (!vis.length) {
      tbody.appendChild(h('tr', null, h('td', { colspan: 7, class: 'cqa-muted cqa-empty' }, t.dialogs.empty)));
    }
    countLabel.textContent = t.dialogs.count(vis.length, rows.length);
    updateSelection();
  }

  async function load(refresh: boolean): Promise<void> {
    notices.replaceChildren();
    const next = groupInput.value.trim() || DEFAULT_GROUP;
    try {
      const data = await ctx.api.conversations(next, refresh);
      if (ctx.signal.aborted) return;
      group = next;
      rows = data;
      const known = new Set(rows.map((r) => r.conversation_id));
      for (const id of [...selected]) if (!known.has(id)) selected.delete(id);
      history.replaceState(null, '', hrefDialogs(group));
    } catch (e) {
      if (ctx.signal.aborted) return;
      const notice = banner(`${t.dialogs.datasetError}: ${errorMessage(e)}`, errorDetails(e));
      if (rows.length) notice.appendChild(h('div', null, t.dialogs.previousRows));
      notices.appendChild(notice);
    }
    drawRows();
  }

  function showJob(job: Job): void {
    const pct = job.total ? Math.round((job.done / job.total) * 100) : 0;
    const failed = Object.entries(job.failed);
    const fill = h('div', { class: 'cqa-progress-fill' });
    fill.style.width = `${pct}%`;
    progress.replaceChildren(
      h(
        'div',
        { class: 'cqa-progress', role: 'progressbar', 'aria-valuemin': 0, 'aria-valuemax': job.total, 'aria-valuenow': job.done },
        fill,
      ),
      h('div', { class: 'cqa-progress-text' }, job.state === 'finished' ? t.dialogs.jobFinished : t.dialogs.progress(job.done, job.total), ` (${job.done}/${job.total})`),
      ...(failed.length ? [banner(t.dialogs.jobFailed, failed.map(([cid, msg]) => `${cid}: ${msg}`))] : []),
    );
  }

  async function evaluate(): Promise<void> {
    const req: BatchRequest = {
      group_id: group,
      conversation_ids: [...selected],
      checklist_id: checklistSelect.value || null,
    };
    if (modeSelect.value) req.mode = modeSelect.value as BatchRequest['mode'];
    const k = parseInt(kInput.value, 10);
    if (k >= 1) req.k = k;
    running = true;
    updateSelection();
    try {
      const job = await ctx.api.runBatch(req, showJob, ctx.signal);
      if (ctx.signal.aborted) return;
      showJob(job);
      selected.clear();
      await load(false);
    } catch (e) {
      progress.replaceChildren(banner(errorMessage(e), errorDetails(e)));
    } finally {
      running = false;
      if (!ctx.signal.aborted) updateSelection();
    }
  }

  root.replaceChildren(
    heading(t.dialogs.title),
    h(
      'form',
      {
        class: 'cqa-toolbar',
        onsubmit: (e: Event) => {
          e.preventDefault();
          void load(true);
        },
      },
      h('label', { class: 'cqa-inline' }, h('span', null, t.dialogs.group), groupInput),
      h('button', { type: 'submit', class: 'cqa-btn' }, t.dialogs.refresh),
      channelFilter,
      langFilter,
      h('label', { class: 'cqa-inline' }, grossOnly, h('span', null, t.dialogs.grossOnly)),
      countLabel,
    ),
    h(
      'div',
      { class: 'cqa-toolbar cqa-toolbar--batch' },
      h('label', { class: 'cqa-inline' }, h('span', null, t.dialogs.checklist), checklistSelect),
      h('label', { class: 'cqa-inline' }, h('span', null, t.dialogs.mode), modeSelect),
      h('label', { class: 'cqa-inline' }, h('span', null, t.dialogs.k), kInput),
      evaluateBtn,
      selectedLabel,
    ),
    notices,
    progress,
    h(
      'table',
      { class: 'cqa-table cqa-dialogs' },
      h(
        'thead',
        null,
        h(
          'tr',
          null,
          h('th', { scope: 'col', class: 'cqa-check-cell' }, allBox),
          [t.dialogs.colId, t.dialogs.colChannel, t.dialogs.colLang, t.dialogs.colTurns, t.dialogs.colTotal, t.dialogs.colGross].map((label) =>
            h('th', { scope: 'col' }, label),
          ),
        ),
      ),
      tbody,
    ),
  );

  // Список чек-листов подгружается параллельно; без него «по каналу» остаётся единственным пунктом.
  ctx.api
    .checklists()
    .then((list) => {
      checklists = list;
      checklistSelect.append(...checklists.map((c) => h('option', { value: c.id }, `${c.name} (v${c.version})`)));
    })
    .catch(() => undefined);

  await load(false);
}
