import { t } from '../i18n.js';
import { h } from './dom.js';

export interface CallProvider {
  id: string;
  label: string;
  available: boolean;
  note?: string | null;
}
export interface CallVariant {
  source: string;
  audioId?: string | null;
  label: string;
}
export type CallUploadState =
  | { state: 'none' }
  | { state: 'selected'; fileName: string }
  | { state: 'uploading'; fileName: string; progress: number | null }
  | { state: 'error'; kind: 'format' | 'size' | 'other'; message?: string }
  | { state: 'ready'; fileName?: string };
export type CallRecognitionState =
  | { state: 'idle' }
  | { state: 'running'; elapsedSeconds?: number }
  | { state: 'done' }
  | { state: 'error'; kind: 'blocked' | 'limit' | 'other'; message?: string };
export interface CallPanelProps {
  /** Unique DOM/radio namespace when more than one panel is mounted. */
  id: string;
  providers: CallProvider[];
  selectedProvider: string | null;
  audioSource: 'none' | 'recording' | 'upload';
  maxUploadBytes: number;
  upload: CallUploadState;
  recognition: CallRecognitionState;
  variants: CallVariant[];
  activeVariant: CallVariant | null;
  /** Missing source means the organizers' transcript; audio identity must also match. */
  evaluatedSource?: string | null;
  evaluatedAudioId?: string | null;
  evaluatedLabel?: string;
  onSelectProvider(id: string): void;
  /** File choice/drop only; the owner validates, uploads and supplies updated state. */
  onUpload(file: File): void;
  onRecognize(): void;
  onRetry(): void;
  onSelectVariant(variant: CallVariant): void;
}

/** Apply this same result to score jumps, table links and TranscriptOptions.evidenceEnabled. */
export function callEvidenceGuard(active: { source: string; audioId?: string | null } | null,
  evaluatedSource?: string | null, evaluatedAudioId?: string | null): { evidenceEnabled: boolean; message: string } {
  const evidenceEnabled = !!active && active.source === (evaluatedSource ?? 'organizers')
    && (active.audioId ?? null) === (evaluatedAudioId ?? null);
  return { evidenceEnabled, message: evidenceEnabled ? '' : t.call.mismatch };
}

/** Presentational only. No API calls or player: the caller keeps one native audio element. */
export function renderCallPanel(props: CallPanelProps): HTMLElement {
  const { upload, recognition } = props;
  const busy = upload.state === 'uploading' || recognition.state === 'running';
  const guard = callEvidenceGuard(props.activeVariant, props.evaluatedSource, props.evaluatedAudioId);
  const selectedProvider = props.providers.find((p) => p.id === props.selectedProvider);
  const input = h('input', { type: 'file', accept: '.mp3,.wav', hidden: true, 'aria-label': t.call.upload });
  input.addEventListener('change', () => {
    const file = input.files?.[0];
    if (file && !busy) props.onUpload(file);
    input.value = '';
  });
  const choose = h('button', { type: 'button', class: 'cqa-btn cqa-btn--small', disabled: busy, onclick: () => input.click() }, t.call.upload);
  const uploadText = upload.state === 'none' ? (props.audioSource === 'recording' ? t.call.recording : t.call.noFile)
    : upload.state === 'selected' ? t.call.selected(upload.fileName)
    : upload.state === 'uploading' ? `${t.call.uploading} ${upload.fileName}`
    : upload.state === 'ready' ? t.call.ready
    : upload.kind === 'format' ? t.call.formatError : upload.kind === 'size' ? t.call.sizeError : upload.message ?? t.call.uploadError;
  const progress = upload.state === 'uploading' ? h('progress', {
    max: 100, value: upload.progress === null ? null : Math.max(0, Math.min(100, upload.progress)), 'aria-label': t.call.uploading,
  }) : null;
  const drop = h('div', { class: 'cqa-call-drop' }, h('p', null, t.call.drop),
    h('p', { class: 'cqa-muted' }, t.call.limits(Math.round(props.maxUploadBytes / 1024 / 1024))), input, choose,
    h('p', { class: upload.state === 'error' ? 'cqa-call-error' : 'cqa-muted', role: 'status' }, uploadText), progress);
  drop.addEventListener('dragover', (event) => { event.preventDefault(); if (!busy) drop.classList.add('is-dragging'); });
  drop.addEventListener('dragleave', () => drop.classList.remove('is-dragging'));
  drop.addEventListener('drop', (event) => {
    event.preventDefault();
    drop.classList.remove('is-dragging');
    const file = event.dataTransfer?.files[0];
    if (file && !busy) props.onUpload(file);
  });
  const providers = h('fieldset', { class: 'cqa-call-providers' }, h('legend', null, t.call.provider));
  for (const p of props.providers) {
    const radio = h('input', { type: 'radio', name: `${props.id}-provider`, value: p.id, checked: p.id === props.selectedProvider, disabled: busy || !p.available });
    const noteId = `${props.id}-note-${p.id}`;
    if (p.note || !p.available) radio.setAttribute('aria-describedby', noteId);
    radio.addEventListener('change', () => { if (radio.checked) props.onSelectProvider(p.id); });
    providers.appendChild(h('label', { class: 'cqa-call-provider' }, radio, h('span', null, h('strong', null, p.label),
      p.note || !p.available ? h('span', { class: 'cqa-muted', id: noteId }, p.note || t.call.unavailable) : null)));
  }
  const recognitionText = recognition.state === 'idle' ? '' : recognition.state === 'done' ? t.call.done
    : recognition.state === 'running' ? recognition.elapsedSeconds === undefined ? t.call.running : t.call.elapsed(recognition.elapsedSeconds)
    : recognition.kind === 'blocked' ? t.call.blocked : recognition.kind === 'limit' ? t.call.keyLimit : recognition.message ?? t.call.providerError;
  const action = h('button', {
    type: 'button', class: 'cqa-btn cqa-btn--tint', 'aria-busy': String(recognition.state === 'running'),
    disabled: busy || !selectedProvider?.available || props.audioSource === 'none' || upload.state === 'selected',
    onclick: () => recognition.state === 'error' ? props.onRetry() : props.onRecognize(),
  }, recognition.state === 'running' ? t.call.running : recognition.state === 'error' ? t.call.retry : t.call.recognize);
  const switcher = h('select', { class: 'cqa-input', disabled: busy || !props.variants.length, 'aria-label': t.call.variants },
    props.variants.map((v, index) => h('option', { value: index, selected: v.source === props.activeVariant?.source && (v.audioId ?? null) === (props.activeVariant?.audioId ?? null) }, v.label)));
  if (!props.activeVariant) switcher.selectedIndex = -1;
  switcher.addEventListener('change', () => { const variant = props.variants[Number(switcher.value)]; if (variant) props.onSelectVariant(variant); });
  const evaluatedLabel = props.evaluatedLabel ?? props.variants.find((v) => v.source === (props.evaluatedSource ?? 'organizers'))?.label
    ?? (props.evaluatedSource ?? t.call.organizers);
  return h('section', { class: 'cqa-call-panel', 'aria-label': t.call.title, 'aria-busy': String(busy) },
    h('h3', null, t.call.title), drop, providers,
    h('div', { class: 'cqa-call-actions' }, action, h('div', { class: 'cqa-call-status', role: 'status' }, recognitionText)),
    props.variants.length ? h('label', { class: 'cqa-field' }, h('span', { class: 'cqa-field-label' }, t.call.variants), switcher) : null,
    h('p', { class: 'cqa-muted cqa-score-source' }, t.call.scoredOn(evaluatedLabel)),
    guard.evidenceEnabled ? null : h('p', { class: 'cqa-banner cqa-banner--info', role: 'status' }, guard.message));
}
