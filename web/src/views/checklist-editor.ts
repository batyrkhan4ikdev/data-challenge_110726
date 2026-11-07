import { t } from '../i18n.js';
import { hrefChecklist } from '../router.js';
import type { Ctx } from '../router.js';
import type { Checklist, Criterion } from '../types.gen.js';
import { banner, errorDetails, errorMessage, fmt, h } from '../ui/dom.js';

const NEW_ID = 'new';

function emptyChecklist(): Checklist {
  return { id: '', name: '', channel_default: null, version: 1, sections: [], criteria: [], notes: '', source: '' };
}

function nextCriterionId(cl: Checklist): string {
  const nums = cl.criteria.map((c) => Number(/(\d+)$/.exec(c.id)?.[1] ?? 0));
  return `c${String(Math.max(0, ...nums) + 1).padStart(2, '0')}`;
}

function newCriterion(cl: Checklist): Criterion {
  return {
    id: nextCriterionId(cl),
    section_id: cl.sections[0]?.id ?? null,
    title: '',
    description: '',
    answer_type: 'yes_no',
    weight: 0,
    steps: null,
    na_allowed: false,
    na_condition: null,
    kind: 'scored',
  };
}

function field(label: string, control: HTMLElement, cls = ''): HTMLElement {
  return h('label', { class: `cqa-field ${cls}` }, h('span', { class: 'cqa-field-label' }, label), control);
}

function select(options: [string, string][], value: string, onChange: (v: string) => void): HTMLSelectElement {
  return h(
    'select',
    { class: 'cqa-input', value, onchange: (e: Event) => onChange((e.target as HTMLSelectElement).value) },
    options.map(([v, label]) => h('option', { value: v }, label)),
  );
}

function textInput(value: string, onInput: (v: string) => void, extra: { [k: string]: unknown } = {}): HTMLInputElement {
  return h('input', {
    class: 'cqa-input',
    type: 'text',
    value,
    oninput: (e: Event) => onInput((e.target as HTMLInputElement).value),
    ...extra,
  });
}

function numberInput(value: number, onInput: (v: number) => void, extra: { [k: string]: unknown } = {}): HTMLInputElement {
  return h('input', {
    class: 'cqa-input cqa-input--num',
    type: 'number',
    step: 'any',
    value: String(value),
    oninput: (e: Event) => {
      const n = parseFloat((e.target as HTMLInputElement).value);
      onInput(Number.isNaN(n) ? 0 : n);
    },
    ...extra,
  });
}

export async function render(root: HTMLElement, ctx: Ctx): Promise<void> {
  const routeId = ctx.params.id;
  const isNewRoute = routeId === NEW_ID;
  let isNew = isNewRoute;
  let cl: Checklist = isNew ? emptyChecklist() : await ctx.api.checklist(routeId);
  if (ctx.signal.aborted) return;
  let latest = cl.version;
  let readOnly = false;
  let status: HTMLElement | null = null;

  const sumEl = h('span', { class: 'cqa-sum-value' });
  const sumBox = h('div', { class: 'cqa-sum' }, h('span', null, `${t.checklists.sumWeights}: `), sumEl);
  function updateSum(): void {
    const sum = cl.criteria.filter((c) => c.kind !== 'gross_error').reduce((acc, c) => acc + c.weight, 0);
    sumEl.textContent = fmt(Math.round(sum * 100) / 100);
    const ok = Math.abs(sum - 100) < 0.005;
    sumBox.classList.toggle('is-ok', ok);
    sumBox.classList.toggle('is-off', !ok);
    sumBox.title = ok ? '' : t.checklists.sumHint;
  }

  async function loadVersion(v: number): Promise<void> {
    status = null;
    try {
      if (v === latest) {
        cl = await ctx.api.checklist(cl.id);
        readOnly = false;
      } else {
        cl = await ctx.api.checklist(cl.id, v);
        readOnly = true;
      }
    } catch (e) {
      status = banner(errorMessage(e), errorDetails(e));
    }
    draw();
  }

  async function save(): Promise<void> {
    status = null;
    try {
      const saved = isNew ? await ctx.api.createChecklist(cl) : await ctx.api.updateChecklist(cl);
      if (isNew) history.replaceState(null, '', hrefChecklist(saved.id));
      isNew = false;
      cl = saved;
      latest = saved.version;
      status = banner(t.checklists.saved(saved.version), null, 'ok');
    } catch (e) {
      status = banner(errorMessage(e) || t.checklists.validationFailed, errorDetails(e));
    }
    draw();
    root.querySelector('.cqa-banner')?.scrollIntoView({ block: 'start' });
  }

  function move(i: number, delta: number): void {
    const j = i + delta;
    if (j < 0 || j >= cl.criteria.length) return;
    [cl.criteria[i], cl.criteria[j]] = [cl.criteria[j], cl.criteria[i]];
    draw();
  }

  function stepsEditor(c: Criterion): HTMLElement {
    const steps = c.steps ?? [];
    return h(
      'div',
      { class: 'cqa-steps' },
      h('div', { class: 'cqa-field-label' }, t.checklists.steps),
      steps.map((s, i) =>
        h(
          'div',
          { class: 'cqa-step' },
          numberInput(s.value, (v) => (s.value = v), { 'aria-label': t.checklists.stepValue, step: '1' }),
          textInput(s.description, (v) => (s.description = v), { 'aria-label': t.checklists.stepDescription, placeholder: t.checklists.stepDescription }),
          h(
            'button',
            {
              type: 'button',
              class: 'cqa-btn cqa-btn--small',
              onclick: () => {
                steps.splice(i, 1);
                draw();
              },
            },
            t.common.remove,
          ),
        ),
      ),
      h(
        'button',
        {
          type: 'button',
          class: 'cqa-btn cqa-btn--small',
          onclick: () => {
            const next = steps.length ? Math.max(...steps.map((s) => s.value)) + 1 : 0;
            c.steps = [...steps, { value: next, description: '' }];
            draw();
          },
        },
        t.checklists.addStep,
      ),
    );
  }

  function criterionCard(c: Criterion, i: number): HTMLElement {
    const sectionOptions: [string, string][] = [
      ['', t.checklists.noSection],
      ...cl.sections.map((s): [string, string] => [s.id, s.title || s.id]),
    ];
    return h(
      'section',
      { class: 'cqa-criterion', 'data-criterion': c.id },
      h(
        'div',
        { class: 'cqa-criterion-head' },
        h('strong', null, `${i + 1}. ${c.title || c.id}`),
        h(
          'div',
          { class: 'cqa-criterion-tools' },
          h('button', { type: 'button', class: 'cqa-btn cqa-btn--small', disabled: i === 0, onclick: () => move(i, -1), 'aria-label': t.common.up, title: t.common.up }, '↑'),
          h('button', { type: 'button', class: 'cqa-btn cqa-btn--small', disabled: i === cl.criteria.length - 1, onclick: () => move(i, 1), 'aria-label': t.common.down, title: t.common.down }, '↓'),
          h(
            'button',
            {
              type: 'button',
              class: 'cqa-btn cqa-btn--small cqa-btn--danger',
              onclick: () => {
                cl.criteria.splice(i, 1);
                draw();
              },
            },
            t.common.remove,
          ),
        ),
      ),
      h(
        'div',
        { class: 'cqa-grid' },
        field(t.checklists.critId, textInput(c.id, (v) => (c.id = v))),
        field(t.checklists.critTitle, textInput(c.title, (v) => (c.title = v)), 'cqa-span-2'),
        field(
          t.checklists.critSection,
          select(sectionOptions, c.section_id ?? '', (v) => (c.section_id = v || null)),
        ),
        field(
          t.checklists.critKind,
          select(
            [
              ['scored', t.checklists.scored],
              ['gross_error', t.checklists.grossError],
            ],
            c.kind ?? 'scored',
            (v) => {
              c.kind = v === 'gross_error' ? 'gross_error' : 'scored';
              updateSum();
            },
          ),
        ),
        field(
          t.checklists.critAnswerType,
          select(
            [
              ['yes_no', t.checklists.yesNo],
              ['scale', t.checklists.scale],
            ],
            c.answer_type,
            (v) => {
              c.answer_type = v === 'scale' ? 'scale' : 'yes_no';
              c.steps = c.answer_type === 'scale' ? (c.steps ?? [{ value: 0, description: '' }, { value: 1, description: '' }]) : null;
              draw();
            },
          ),
        ),
        field(
          t.checklists.critWeight,
          numberInput(c.weight, (v) => {
            c.weight = v;
            updateSum();
          }, { min: '0' }),
        ),
        field(t.checklists.critDescription, h('textarea', { class: 'cqa-input cqa-textarea', rows: 3, value: c.description, oninput: (e: Event) => (c.description = (e.target as HTMLTextAreaElement).value) }), 'cqa-span-4'),
        h(
          'label',
          { class: 'cqa-field cqa-check' },
          h('input', { type: 'checkbox', checked: c.na_allowed, onchange: (e: Event) => { c.na_allowed = (e.target as HTMLInputElement).checked; draw(); } }),
          h('span', null, t.checklists.critNaAllowed),
        ),
        c.na_allowed
          ? field(t.checklists.critNaCondition, textInput(c.na_condition ?? '', (v) => (c.na_condition = v || null)), 'cqa-span-3')
          : null,
      ),
      c.answer_type === 'scale' ? stepsEditor(c) : null,
    );
  }

  function sectionsEditor(): HTMLElement {
    return h(
      'div',
      { class: 'cqa-sections' },
      h('h2', null, t.checklists.sections),
      cl.sections.map((s, i) =>
        h(
          'div',
          { class: 'cqa-section-row' },
          textInput(s.id, (v) => (s.id = v), { 'aria-label': t.checklists.sectionId, placeholder: t.checklists.sectionId }),
          textInput(s.title, (v) => (s.title = v), { 'aria-label': t.checklists.sectionTitle, placeholder: t.checklists.sectionTitle }),
          h(
            'button',
            {
              type: 'button',
              class: 'cqa-btn cqa-btn--small',
              onclick: () => {
                cl.sections.splice(i, 1);
                draw();
              },
            },
            t.common.remove,
          ),
        ),
      ),
      h(
        'button',
        {
          type: 'button',
          class: 'cqa-btn cqa-btn--small',
          onclick: () => {
            cl.sections.push({ id: `s${cl.sections.length + 1}`, title: '' });
            draw();
          },
        },
        t.checklists.addSection,
      ),
    );
  }

  function versionPicker(): HTMLElement | null {
    if (isNew) return null;
    const versions = Array.from({ length: latest }, (_, i) => latest - i);
    return field(
      t.checklists.versionLabel,
      select(
        versions.map((v): [string, string] => [String(v), v === latest ? `v${v} (${t.checklists.currentSuffix})` : `v${v}`]),
        String(cl.version),
        (v) => void loadVersion(Number(v)),
      ),
      'cqa-version-picker',
    );
  }

  function draw(): void {
    const form = h(
      'form',
      {
        class: 'cqa-form cqa-editor',
        novalidate: true,
        onsubmit: (e: Event) => {
          e.preventDefault();
          void save();
        },
      },
      h(
        'fieldset',
        { class: 'cqa-fieldset', disabled: readOnly },
        h(
          'div',
          { class: 'cqa-grid' },
          field(t.checklists.id, textInput(cl.id, (v) => (cl.id = v), { disabled: !isNew, required: true })),
          field(t.checklists.name, textInput(cl.name, (v) => (cl.name = v)), 'cqa-span-2'),
          field(
            t.checklists.channel,
            select(
              [
                ['', t.checklists.noChannel],
                ['agent chat', t.channel['agent chat']],
                ['voice call', t.channel['voice call']],
              ],
              cl.channel_default ?? '',
              (v) => (cl.channel_default = v === '' ? null : (v as Checklist['channel_default'])),
            ),
          ),
          field(t.checklists.notes, h('textarea', { class: 'cqa-input cqa-textarea', rows: 2, value: cl.notes, oninput: (e: Event) => (cl.notes = (e.target as HTMLTextAreaElement).value) }), 'cqa-span-3'),
          field(t.checklists.source, textInput(cl.source, (v) => (cl.source = v))),
        ),
        sectionsEditor(),
        h('h2', null, t.checklists.criteria),
        cl.criteria.map(criterionCard),
        h(
          'button',
          {
            type: 'button',
            class: 'cqa-btn',
            onclick: () => {
              cl.criteria.push(newCriterion(cl));
              draw();
              root.querySelector('.cqa-criterion:last-of-type')?.scrollIntoView({ block: 'center' });
            },
          },
          t.checklists.addCriterion,
        ),
      ),
      h(
        'div',
        { class: 'cqa-savebar' },
        sumBox,
        readOnly
          ? h('span', { class: 'cqa-muted' }, t.checklists.readOnly)
          : h('button', { type: 'submit', class: 'cqa-btn cqa-btn--primary' }, t.common.save),
        readOnly ? h('button', { type: 'button', class: 'cqa-btn', onclick: () => void loadVersion(latest) }, t.checklists.backToCurrent) : null,
      ),
    );

    root.replaceChildren(
      h(
        'div',
        { class: 'cqa-heading' },
        h('h1', null, isNew ? t.checklists.editorNew : cl.name || cl.id),
        h('a', { class: 'cqa-link', href: '#/checklists' }, `← ${t.checklists.title}`),
        versionPicker(),
      ),
      ...(status ? [status] : []),
      form,
    );
    updateSum();
  }

  draw();
}
