import type { Api } from '../api.js';
import { t } from '../i18n.js';
import type { Record as DialogRecord } from '../types.gen.js';
import { banner, errorDetails, errorMessage, h } from './dom.js';

export interface CustomTranscriptModalOptions {
  api: Api;
  group: string;
  cid: string;
  /** Вызывается после успешного сохранения, до закрытия окна. */
  onSaved: (record: DialogRecord) => void;
}

/** Модальное окно «Вставить свой транскрипт»; вставляется внутрь `host` (корень .cqa), чтобы работал CSS. */
export function openCustomTranscriptModal(host: HTMLElement, opts: CustomTranscriptModalOptions): void {
  const text = h('textarea', {
    class: 'cqa-input cqa-textarea cqa-transcript-input',
    rows: 12,
    required: true,
    placeholder: t.transcripts.pastePlaceholder,
    'aria-label': t.transcripts.pasteText,
  });
  const errors = h('div', { class: 'cqa-form-errors' });
  const submit = h('button', { type: 'submit', class: 'cqa-btn cqa-btn--primary' }, t.transcripts.pasteSave);
  const dialog = h('dialog', { class: 'cqa-modal cqa-modal--wide', 'aria-label': t.transcripts.pasteTitle });

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
        if (!text.value.trim()) {
          errors.appendChild(banner(t.transcripts.pasteRequired));
          text.focus();
          return;
        }
        submit.disabled = true;
        try {
          const record = await opts.api.putCustomTranscript(opts.cid, { group_id: opts.group, text: text.value });
          opts.onSaved(record);
          close();
        } catch (e) {
          errors.appendChild(banner(errorMessage(e), errorDetails(e)));
          submit.disabled = false;
        }
      },
    },
    h('h2', null, t.transcripts.pasteTitle),
    h('p', { class: 'cqa-muted' }, t.transcripts.pasteHint),
    h('label', { class: 'cqa-field' }, h('span', null, t.transcripts.pasteText), text),
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
  text.focus();
}
