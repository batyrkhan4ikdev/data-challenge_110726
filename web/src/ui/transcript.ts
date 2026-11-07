import { t } from '../i18n.js';
import type { Record as DialogRecord, Turn } from '../types.gen.js';
import { h } from './dom.js';

export interface TranscriptOptions {
  /** Показать только реплики [from, to] включительно (границы обрезаются по транскрипту). */
  range?: [number, number];
  /** Выставлять id="turn-<idx>" (только когда на странице один транскрипт). */
  ids?: boolean;
  /** Показать плеер для звонков. */
  audio?: boolean;
}

export interface TranscriptView {
  el: HTMLElement;
  audio: HTMLAudioElement | null;
  /** Подсветить реплики-подтверждения (is-evidence) и ожидаемый диапазон (is-expected). */
  highlight(evidence: number[], expected?: [number, number] | null): void;
  /** Прокрутить к реплике и подсветить; на звонках перемотать аудио на offset_s. */
  focusEvidence(idx: number): void;
  focusExpected(range: [number, number]): void;
}

function turnEl(turn: Turn, ids: boolean): HTMLElement {
  return h(
    'div',
    { class: `cqa-turn cqa-turn--${turn.speaker}`, id: ids ? `turn-${turn.idx}` : null, 'data-idx': turn.idx },
    h(
      'div',
      { class: 'cqa-turn-meta' },
      h('span', { class: 'cqa-turn-idx' }, `#${turn.idx}`),
      h('span', { class: 'cqa-turn-speaker' }, t.speaker[turn.speaker] ?? turn.speaker),
      h('time', { class: 'cqa-turn-time' }, turn.timestamp),
    ),
    h('div', { class: 'cqa-turn-text' }, turn.text),
  );
}

export function renderTranscript(record: DialogRecord, opts: TranscriptOptions = {}): TranscriptView {
  const turns = record.transcript;
  const [from, to] = opts.range ?? [0, turns.length - 1];
  const showAudio = (opts.audio ?? true) && record.channel === 'voice call' && !!record.audio_url;
  const audio = showAudio
    ? h('audio', { class: 'cqa-audio', controls: true, preload: 'none', src: record.audio_url, 'aria-label': t.result.audio })
    : null;

  const body = h('div', { class: 'cqa-turns' });
  const byIdx = new Map<number, { turn: Turn; el: HTMLElement }>();
  for (const turn of turns) {
    if (turn.idx < from || turn.idx > to) continue;
    const el = turnEl(turn, opts.ids ?? false);
    byIdx.set(turn.idx, { turn, el });
    body.appendChild(el);
  }
  const el = h('div', { class: 'cqa-transcript' }, audio ? h('div', { class: 'cqa-audio-bar' }, audio) : null, body);

  function highlight(evidence: number[], expected?: [number, number] | null): void {
    for (const { el: e } of byIdx.values()) e.classList.remove('is-evidence', 'is-expected');
    for (const idx of evidence) byIdx.get(idx)?.el.classList.add('is-evidence');
    if (expected) {
      for (let i = expected[0]; i <= expected[1]; i++) byIdx.get(i)?.el.classList.add('is-expected');
    }
  }

  function reveal(idx: number): void {
    const entry = byIdx.get(idx);
    if (!entry) return;
    entry.el.scrollIntoView({ block: 'center', behavior: 'smooth' });
    if (audio && entry.turn.offset_s !== null && entry.turn.offset_s !== undefined) {
      audio.currentTime = entry.turn.offset_s;
    }
  }

  return {
    el,
    audio,
    highlight,
    focusEvidence(idx) {
      highlight([idx]);
      reveal(idx);
    },
    focusExpected(range) {
      highlight([], range);
      reveal(range[0]);
    },
  };
}
