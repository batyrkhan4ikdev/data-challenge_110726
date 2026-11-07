import { t } from '../i18n.js';
import { hrefChecklist } from '../router.js';
import type { Ctx } from '../router.js';
import { badge, h, heading } from '../ui/dom.js';

export async function render(root: HTMLElement, ctx: Ctx): Promise<void> {
  const list = await ctx.api.checklists();
  if (ctx.signal.aborted) return;

  const rows = list.map((c) =>
    h(
      'tr',
      { 'data-checklist': c.id },
      h('td', null, h('a', { href: hrefChecklist(c.id), class: 'cqa-link' }, c.name)),
      h('td', { class: 'cqa-muted' }, c.id),
      h('td', null, c.channel_default ? t.channel[c.channel_default] : h('span', { class: 'cqa-muted' }, t.checklists.noChannel)),
      h('td', { class: 'cqa-num' }, badge(`v${c.version}`, 'info')),
    ),
  );

  root.replaceChildren(
    heading(
      t.checklists.title,
      h('a', { class: 'cqa-btn cqa-btn--primary', href: '#/checklists/new' }, t.common.create),
    ),
    rows.length
      ? h(
          'table',
          { class: 'cqa-table' },
          h(
            'thead',
            null,
            h(
              'tr',
              null,
              [t.checklists.name, t.checklists.id, t.checklists.channel, t.checklists.version].map((label) => h('th', { scope: 'col' }, label)),
            ),
          ),
          h('tbody', null, rows),
        )
      : h('p', { class: 'cqa-muted' }, t.checklists.empty),
  );
}
