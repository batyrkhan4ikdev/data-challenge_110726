import type { Api } from '../api.js';
import { t } from '../i18n.js';
import type { Criterion } from '../types.gen.js';
import { banner, errorDetails, errorMessage, h } from './dom.js';

export interface AppealModalOptions {
  api: Api;
  evaluationId: string;
  criterion: Criterion;
  /** Вызывается после успешной отправки, до закрытия окна. */
  onSent: () => void;
}

/** Модальное окно апелляции; вставляется внутрь `host` (корень .cqa), чтобы работал CSS. */
export function openAppealModal(host: HTMLElement, opts: AppealModalOptions): void {
  const comment = h('textarea', {
    class: 'cqa-input cqa-textarea',
    rows: 5,
    required: true,
    placeholder: t.appeal.commentPlaceholder,
    'aria-label': t.appeal.comment,
  });
  const errors = h('div', { class: 'cqa-form-errors' });
  const submit = h('button', { type: 'submit', class: 'cqa-btn cqa-btn--primary' }, t.appeal.submit);
  const dialog = h('dialog', { class: 'cqa-modal', 'aria-label': t.appeal.modalTitle });

  const close = () => {
    dialog.close();
    dialog.remove();
  };

  const form = h(
    'form',
    {
      class: 'cqa-form',
      novalidate: true,
      onsubmit: async (ev: Event) => {
        ev.preventDefault();
        errors.replaceChildren();
        if (!comment.value.trim()) {
          errors.appendChild(banner(t.common.commentRequired));
          comment.focus();
          return;
        }
        submit.disabled = true;
        try {
          await opts.api.createAppeal({
            evaluation_id: opts.evaluationId,
            criterion_id: opts.criterion.id,
            comment: comment.value.trim(),
          });
          opts.onSent();
          close();
        } catch (e) {
          errors.appendChild(banner(errorMessage(e), errorDetails(e)));
          submit.disabled = false;
        }
      },
    },
    h('h2', null, t.appeal.modalTitle),
    h('p', null, h('span', { class: 'cqa-muted' }, `${t.appeal.criterion}: `), h('strong', null, `${opts.criterion.id} · ${opts.criterion.title}`)),
    h('label', { class: 'cqa-field' }, h('span', null, t.appeal.comment), comment),
    errors,
    h(
      'div',
      { class: 'cqa-form-actions' },
      submit,
      h('button', { type: 'button', class: 'cqa-btn', onclick: close }, t.common.cancel),
    ),
  );
  dialog.appendChild(form);
  dialog.addEventListener('cancel', () => dialog.remove());
  host.appendChild(dialog);
  dialog.showModal();
  comment.focus();
}
