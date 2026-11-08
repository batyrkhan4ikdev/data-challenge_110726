import type { Api } from '../api.js';
import { t } from '../i18n.js';
import type { Criterion, Record as DialogRecord } from '../types.gen.js';
import { badge, banner, errorDetails, errorMessage, h } from './dom.js';

interface RecourseEdit {
  idx: number | null;
  insert_after: number | null;
  new_text: string;
}
interface RecourseVerdict {
  verdict: string;
  points: number | null;
  max_points: number;
}
export interface RecourseResult {
  edits: RecourseEdit[];
  rationale: string;
  before: RecourseVerdict;
  after: RecourseVerdict;
  verified: boolean;
  note: string;
}

const VERDICT: Record<string, string> = { yes: 'Да', no: 'Нет', na: 'N/A' };

function diffBlock(edit: RecourseEdit, record: DialogRecord | null): HTMLElement {
  const turns = record?.transcript ?? [];
  const old = edit.idx !== null ? turns.find((t) => t.idx === edit.idx) : undefined;
  const where =
    edit.idx !== null ? `Реплика оператора #${edit.idx + 1}` : `Новая реплика оператора после #${(edit.insert_after ?? 0) + 1}`;
  return h(
    'div',
    { class: 'cqa-recourse-diff' },
    h('div', { class: 'cqa-muted' }, where),
    old ? h('div', { class: 'cqa-recourse-del' }, `− ${old.text}`) : null,
    h('div', { class: 'cqa-recourse-add' }, `+ ${edit.new_text}`),
  );
}

function renderResult(r: RecourseResult, record: DialogRecord | null): HTMLElement {
  const badgeEl = r.verified
    ? badge(`проверено судьёй: ${VERDICT[r.before.verdict] ?? r.before.verdict} → ${VERDICT[r.after.verdict] ?? r.after.verdict}`, 'good')
    : badge('не подтвердилось', 'warn', 'Судья не поставил более высокую оценку после правки');
  return h(
    'div',
    { class: 'cqa-recourse' },
    h('div', { class: 'cqa-recourse-head' }, h('strong', null, t.result.recourseButton), badgeEl),
    r.edits.length ? r.edits.map((e) => diffBlock(e, record)) : h('div', { class: 'cqa-muted' }, 'Модель не предложила правок.'),
    r.rationale ? h('p', { class: 'cqa-recourse-why' }, r.rationale) : null,
    h('p', { class: 'cqa-muted cqa-recourse-note' }, 'Подсказка для оператора. В оценку не входит: баллы и итог не меняются.'),
  );
}

/** Кнопка «Как было бы правильно» для потерянного критерия и слот под её результат; для грубых ошибок null. */
export function recourseControl(api: Api, evaluationId: string, c: Criterion, record: DialogRecord | null): { button: HTMLButtonElement; slot: HTMLElement } | null {
  if (c.kind === 'gross_error' || c.id === 'c08') return null;
  const slot = h('div', { class: 'cqa-recourse-slot' });
  const button = h('button', { type: 'button', class: 'cqa-btn cqa-btn--small cqa-recourse-btn' }, t.result.recourseButton);
  button.addEventListener('click', async () => {
    button.disabled = true;
    slot.replaceChildren(h('span', { class: 'cqa-muted' }, 'Судья подбирает правку и проверяет её…'));
    try {
      slot.replaceChildren(renderResult(await api.recourse<RecourseResult>(evaluationId, c.id), record));
    } catch (e) {
      slot.replaceChildren(banner(t.caseTools.recourseFail, [errorMessage(e), ...(errorDetails(e) ?? [])], 'error', true));
      button.disabled = false;
    }
  });
  return { button, slot };
}
