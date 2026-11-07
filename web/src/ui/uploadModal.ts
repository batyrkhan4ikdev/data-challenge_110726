import type { Api, UploadLanguage } from '../api.js';
import { t } from '../i18n.js';
import type { Record as DialogRecord } from '../types.gen.js';
import { banner, errorDetails, errorMessage, h } from './dom.js';

export interface UploadModalOptions {
  api: Api;
  /** Вызывается после добавления диалога, до закрытия окна. */
  onAdded: (record: DialogRecord) => void;
}

/** Предпочтительная модель для загрузки: единственная, что понимает казахский и различает говорящих. */
const PREFERRED_PROVIDER = 'h200-whisperx';

/** Окно «Загрузить звонок или чат»: новый диалог в группе UPLOADS. Вставляется внутрь `host` (корень .cqa). */
export function openUploadModal(host: HTMLElement, opts: UploadModalOptions): void {
  const u = t.uploads;
  let kind: 'call' | 'chat' = 'call';

  const languageSelect = (withAuto: boolean) =>
    h(
      'select',
      { class: 'cqa-input', 'aria-label': u.language },
      ...(withAuto ? [h('option', { value: 'auto' }, u.auto)] : []),
      h('option', { value: 'RU' }, 'RU'),
      h('option', { value: 'KZ' }, 'KZ'),
      h('option', { value: 'EN' }, 'EN'),
    );

  const file = h('input', { class: 'cqa-input', type: 'file', accept: '.mp3,.wav,.ogg,.m4a,.webm,.flac,audio/*', 'aria-label': u.file });
  const callLanguage = languageSelect(true);
  const provider = h('select', { class: 'cqa-input', 'aria-label': u.provider, disabled: true });
  const chatText = h('textarea', {
    class: 'cqa-input cqa-textarea cqa-transcript-input',
    rows: 10,
    placeholder: u.chatPlaceholder,
    'aria-label': u.chatText,
  });
  const chatLanguage = languageSelect(false);

  const callFields = h(
    'div',
    { class: 'cqa-upload-fields' },
    h('label', { class: 'cqa-field' }, h('span', null, u.file), file, h('small', { class: 'cqa-muted' }, u.fileHint)),
    h('label', { class: 'cqa-field' }, h('span', null, u.language), callLanguage),
    h('label', { class: 'cqa-field' }, h('span', null, u.provider), provider),
  );
  const chatFields = h(
    'div',
    { class: 'cqa-upload-fields', hidden: true },
    h('label', { class: 'cqa-field' }, h('span', null, u.chatText), chatText),
    h('label', { class: 'cqa-field' }, h('span', null, u.language), chatLanguage),
  );

  const errors = h('div', { class: 'cqa-form-errors' });
  const status = h('p', { class: 'cqa-muted', role: 'status' });
  const submit = h('button', { type: 'submit', class: 'cqa-btn cqa-btn--primary' }, u.submitCall);

  const tabButton = (which: 'call' | 'chat', label: string) =>
    h('button', { type: 'button', class: 'cqa-btn', role: 'tab', 'aria-selected': String(which === kind), onclick: () => select(which) }, label);
  const callTab = tabButton('call', u.tabCall);
  const chatTab = tabButton('chat', u.tabChat);

  function select(which: 'call' | 'chat'): void {
    kind = which;
    callFields.hidden = which !== 'call';
    chatFields.hidden = which !== 'chat';
    callTab.setAttribute('aria-selected', String(which === 'call'));
    chatTab.setAttribute('aria-selected', String(which === 'chat'));
    callTab.classList.toggle('cqa-btn--primary', which === 'call');
    chatTab.classList.toggle('cqa-btn--primary', which === 'chat');
    submit.textContent = which === 'call' ? u.submitCall : u.submitChat;
    errors.replaceChildren();
  }

  const dialog = h('dialog', { class: 'cqa-modal cqa-modal--wide', 'aria-label': u.title });
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
        if (kind === 'call' && !file.files?.length) {
          errors.appendChild(banner(u.fileRequired));
          return;
        }
        if (kind === 'chat' && !chatText.value.trim()) {
          errors.appendChild(banner(u.textRequired));
          chatText.focus();
          return;
        }
        submit.disabled = true;
        status.textContent = kind === 'call' ? u.working : '';
        try {
          const record =
            kind === 'call'
              ? await opts.api.uploadCall(file.files![0]!, callLanguage.value as UploadLanguage, provider.value)
              : await opts.api.uploadChat({ text: chatText.value, language: chatLanguage.value as 'RU' | 'KZ' | 'EN' });
          opts.onAdded(record);
          close();
        } catch (e) {
          status.textContent = '';
          errors.appendChild(banner(errorMessage(e), errorDetails(e)));
          submit.disabled = false;
        }
      },
    },
    h('h2', null, u.title),
    h('p', { class: 'cqa-muted' }, u.hint),
    h('div', { class: 'cqa-toolbar', role: 'tablist' }, callTab, chatTab),
    callFields,
    chatFields,
    errors,
    status,
    h('div', { class: 'cqa-form-actions' }, submit, h('button', { type: 'button', class: 'cqa-btn', onclick: close }, t.common.cancel)),
  );
  dialog.appendChild(form);
  dialog.addEventListener('cancel', () => dialog.remove());
  host.appendChild(dialog);
  dialog.showModal();
  select('call');

  void opts.api
    .asrProviders()
    .then((list) => {
      const usable = list.filter((p) => p.available);
      if (!usable.length) {
        errors.appendChild(banner(u.noProviders));
        return;
      }
      provider.replaceChildren(
        ...usable.map((p) => h('option', { value: p.id }, `${p.label}${p.hosting === 'local' ? '' : ' · облако'}`)),
      );
      provider.value = usable.some((p) => p.id === PREFERRED_PROVIDER) ? PREFERRED_PROVIDER : usable[0]!.id;
      provider.disabled = false;
    })
    .catch((e: unknown) => errors.appendChild(banner(errorMessage(e), errorDetails(e))));
}
