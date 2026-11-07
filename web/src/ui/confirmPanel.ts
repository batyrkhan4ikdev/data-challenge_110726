import { t } from '../i18n.js';
import type { Ctx } from '../router.js';
import type { Attention, Confirmation, EvaluationView } from '../types.gen.js';
import { banner, errorMessage, h } from './dom.js';

const REVIEWER_KEY = 'cqa-reviewer';

function savedReviewer(): string {
  try {
    return localStorage.getItem(REVIEWER_KEY) ?? '';
  } catch {
    return '';
  }
}

/** Поле «Проверяющий»; значение запоминается и общее для всех панелей. */
export function reviewerInput(): HTMLInputElement {
  const input = h('input', {
    class: 'cqa-input cqa-confirm-reviewer',
    type: 'text',
    value: savedReviewer(),
    placeholder: t.confirm.reviewer,
    'aria-label': t.confirm.reviewer,
    oninput: () => {
      try {
        localStorage.setItem(REVIEWER_KEY, input.value.trim());
      } catch {
        // хранилище недоступно: имя живёт только в поле
      }
    },
  });
  return input;
}

/** Критерии без причины внимания и ещё не принятые ранее. */
async function undisputedIds(ctx: Ctx, evaluationId: string): Promise<string[]> {
  const [view, attention, done] = await Promise.all([
    ctx.api.evaluation(evaluationId),
    ctx.api.attention(evaluationId),
    ctx.api.confirmations(evaluationId),
  ]);
  const skip = new Set([...attention.criterion_ids, ...done.flatMap((c) => c.criterion_ids)]);
  return view.checklist.criteria.map((c) => c.id).filter((id) => !skip.has(id));
}

/** «Принять неспорные»: один пакетный POST. Пустой результат = принимать нечего. */
export async function acceptUndisputed(ctx: Ctx, evaluationId: string, reviewer: string): Promise<Confirmation | null> {
  if (!reviewer.trim()) throw new Error(t.confirm.reviewerRequired);
  const ids = await undisputedIds(ctx, evaluationId);
  if (!ids.length) return null;
  return ctx.api.createConfirmation(evaluationId, { criterion_ids: ids, mode: 'batch', reviewer, note: '' });
}

/** Строка счётчиков: пакетом / по одному / изменено через апелляцию. Возвращает элемент и функцию обновления. */
export function statsLine(ctx: Ctx): { el: HTMLElement; refresh: () => Promise<void> } {
  const el = h('p', { class: 'cqa-muted cqa-confirm-stats', 'aria-live': 'polite' });
  const refresh = async () => {
    try {
      const s = await ctx.api.confirmationStats();
      if (!ctx.signal.aborted) el.textContent = t.confirm.statsLine(s.batch, s.single, s.overridden);
    } catch {
      // счётчики вторичны: ошибка не мешает ревью
    }
  };
  void refresh();
  return { el, refresh };
}

/** Кнопка «Принять неспорные» с собственным статусом; `onDone` вызывается после успешной записи. */
export function acceptButton(
  ctx: Ctx,
  evaluationId: string,
  reviewer: () => string,
  onDone: () => void,
): { el: HTMLElement; run: () => void } {
  const status = h('span', { class: 'cqa-muted cqa-confirm-status', role: 'status' });
  const btn = h('button', { type: 'button', class: 'cqa-btn', 'data-action': 'accept-undisputed' }, t.confirm.acceptUndisputed);
  const run = () => {
    if (btn.disabled) return;
    btn.disabled = true;
    status.textContent = '';
    acceptUndisputed(ctx, evaluationId, reviewer())
      .then((c) => {
        status.textContent = c ? t.confirm.accepted(c.criterion_ids.join(', ')) : t.confirm.nothing;
        if (c) onDone();
      })
      .catch((e) => {
        status.textContent = errorMessage(e);
      })
      .finally(() => {
        btn.disabled = false;
      });
  };
  btn.addEventListener('click', run);
  return { el: h('span', { class: 'cqa-confirm-accept' }, btn, status), run };
}

function historyList(items: Confirmation[]): HTMLElement {
  if (!items.length) return h('p', { class: 'cqa-muted' }, t.confirm.none);
  return h(
    'ul',
    { class: 'cqa-confirm-history' },
    items.map((c) =>
      h(
        'li',
        null,
        h('strong', null, `${c.reviewer} · ${c.mode === 'batch' ? t.confirm.modeBatch : t.confirm.modeSingle}: `),
        c.criterion_ids.join(', '),
        c.auto_note ? h('div', { class: 'cqa-muted' }, c.auto_note) : null,
        c.note ? h('div', { class: 'cqa-muted' }, c.note) : null,
      ),
    ),
  );
}

/** Полная панель подтверждений для страницы результата: причины внимания, пакет, поштучно, журнал. */
export async function mountConfirmPanel(ctx: Ctx, view: EvaluationView): Promise<HTMLElement> {
  const evaluationId = view.evaluation.id;
  const body = h('div', { class: 'cqa-confirm-body' });
  const stats = statsLine(ctx);
  const reviewer = reviewerInput();

  const draw = async () => {
    let attention: Attention;
    let history: Confirmation[];
    try {
      [attention, history] = await Promise.all([ctx.api.attention(evaluationId), ctx.api.confirmations(evaluationId)]);
    } catch (e) {
      body.replaceChildren(banner(errorMessage(e)));
      return;
    }
    if (ctx.signal.aborted) return;
    const accept = acceptButton(ctx, evaluationId, () => reviewer.value.trim(), () => {
      void draw();
      void stats.refresh();
    });
    const single = (id: string) =>
      h(
        'button',
        {
          type: 'button',
          class: 'cqa-btn cqa-btn--small',
          onclick: async (e: Event) => {
            const btn = e.target as HTMLButtonElement;
            if (!reviewer.value.trim()) {
              btn.title = t.confirm.reviewerRequired;
              reviewer.focus();
              return;
            }
            btn.disabled = true;
            try {
              await ctx.api.createConfirmation(evaluationId, { criterion_ids: [id], mode: 'single', reviewer: reviewer.value.trim(), note: '' });
              void stats.refresh();
              await draw();
            } catch (err) {
              btn.disabled = false;
              btn.title = errorMessage(err);
            }
          },
        },
        `${t.review.confirm} ${id}`,
      );
    body.replaceChildren(
      attention.reasons.length
        ? h('div', null, h('h3', null, t.confirm.disputed), h('ul', null, attention.reasons.map((r) => h('li', null, r))), attention.criterion_ids.map(single))
        : h('p', { class: 'cqa-muted' }, t.dialogs.attentionNone),
      h('div', { class: 'cqa-confirm-actions' }, accept.el),
      h('h3', null, t.confirm.history),
      historyList(history),
    );
  };
  await draw();
  return h(
    'section',
    { class: 'cqa-card cqa-confirm-panel', 'aria-label': t.confirm.title },
    h('h2', null, t.confirm.title),
    h('label', { class: 'cqa-inline' }, h('span', null, t.confirm.reviewer), reviewer),
    h('p', { class: 'cqa-muted' }, t.confirm.totalUnchanged),
    stats.el,
    body,
  );
}
