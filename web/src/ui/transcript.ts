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
  /** Disable evidence and expected highlights when transcript/audio identity differs. */
  evidenceEnabled?: boolean;
}

export interface TranscriptView {
  el: HTMLElement;
  audio: HTMLAudioElement | null;
  /** Подсветить реплики-подтверждения (is-evidence) и ожидаемый диапазон (is-expected). */
  highlight(evidence: number[], expected?: [number, number] | null): void;
  /** Прокрутить к реплике и подсветить; на звонках перемотать аудио на offset_s. */
  focusEvidence(idx: number): void;
  focusExpected(range: [number, number]): void;
  setTurns(turns: Turn[]): void;
  setEvidenceEnabled(enabled: boolean): void;
}

/** Для звонков — время от начала записи (мм:сс), для чатов — исходная метка. */
function clock(turn: Turn): string {
  if (turn.offset_s === null || turn.offset_s === undefined) return turn.timestamp;
  const sec = Math.floor(turn.offset_s);
  return `${String(Math.floor(sec / 60)).padStart(2, '0')}:${String(sec % 60).padStart(2, '0')}`;
}

function turnEl(turn: Turn, ids: boolean): HTMLElement {
  return h(
    'div',
    { class: `cqa-turn cqa-turn--${turn.speaker}`, id: ids ? `turn-${turn.idx}` : null, 'data-idx': turn.idx, tabindex: '-1' },
    h(
      'div',
      { class: 'cqa-turn-meta' },
      clock(turn) ? h('time', { class: 'cqa-turn-time', title: turn.timestamp }, clock(turn)) : null,
      h('span', { class: 'cqa-turn-speaker' }, t.speaker[turn.speaker] ?? turn.speaker),
      h('span', { class: 'cqa-turn-idx', title: `№ ${turn.idx + 1}` }, `#${turn.idx + 1}`),
      h('span', { class: 'cqa-turn-marker', hidden: true }),
    ),
    h('div', { class: 'cqa-turn-text' }, turn.text),
  );
}

export function renderTranscript(record: DialogRecord, opts: TranscriptOptions = {}): TranscriptView {
  const [from, to] = opts.range ?? [0, Number.POSITIVE_INFINITY];
  const showAudio = (opts.audio ?? true) && record.channel === 'voice call';
  const audio = showAudio
    ? h('audio', { class: 'cqa-audio', id: opts.ids ? 'cqa-call-audio' : null, controls: true, preload: 'none', src: record.audio_url || null, 'aria-label': t.result.audio })
    : null;
  const audioStatus = h('p', { class: 'cqa-muted', role: 'status' }, record.audio_url ? '' : t.result.audioMissing);
  audio?.addEventListener('error', () => { audioStatus.textContent = t.result.audioError; });
  audio?.addEventListener('loadedmetadata', () => { audioStatus.textContent = ''; });
  const body = h('div', { class: 'cqa-turns' });
  const byIdx = new Map<number, { turn: Turn; el: HTMLElement }>();
  let evidenceEnabled = opts.evidenceEnabled ?? true;
  function setTurns(turns: Turn[]): void {
    byIdx.clear();
    body.replaceChildren();
    for (const turn of turns) {
      if (turn.idx < from || turn.idx > to) continue;
      const turnNode = turnEl(turn, opts.ids ?? false);
      byIdx.set(turn.idx, { turn, el: turnNode });
      body.appendChild(turnNode);
    }
  }
  setTurns(record.transcript);
  const el = h('div', { class: 'cqa-transcript' }, audio ? h('div', { class: 'cqa-audio-bar' }, audio, audioStatus) : null, body);

  function highlight(evidence: number[], expected?: [number, number] | null): void {
    for (const [idx, { el: e }] of byIdx) {
      const isEvidence = evidenceEnabled && evidence.includes(idx);
      const isExpected = evidenceEnabled && !!expected && idx >= expected[0] && idx <= expected[1];
      e.classList.toggle('is-evidence', isEvidence);
      e.classList.toggle('is-expected', isExpected);
      const marker = e.querySelector<HTMLElement>('.cqa-turn-marker')!;
      marker.hidden = !isEvidence && !isExpected;
      marker.textContent = isEvidence ? t.result.fragmentLabel : isExpected ? t.result.expectedLabel : '';
    }
  }

  function reveal(idx: number): void {
    const entry = byIdx.get(idx);
    if (!entry || !evidenceEnabled) return;
    entry.el.focus({ preventScroll: true });
    entry.el.scrollIntoView({ block: 'center', behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
    if (audio && entry.turn.offset_s !== null && entry.turn.offset_s !== undefined) {
      audio.currentTime = entry.turn.offset_s;
    }
  }

  return {
    el,
    audio,
    highlight,
    setTurns,
    setEvidenceEnabled(enabled) {
      evidenceEnabled = enabled;
      if (!enabled) highlight([]);
    },
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
