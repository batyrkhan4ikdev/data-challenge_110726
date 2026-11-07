import type { Api } from '../api.js';
import { t } from '../i18n.js';
import type { Criterion } from '../types.gen.js';
import { banner, errorDetails, errorMessage, h } from './dom.js';

export interface AppealModalOptions {
  api: Api;
  evaluationId: string;
  criterion: Criterion;
  /** Вызывается после успешной отправки, когда окно уже закрыто. */
  onSent: () => void;
}

let seq = 0;

/** Модальное окно апелляции; вставляется внутрь `host` (корень .cqa), чтобы работал CSS. */
export function openAppealModal(host: HTMLElement, opts: AppealModalOptions): void {
  const id = `cqa-appeal-modal-${++seq}`;
  const titleId = `${id}-title`;
  const criterionId = `${id}-criterion`;
  const errorsId = `${id}-errors`;
  // Кнопка, с которой открыли окно: после закрытия фокус возвращается к ней.
  const opener = document.activeElement instanceof HTMLElement ? document.activeElement : null;
  let busy = false;

  const title = h('h2', { id: titleId, class: 'cqa-modal-title', tabindex: '-1' }, t.appeal.modalTitle);
  const comment = h('textarea', {
    class: 'cqa-input cqa-textarea',
    rows: 5,
    required: true,
    placeholder: t.appeal.commentPlaceholder,
  });
  const errors = h('div', { id: errorsId, class: 'cqa-form-errors' });
  const submit = h('button', { type: 'submit', class: 'cqa-btn cqa-btn--primary' }, t.appeal.submit);
  const dialog = h('dialog', {
    class: 'cqa-modal',
    'aria-labelledby': titleId,
    'aria-describedby': `${criterionId} ${errorsId}`,
  });

  const setInvalid = (invalid: boolean) => {
    if (invalid) {
      comment.setAttribute('aria-invalid', 'true');
      comment.setAttribute('aria-describedby', errorsId);
    } else {
      comment.removeAttribute('aria-invalid');
      comment.removeAttribute('aria-describedby');
    }
  };
  const showError = (node: HTMLElement) => {
    errors.replaceChildren(node);
    setInvalid(true);
    comment.focus();
  };
  const setBusy = (on: boolean) => {
    busy = on;
    submit.disabled = on;
    submit.textContent = on ? t.appeal.sending : t.appeal.submit;
    if (on) submit.setAttribute('aria-busy', 'true');
    else submit.removeAttribute('aria-busy');
  };

  comment.addEventListener('input', () => {
    if (comment.getAttribute('aria-invalid') === 'true' && comment.value.trim()) {
      errors.replaceChildren();
      setInvalid(false);
    }
  });

  const form = h(
    'form',
    {
      class: 'cqa-form cqa-modal-form',
      novalidate: true,
      onsubmit: async (ev: Event) => {
        ev.preventDefault();
        if (busy) return;
        errors.replaceChildren();
        if (!comment.value.trim()) {
          showError(banner(t.common.commentRequired));
          return;
        }
        setInvalid(false);
        setBusy(true);
        try {
          await opts.api.createAppeal({
            evaluation_id: opts.evaluationId,
            criterion_id: opts.criterion.id,
            comment: comment.value.trim(),
          });
          busy = false;
          dialog.close();
          opts.onSent();
        } catch (e) {
          setBusy(false);
          showError(banner(errorMessage(e), errorDetails(e)));
        }
      },
    },
    h('div', { class: 'cqa-modal-head' }, title),
    h(
      'div',
      { class: 'cqa-modal-body' },
      h(
        'p',
        { id: criterionId, class: 'cqa-modal-criterion' },
        h('span', { class: 'cqa-field-label' }, t.appeal.criterion),
        h('strong', null, `${opts.criterion.id} · ${opts.criterion.title}`),
      ),
      h('label', { class: 'cqa-field' }, h('span', { class: 'cqa-field-label' }, t.appeal.comment), comment),
      errors,
    ),
    h(
      'div',
      { class: 'cqa-form-actions' },
      h('button', { type: 'button', class: 'cqa-btn', onclick: () => dialog.close() }, t.common.cancel),
      submit,
    ),
  );
  dialog.appendChild(form);
  // Escape во время отправки не закрывает окно: запрос уже ушёл.
  dialog.addEventListener('cancel', (e) => {
    if (busy) e.preventDefault();
  });
  dialog.addEventListener('close', () => {
    dialog.remove();
    if (opener?.isConnected) opener.focus();
  });
  host.appendChild(dialog);
  dialog.showModal();
  // На сенсорных экранах не открываем клавиатуру без выбора поля.
  if (matchMedia('(pointer: coarse)').matches) title.focus();
  else comment.focus();
}
