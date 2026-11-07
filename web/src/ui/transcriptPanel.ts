import type { Api } from '../api.js';
import { t } from '../i18n.js';
import type { Record as DialogRecord, TranscriptSourceInfo } from '../types.gen.js';
import { openCustomTranscriptModal } from './customTranscriptModal.js';
import { badge, banner, errorDetails, errorMessage, fmt, h } from './dom.js';
import { renderTranscript } from './transcript.js';
import type { TranscriptView } from './transcript.js';

export const API_SOURCE = 'api';
/** Транскрипт, который для звонков показывается по умолчанию, если он есть. */
export const PREFERRED_CALL_SOURCE = 'freedomspeech';

const API_ONLY: TranscriptSourceInfo[] = [{ source: API_SOURCE, label: t.transcripts.api, kind: 'api', available: true }];

/** Список источников транскрипта звонка; при ошибке — только транскрипт организатора. */
export async function loadSources(api: Api, cid: string): Promise<TranscriptSourceInfo[]> {
  try {
    const sources = await api.transcripts(cid);
    return sources.some((s) => s.source === API_SOURCE) ? sources : [...API_ONLY, ...sources];
  } catch {
    return API_ONLY;
  }
}

/** FreedomSpeech, если он есть, иначе транскрипт организатора. */
export function defaultSource(sources: TranscriptSourceInfo[]): string {
  return sources.some((s) => s.source === PREFERRED_CALL_SOURCE && s.available) ? PREFERRED_CALL_SOURCE : API_SOURCE;
}

export function sourceLabel(sources: TranscriptSourceInfo[], source: string): string {
  return sources.find((s) => s.source === source)?.label ?? (source === API_SOURCE ? t.transcripts.api : source);
}

const pct = (x: number) => fmt(Math.round(x * 1000) / 10);

/** Бейдж качества источника: ручная оценка, иначе CER и попадания оценщика; в подсказке — всё, что известно. */
function qualityBadge(s: TranscriptSourceInfo): HTMLElement | null {
  const q = s.quality;
  if (!q) return null;
  const q18 = t.transcripts.quality;
  const has = (x: number | null | undefined): x is number => x !== null && x !== undefined;
  const cer = has(q.cer_vs_freedomspeech) ? q18.cerFs(pct(q.cer_vs_freedomspeech)) : has(q.cer_vs_api) ? q18.cerApi(pct(q.cer_vs_api)) : null;
  const gold = has(q.gold_hits) && has(q.gold_total) ? q18.gold(q.gold_hits, q.gold_total) : null;
  const text = has(q.manual_score) ? q18.manual(fmt(q.manual_score)) : [cer, gold].filter(Boolean).join(' · ') || null;
  const parts = [
    has(q.cer_vs_freedomspeech) ? q18.cerFs(pct(q.cer_vs_freedomspeech)) : null,
    has(q.cer_vs_api) ? q18.cerApi(pct(q.cer_vs_api)) : null,
    gold,
    q.diarized === null || q.diarized === undefined ? null : q.diarized ? q18.diarized : q18.notDiarized,
    has(q.speaker_turns) ? q18.turns(fmt(q.speaker_turns)) : null,
    has(q.seconds_per_min) ? q18.speed(fmt(q.seconds_per_min)) : null,
    q.notes,
  ].filter((x): x is string => !!x);
  if (!text) return null;
  return badge(text, 'info', parts.join(' · '));
}

export interface TranscriptPanelOptions {
  api: Api;
  /** Корень .cqa: внутрь вставляется модальное окно. */
  host: HTMLElement;
  signal: AbortSignal;
  group: string;
  cid: string;
  sources: TranscriptSourceInfo[];
  /** Источник, открытый сначала. */
  initial: string;
  /** Источник, по которому сделана показанная оценка: ссылки на реплики и подсветка относятся к нему. */
  evaluated?: string;
  /** «Оценить по этому транскрипту». */
  onEvaluate?: (source: string, status: HTMLElement, setBusy: (busy: boolean) => void) => void;
}

export interface TranscriptPanel {
  el: HTMLElement;
  /** Открыть реплику в транскрипте оценки (переключает источник, если открыт другой). */
  focusEvidence(idx: number): Promise<void>;
  focusExpected(range: [number, number]): Promise<void>;
}

/** Транскрипт звонка с переключателем источников, распознаванием заново и вставкой своего текста. */
export function createTranscriptPanel(opts: TranscriptPanelOptions): TranscriptPanel {
  let sources = opts.sources;
  let current = sources.some((s) => s.source === opts.initial && s.available) ? opts.initial : API_SOURCE;
  let view: TranscriptView | null = null;
  let shown = 0; // отбрасывает ответы устаревших переключений
  const cache = new Map<string, DialogRecord>();

  const bar = h('div', { class: 'cqa-seg', role: 'group', 'aria-label': t.transcripts.switchLabel });
  const providerSelect = h('select', { class: 'cqa-input', 'aria-label': t.transcripts.providerLabel });
  const rerunBtn = h('button', { type: 'button', class: 'cqa-btn cqa-btn--outline cqa-btn--small', id: 'cqa-rerun-asr' }, t.transcripts.rerun);
  const pasteBtn = h('button', { type: 'button', class: 'cqa-btn cqa-btn--outline cqa-btn--small', id: 'cqa-paste-transcript' }, t.transcripts.paste);
  const evalBtn = opts.onEvaluate
    ? h('button', { type: 'button', class: 'cqa-btn cqa-btn--primary cqa-btn--small', id: 'cqa-evaluate-source' }, t.transcripts.evaluate)
    : null;
  const note = h('div', { class: 'cqa-tsrc-note cqa-muted' });
  const status = h('div', { class: 'cqa-status cqa-tsrc-status' });
  const body = h('div', { class: 'cqa-tsrc-body' });
  const asrRow = h('div', { class: 'cqa-tsrc-asr' }, providerSelect, rerunBtn);

  const setBusy = (busy: boolean) => {
    rerunBtn.disabled = busy;
    providerSelect.disabled = busy;
    pasteBtn.disabled = busy;
    if (evalBtn) evalBtn.disabled = busy;
  };

  function renderBar(): void {
    bar.replaceChildren(
      h('span', { class: 'cqa-muted cqa-seg-label' }, t.transcripts.switchLabel),
      ...sources
        .filter((s) => s.available)
        .map((s) =>
          h(
            'button',
            {
              type: 'button',
              class: `cqa-seg-btn${s.source === current ? ' is-active' : ''}`,
              'aria-pressed': String(s.source === current),
              'data-source': s.source,
              onclick: () => void show(s.source),
            },
            h('span', null, s.label),
            qualityBadge(s),
          ),
        ),
    );
    const asr = sources.filter((s) => s.kind === 'asr');
    providerSelect.replaceChildren(
      ...asr.map((s) => h('option', { value: s.source }, s.provider_hosting === 'local' ? `${s.label} · local` : s.label)),
    );
    const pick = asr.find((s) => s.source === current) ?? asr.find((s) => s.source === PREFERRED_CALL_SOURCE) ?? asr[0];
    if (pick) providerSelect.value = pick.source;
    asrRow.hidden = asr.length === 0;
    if (evalBtn) evalBtn.title = sourceLabel(sources, current);
    note.textContent =
      opts.evaluated && opts.evaluated !== current ? t.transcripts.evaluatedNote(sourceLabel(sources, opts.evaluated)) : '';
  }

  async function show(source: string): Promise<void> {
    const ticket = ++shown;
    current = source;
    renderBar();
    let record = cache.get(source);
    if (!record) {
      body.replaceChildren(h('span', { class: 'cqa-muted' }, t.common.loading));
      try {
        record = await opts.api.record(opts.group, opts.cid, source);
      } catch (e) {
        if (ticket === shown) body.replaceChildren(banner(t.transcripts.recordFailed, [errorMessage(e)]));
        return;
      }
      cache.set(source, record);
    }
    if (ticket !== shown || opts.signal.aborted) return;
    view = renderTranscript(record, { ids: true });
    body.replaceChildren(view.el);
  }

  async function refresh(select: string): Promise<void> {
    sources = await loadSources(opts.api, opts.cid);
    cache.delete(select);
    await show(select);
  }

  rerunBtn.addEventListener('click', async () => {
    const provider = providerSelect.value;
    if (!provider) return;
    const label = sourceLabel(sources, provider);
    const started = Date.now();
    const tick = () => status.replaceChildren(h('span', { class: 'cqa-muted' }, t.transcripts.recognizing(Math.round((Date.now() - started) / 1000))));
    tick();
    const timer = window.setInterval(tick, 1000);
    opts.signal.addEventListener('abort', () => window.clearInterval(timer));
    setBusy(true);
    try {
      await opts.api.transcribe(opts.cid, { group_id: opts.group, provider });
      window.clearInterval(timer);
      await refresh(provider);
      status.replaceChildren(banner(t.transcripts.recognized(label), null, 'ok'));
    } catch (e) {
      window.clearInterval(timer);
      status.replaceChildren(banner(errorMessage(e), errorDetails(e)));
    } finally {
      window.clearInterval(timer);
      setBusy(false);
    }
  });

  pasteBtn.addEventListener('click', () =>
    openCustomTranscriptModal(opts.host, {
      api: opts.api,
      group: opts.group,
      cid: opts.cid,
      onSaved: () => {
        status.replaceChildren();
        void refresh('custom');
      },
    }),
  );

  evalBtn?.addEventListener('click', () => opts.onEvaluate?.(current, status, setBusy));

  async function focusSource(): Promise<void> {
    if (opts.evaluated && opts.evaluated !== current) await show(opts.evaluated);
  }

  const el = h(
    'div',
    { class: 'cqa-tsrc' },
    bar,
    h('div', { class: 'cqa-tsrc-actions' }, asrRow, pasteBtn, evalBtn),
    status,
    note,
    body,
  );
  void show(current);

  return {
    el,
    async focusEvidence(idx) {
      await focusSource();
      view?.focusEvidence(idx);
    },
    async focusExpected(range) {
      await focusSource();
      view?.focusExpected(range);
    },
  };
}
