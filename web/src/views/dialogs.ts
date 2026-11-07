import { t } from '../i18n.js';
import { DEFAULT_GROUP, hrefDialogs, hrefEvaluation, hrefTranscript } from '../router.js';
import type { Ctx } from '../router.js';
import type { BatchRequest, ChecklistSummary, ConversationSummary, Job } from '../types.gen.js';
import { badge, banner, errorDetails, errorMessage, fmt, h, heading } from '../ui/dom.js';
import { openUploadModal } from '../ui/uploadModal.js';

/** Группа диалогов, добавленных вручную (server/uploads.py). */
const UPLOADS_GROUP = 'UPLOADS';

/** Подпись, видимая только в мобильной карточке, где заголовок колонки скрыт. */
function cellLabel(text: string): HTMLElement {
  return h('span', { class: 'cqa-cell-label' }, text);
}

function totalCell(row: ConversationSummary): HTMLElement {
  const l = row.latest;
  if (!l) return h('td', { role: 'cell', class: 'cqa-num cqa-cell-total cqa-muted' }, t.dialogs.notEvaluated);
  const changed = l.final_total !== l.total;
  return h(
    'td',
    { role: 'cell', class: 'cqa-num cqa-cell-total' },
    cellLabel(`${t.dialogs.colTotal} `),
    fmt(l.total),
    changed ? h('span', { class: 'cqa-chain-arrow' }, ' → ') : null,
    changed ? h('strong', null, fmt(l.final_total)) : null,
  );
}

/** Чип «приоритет просмотра»: причины в подсказке. Не вероятность ошибки, итог не меняется. */
function attentionChip(row: ConversationSummary): HTMLElement | null {
  const a = row.attention;
  if (!a || !a.reasons.length) return null;
  const tone = a.score >= 50 ? 'bad' : a.score >= 15 ? 'warn' : 'neutral';
  return badge(t.dialogs.attentionChip(a.score), tone, `${t.dialogs.attentionTitle}\n• ${a.reasons.join('\n• ')}`);
}

export async function render(root: HTMLElement, ctx: Ctx): Promise<void> {
  let group = ctx.params.group;
  let rows: ConversationSummary[] = [];
  const selected = new Set<string>();
  let checklists: ChecklistSummary[] = [];
  let running = false;

  const groupInput = h('input', { class: 'cqa-input cqa-input--group', type: 'text', value: group, size: 10 });
  const refreshBtn = h('button', { type: 'submit', class: 'cqa-btn' }, t.dialogs.refresh);
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
  const checklistSelect = h('select', { class: 'cqa-input' }, h('option', { value: '' }, t.dialogs.byChannel));
  const modeSelect = h(
    'select',
    { class: 'cqa-input' },
    h('option', { value: '' }, t.dialogs.modeDefault),
    h('option', { value: 'single' }, t.dialogs.modeSingle),
    h('option', { value: 'per_criterion' }, t.dialogs.modePerCriterion),
  );
  const kInput = h('input', { class: 'cqa-input cqa-input--num', type: 'number', min: '1', max: '9', placeholder: t.dialogs.kDefault });
  const evaluateBtn = h('button', { type: 'button', class: 'cqa-btn cqa-btn--primary', onclick: () => void evaluate() }, t.dialogs.evaluate);
  const selectedLabel = h('span', { class: 'cqa-muted cqa-batch-count', 'aria-live': 'polite' });
  const countLabel = h('span', { class: 'cqa-muted cqa-filter-count' });
  const notices = h('div', { class: 'cqa-notices' });
  const progress = h('div', { class: 'cqa-progress-wrap' });
  const tbody = h('tbody', { role: 'rowgroup' });
  const allBox = h('input', { type: 'checkbox', 'aria-label': t.dialogs.selectAll, onchange: () => toggleAll(allBox.checked) });
  const grossOnly = h('input', { type: 'checkbox', onchange: () => drawRows() });
  const sortSelect = h(
    'select',
    { class: 'cqa-input', 'aria-label': t.dialogs.sortLabel, onchange: () => drawRows() },
    h('option', { value: '' }, `${t.dialogs.sortLabel}: ${t.dialogs.sortDefault}`),
    h('option', { value: 'attention' }, `${t.dialogs.sortLabel}: ${t.dialogs.sortAttention}`),
  );
  const tableWrap = h('div', { class: 'cqa-table-wrap', role: 'region', tabindex: '0', 'aria-label': t.dialogs.tableLabel });

  function visibleRows(): ConversationSummary[] {
    const vis = rows.filter(
      (r) =>
        (!channelFilter.value || r.channel === channelFilter.value) &&
        (!langFilter.value || r.language === langFilter.value) &&
        (!grossOnly.checked || r.latest?.gross_error === true),
    );
    if (sortSelect.value !== 'attention') return vis;
    // Детерминированно: приоритет по убыванию, затем id; неоценённые в конце.
    const score = (r: ConversationSummary) => r.attention?.score ?? -1;
    return vis.sort((a, b) => score(b) - score(a) || a.conversation_id.localeCompare(b.conversation_id));
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

  function resetFilters(): void {
    channelFilter.value = '';
    langFilter.value = '';
    grossOnly.checked = false;
    drawRows();
  }

  function emptyRow(): HTMLElement {
    // Фильтры сузили непустой список: предлагаем их сбросить; иначе данных просто нет.
    const filtered = rows.length > 0;
    return h(
      'tr',
      { role: 'row', class: 'cqa-row-empty' },
      h(
        'td',
        { role: 'cell', colspan: 7, class: 'cqa-empty' },
        h('p', { class: 'cqa-muted' }, filtered ? t.dialogs.emptyFiltered : t.dialogs.empty),
        filtered ? h('button', { type: 'button', class: 'cqa-btn', onclick: () => resetFilters() }, t.dialogs.resetFilters) : null,
      ),
    );
  }

  function drawRows(): void {
    const vis = visibleRows();
    tbody.replaceChildren(
      ...vis.map((r) =>
        h(
          'tr',
          { role: 'row', 'data-cid': r.conversation_id, class: selected.has(r.conversation_id) ? 'is-selected' : '' },
          h(
            'td',
            { role: 'cell', class: 'cqa-check-cell' },
            h(
              'label',
              { class: 'cqa-check-hit' },
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
          ),
          h(
            'td',
            { role: 'cell', class: 'cqa-cell-id' },
            h(
              'a',
              { class: 'cqa-link', href: r.latest ? hrefEvaluation(r.latest.id) : hrefTranscript(group, r.conversation_id) },
              r.conversation_id,
            ),
          ),
          h('td', { role: 'cell', class: 'cqa-cell-channel' }, t.channel[r.channel] ?? r.channel),
          h('td', { role: 'cell', class: 'cqa-cell-lang' }, r.language),
          h('td', { role: 'cell', class: 'cqa-num cqa-cell-turns' }, String(r.turns), cellLabel(` ${t.dialogs.turnsSuffix}`)),
          totalCell(r),
          h('td', { role: 'cell', class: 'cqa-cell-gross' }, r.latest?.gross_error ? badge(t.dialogs.gross, 'bad') : null, attentionChip(r)),
        ),
      ),
    );
    if (!vis.length) tbody.appendChild(emptyRow());
    countLabel.textContent = t.dialogs.count(vis.length, rows.length);
    updateSelection();
  }

  async function load(refresh: boolean): Promise<void> {
    notices.replaceChildren();
    const next = groupInput.value.trim() || DEFAULT_GROUP;
    // Прежние строки остаются на месте, пока идёт загрузка.
    tableWrap.setAttribute('aria-busy', 'true');
    refreshBtn.disabled = true;
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
    } finally {
      tableWrap.removeAttribute('aria-busy');
      refreshBtn.disabled = false;
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

  const headers: [string, string][] = [
    [t.dialogs.colId, 'cqa-cell-id'],
    [t.dialogs.colChannel, 'cqa-cell-channel'],
    [t.dialogs.colLang, 'cqa-cell-lang'],
    [t.dialogs.colTurns, 'cqa-num cqa-cell-turns'],
    [t.dialogs.colTotal, 'cqa-num cqa-cell-total'],
    [t.dialogs.colAttention, 'cqa-cell-gross'],
  ];
  // Явные role сохраняют семантику таблицы, когда на узком экране строки становятся карточками (display:grid).
  tableWrap.appendChild(
    h(
      'table',
      { role: 'table', class: 'cqa-table cqa-table--dialogs' },
      h(
        'thead',
        { role: 'rowgroup' },
        h(
          'tr',
          { role: 'row' },
          h(
            'th',
            { role: 'columnheader', scope: 'col', class: 'cqa-check-cell' },
            h('label', { class: 'cqa-check-hit' }, allBox, h('span', { class: 'cqa-cell-label', 'aria-hidden': 'true' }, t.dialogs.selectAll)),
          ),
          headers.map(([label, cls]) => h('th', { role: 'columnheader', scope: 'col', class: cls }, label)),
        ),
      ),
      tbody,
    ),
  );

  root.replaceChildren(
    heading(t.dialogs.title),
    h(
      'div',
      { class: 'cqa-toolbar cqa-toolbar--uploads' },
      h(
        'button',
        {
          type: 'button',
          class: 'cqa-btn cqa-btn--primary',
          onclick: () =>
            openUploadModal(root, {
              api: ctx.api,
              onAdded: (record) => ctx.navigate(hrefTranscript(UPLOADS_GROUP, record.conversation_id)),
            }),
        },
        t.uploads.open,
      ),
      group === UPLOADS_GROUP ? null : h('a', { class: 'cqa-link', href: hrefDialogs(UPLOADS_GROUP) }, t.uploads.group),
    ),
    h(
      'form',
      {
        class: 'cqa-toolbar cqa-toolbar--filters',
        'aria-label': t.dialogs.filtersLabel,
        onsubmit: (e: Event) => {
          e.preventDefault();
          void load(true);
        },
      },
      h('label', { class: 'cqa-inline cqa-filter-group' }, h('span', null, t.dialogs.group), groupInput),
      refreshBtn,
      channelFilter,
      langFilter,
      sortSelect,
      h('label', { class: 'cqa-inline cqa-filter-gross' }, grossOnly, h('span', null, t.dialogs.grossOnly)),
      countLabel,
    ),
    h(
      'div',
      { class: 'cqa-toolbar cqa-toolbar--batch', role: 'group', 'aria-label': t.dialogs.batchLabel },
      h('label', { class: 'cqa-inline cqa-batch-checklist' }, h('span', null, t.dialogs.checklist), checklistSelect),
      evaluateBtn,
      selectedLabel,
      h(
        'details',
        { class: 'cqa-batch-params' },
        h('summary', null, t.dialogs.params),
        h(
          'div',
          { class: 'cqa-batch-params-body' },
          h('label', { class: 'cqa-inline' }, h('span', null, t.dialogs.mode), modeSelect),
          h('label', { class: 'cqa-inline' }, h('span', null, t.dialogs.k), kInput),
        ),
      ),
    ),
    notices,
    progress,
    tableWrap,
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
