import { t } from '../i18n.js';
import { hrefChecklist } from '../router.js';
import type { Ctx } from '../router.js';
import type { ChecklistSummary } from '../types.gen.js';
import { badge, banner, errorDetails, errorMessage, h, heading } from '../ui/dom.js';

const CREATE_HREF = '#/checklists/new';

/** Подпись, видимая только в мобильной карточке, где заголовок колонки скрыт. */
function cellLabel(text: string): HTMLElement {
  return h('span', { class: 'cqa-cell-label' }, text);
}

function row(c: ChecklistSummary): HTMLElement {
  return h(
    'tr',
    { role: 'row', 'data-checklist': c.id },
    h('td', { role: 'cell', class: 'cqa-cell-name' }, h('a', { href: hrefChecklist(c.id), class: 'cqa-link' }, c.name)),
    h(
      'td',
      { role: 'cell', class: 'cqa-cell-channel' },
      cellLabel(`${t.lists.channelShort}: `),
      c.channel_default ? t.channel[c.channel_default] : h('span', { class: 'cqa-muted' }, t.checklists.noChannel),
    ),
    h('td', { role: 'cell', class: 'cqa-cell-version' }, badge(`v${c.version}`, 'info')),
    h('td', { role: 'cell', class: 'cqa-cell-id cqa-muted' }, cellLabel(`${t.lists.idShort}: `), c.id),
  );
}

/** Спокойная статичная строка-заглушка до первого ответа (без shimmer). */
function placeholderRow(): HTMLElement {
  const bar = (cls: string) => h('span', { class: `cqa-placeholder ${cls}` });
  return h(
    'tr',
    { role: 'row', class: 'cqa-row-placeholder', 'aria-hidden': 'true' },
    h('td', { role: 'cell', class: 'cqa-cell-name' }, bar('cqa-placeholder--wide')),
    h('td', { role: 'cell', class: 'cqa-cell-channel' }, bar('')),
    h('td', { role: 'cell', class: 'cqa-cell-version' }, bar('cqa-placeholder--short')),
    h('td', { role: 'cell', class: 'cqa-cell-id' }, bar('')),
  );
}

export async function render(root: HTMLElement, ctx: Ctx): Promise<void> {
  const tbody = h('tbody', { role: 'rowgroup' });
  const tableWrap = h(
    'div',
    { class: 'cqa-table-wrap', role: 'region', tabindex: '0', 'aria-label': t.lists.tableLabel },
    h(
      'table',
      { role: 'table', class: 'cqa-table cqa-table--checklists' },
      h(
        'thead',
        { role: 'rowgroup' },
        h(
          'tr',
          { role: 'row' },
          (
            [
              [t.checklists.name, 'cqa-cell-name'],
              [t.checklists.channel, 'cqa-cell-channel'],
              [t.checklists.version, 'cqa-cell-version'],
              [t.checklists.id, 'cqa-cell-id'],
            ] as const
          ).map(([label, cls]) => h('th', { role: 'columnheader', scope: 'col', class: cls }, label)),
        ),
      ),
      tbody,
    ),
  );
  const body = h('div', { class: 'cqa-lists-body' });

  async function load(): Promise<void> {
    tbody.replaceChildren(placeholderRow(), placeholderRow());
    tableWrap.setAttribute('aria-busy', 'true');
    body.replaceChildren(h('p', { class: 'cqa-loading', role: 'status' }, t.common.loading), tableWrap);
    let list: ChecklistSummary[];
    try {
      list = await ctx.api.checklists();
    } catch (e) {
      if (ctx.signal.aborted) return;
      // Ошибка не превращается в пустой список: показываем причину и повтор GET.
      const notice = banner(`${t.lists.loadError}: ${errorMessage(e)}`, errorDetails(e));
      notice.appendChild(
        h('div', { class: 'cqa-banner-actions' }, h('button', { type: 'button', class: 'cqa-btn', onclick: () => void load() }, t.lists.retry)),
      );
      body.replaceChildren(notice);
      return;
    } finally {
      tableWrap.removeAttribute('aria-busy');
    }
    if (ctx.signal.aborted) return;
    if (!list.length) {
      body.replaceChildren(
        h(
          'div',
          { class: 'cqa-card cqa-lists-empty' },
          h('h2', { class: 'cqa-card-title' }, t.lists.emptyTitle),
          h('p', { class: 'cqa-muted' }, t.lists.emptyHint),
          h('a', { class: 'cqa-btn cqa-btn--tint', href: CREATE_HREF }, t.lists.createFirst),
        ),
      );
      return;
    }
    tbody.replaceChildren(...list.map(row));
    body.replaceChildren(tableWrap);
  }

  root.replaceChildren(heading(t.checklists.title, h('a', { class: 'cqa-btn cqa-btn--primary', href: CREATE_HREF }, t.common.create)), body);
  await load();
}
