import { ApiFail } from '../api.js';
import { t } from '../i18n.js';
import type { Criterion } from '../types.gen.js';

export type Child = Node | string | number | null | undefined | false | Child[];
export type Attrs = { [k: string]: unknown };

const PROPERTY_ATTRS = new Set(['value', 'checked', 'disabled', 'selected', 'indeterminate']);

function append(parent: Node, children: Child[]): void {
  for (const c of children) {
    if (c === null || c === undefined || c === false) continue;
    if (Array.isArray(c)) append(parent, c);
    else parent.appendChild(typeof c === 'object' ? c : document.createTextNode(String(c)));
  }
}

/** Мини-конструктор DOM: h('div', {class: 'x', onclick: fn}, 'текст', child). */
export function h<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  attrs?: Attrs | null,
  ...children: Child[]
): HTMLElementTagNameMap[K] {
  const el = document.createElement(tag);
  const props: [string, unknown][] = [];
  for (const [k, v] of Object.entries(attrs ?? {})) {
    if (v === null || v === undefined || v === false) continue;
    if (k.startsWith('on') && typeof v === 'function') el.addEventListener(k.slice(2).toLowerCase(), v as EventListener);
    else if (k === 'class') el.className = String(v);
    // Строка style через setAttribute нарушает строгий CSP (style-src-attr); запись через CSSOM разрешена.
    else if (k === 'style') el.style.cssText = String(v);
    else if (PROPERTY_ATTRS.has(k)) props.push([k, v]);
    else el.setAttribute(k, v === true ? '' : String(v));
  }
  append(el, children);
  // value у <select> выставляется только после добавления <option>.
  for (const [k, v] of props) Reflect.set(el, k, v);
  return el;
}

export function clear(el: HTMLElement): void {
  el.replaceChildren();
}

export function badge(text: string, tone: 'good' | 'bad' | 'warn' | 'neutral' | 'info' = 'neutral', title?: string): HTMLElement {
  return h('span', { class: `cqa-badge cqa-badge--${tone}`, title }, text);
}

export function banner(text: string, details?: string[] | null, tone: 'error' | 'ok' | 'info' = 'error'): HTMLElement {
  return h(
    'div',
    { class: `cqa-banner cqa-banner--${tone}`, role: tone === 'error' ? 'alert' : 'status' },
    h('strong', null, text),
    details && details.length ? h('ul', null, details.map((d) => h('li', null, d))) : null,
  );
}

export function heading(text: string, ...extra: Child[]): HTMLElement {
  return h('div', { class: 'cqa-heading' }, h('h1', null, text), ...extra);
}

const numberFormat = new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 2 });

export function fmt(n: number | null | undefined): string {
  return n === null || n === undefined ? t.common.none : numberFormat.format(n);
}

export function fmtDate(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString('ru-RU', { dateStyle: 'short', timeStyle: 'short' });
}

/** Те же допустимые вердикты, что у server.scoring.allowed_verdicts. */
export function allowedVerdicts(c: Criterion): string[] {
  const verdicts =
    c.answer_type === 'yes_no'
      ? ['yes', 'no']
      : (c.steps ?? [])
          .map((s) => s.value)
          .sort((a, b) => a - b)
          .map(String);
  if (c.na_allowed) verdicts.push('na');
  return verdicts;
}

/** Подпись вердикта: Да / Нет / N/A / значение ступени. */
export function verdictLabel(verdict: string): string {
  if (verdict === 'yes') return t.common.yes;
  if (verdict === 'no') return t.common.no;
  if (verdict === 'na') return t.common.na;
  return verdict;
}

export type Tone = 'good' | 'bad' | 'warn' | 'neutral';

/** Цвет вердикта: для грубой ошибки «Да» — плохо. */
export function verdictTone(c: Criterion | undefined, verdict: string): Tone {
  if (verdict === 'na') return 'neutral';
  if (c?.kind === 'gross_error') return verdict === 'yes' ? 'bad' : 'good';
  if (c?.answer_type === 'scale') {
    const values = (c.steps ?? []).map((s) => s.value);
    const v = Number(verdict);
    if (values.length && v === Math.max(...values)) return 'good';
    if (values.length && v === Math.min(...values)) return 'bad';
    return 'warn';
  }
  return verdict === 'yes' ? 'good' : 'bad';
}

/** Описание ступени шкалы по значению вердикта. */
export function stepDescription(c: Criterion | undefined, verdict: string): string | null {
  const step = c?.steps?.find((s) => String(s.value) === verdict);
  return step ? step.description : null;
}

/** Пара чисел из expected_range (контракт: [unknown, unknown] | null). */
export function rangeOf(range: [unknown, unknown] | null | undefined): [number, number] | null {
  if (!range) return null;
  const a = Number(range[0]);
  const b = Number(range[1]);
  return Number.isFinite(a) && Number.isFinite(b) ? [Math.min(a, b), Math.max(a, b)] : null;
}

export function errorMessage(e: unknown): string {
  return e instanceof Error ? e.message : String(e);
}

export function errorDetails(e: unknown): string[] | null {
  return e instanceof ApiFail ? e.details : null;
}
