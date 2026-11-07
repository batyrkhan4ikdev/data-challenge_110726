import { t } from '../i18n.js';
import type { DialogFacts } from '../types.gen.js';
import { badge, h } from './dom.js';

function clock(s: number | null | undefined): string {
  if (s === null || s === undefined) return t.result.facts.none;
  const total = Math.round(s);
  const hh = Math.floor(total / 3600);
  const mm = Math.floor((total % 3600) / 60);
  const ss = total % 60;
  const p = (n: number) => String(n).padStart(2, '0');
  return hh ? `${hh}:${p(mm)}:${p(ss)}` : `${p(mm)}:${p(ss)}`;
}

/** Карточка «Факты диалога»; `onJump` — тот же переход, что и у подтверждений (скролл, подсветка, перемотка аудио). */
export function factsCard(slot: Promise<DialogFacts>, onJump: (idx: number) => void): HTMLElement {
  const f = t.result.facts;
  const card = h(
    'section',
    { class: 'cqa-card cqa-facts', 'aria-label': f.title },
    h('h2', { class: 'cqa-card-title' }, f.title),
    h('span', { class: 'cqa-muted' }, t.common.loading),
  );
  const link = (idx: number) =>
    h('button', { type: 'button', class: 'cqa-link cqa-evidence-link', onclick: () => onJump(idx) }, `#${idx + 1}`);
  const row = (label: string, ...value: (string | Node)[]) =>
    h('div', { class: 'cqa-facts-row' }, h('span', { class: 'cqa-muted cqa-facts-label' }, label), h('span', { class: 'cqa-facts-value' }, ...value));

  slot.then(
    (d) => {
      const rows: HTMLElement[] = [row(f.duration, clock(d.duration_s))];
      rows.push(
        row(
          f.firstResponse,
          clock(d.first_response_s),
          ' ',
          d.sla_ok === null || d.sla_ok === undefined ? '' : d.sla_ok ? badge(f.slaOk(Math.round((d.sla_s ?? 180) / 60)), 'good') : badge(f.slaBad, 'bad'),
          ' ',
          d.first_response_idx === null || d.first_response_idx === undefined ? '' : link(d.first_response_idx),
        ),
        row(f.maxWait, clock(d.max_wait_s), ' ', d.max_wait_idx === null || d.max_wait_idx === undefined ? '' : link(d.max_wait_idx)),
        row(f.turns, `${f.client} ${d.turns.client ?? 0} · ${f.operator} ${d.turns.operator ?? 0} · ${f.bot} ${d.turns.bot ?? 0}`),
        row(
          f.masked,
          ...(d.masked.length
            ? d.masked.flatMap((m) => [badge(`${m.token} ×${m.count}`, 'neutral'), link(m.first_idx), ' '])
            : [f.none]),
        ),
      );
      if (d.identity_verified_idx !== null && d.identity_verified_idx !== undefined) {
        rows.push(row(f.verified, link(d.identity_verified_idx)));
      }
      const events = h(
        'ul',
        { class: 'cqa-facts-events' },
        ...d.events.map((e) => h('li', null, link(e.idx), ' ', e.offset_s !== null && e.offset_s !== undefined ? `${clock(e.offset_s)} ` : '', e.text)),
      );
      rows.push(row(f.events, ...(d.events.length ? [] : [f.none])));
      if (d.events.length) rows.push(events);
      card.replaceChildren(h('h2', { class: 'cqa-card-title' }, f.title), ...rows);
    },
    () => card.replaceChildren(h('h2', { class: 'cqa-card-title' }, f.title), h('p', { class: 'cqa-muted' }, f.error)),
  );
  return card;
}
