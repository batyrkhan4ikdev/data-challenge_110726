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

function named<T extends HTMLElement>(control: T, path: string): T {
  control.setAttribute('name', path);
  return control;
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
  let saving = false;
  let loadingVersion = false;
  let cleanDraft = JSON.stringify(cl);
  const descriptionsOpen = new WeakMap<Criterion, boolean>();
  const statusSlot = h('div', { class: 'cqa-editor-status' });
  const draftStatus = h('span', { role: 'status', 'aria-live': 'polite' });
  const savebarObserver = new ResizeObserver(([entry]) => {
    const form = root.querySelector<HTMLElement>('.cqa-editor');
    if (form && entry) form.style.setProperty('--cqa-savebar-space', `${Math.ceil(entry.target.getBoundingClientRect().height) + 24}px`);
  });
  const hasChanges = () => !readOnly && JSON.stringify(cl) !== cleanDraft;
  const beforeUnload = (event: BeforeUnloadEvent) => {
    if (!hasChanges() && !saving) return;
    event.preventDefault();
    event.returnValue = '';
  };
  // Маршрутизатор размонтирует экран до hashchange редактора. Предупреждаем
  // при закрытии/перезагрузке страницы, не перехватывая чужую навигацию D365.
  window.addEventListener('beforeunload', beforeUnload, { signal: ctx.signal });
  ctx.signal.addEventListener('abort', () => savebarObserver.disconnect(), { once: true });

  function updateDraftStatus(): void {
    draftStatus.textContent = saving ? t.checklists.saving : readOnly ? t.checklists.readOnly
      : hasChanges() ? t.checklists.draftChanged : t.checklists.draftClean;
  }

  function showStatus(): void {
    statusSlot.replaceChildren(...(status ? [status] : []));
  }

  function markErrors(details: string[] | null): void {
    for (const detail of details ?? []) {
      const path = detail.split(':')[0].replace(/^(body|data)\./, '').replace(/\[(\d+)\]/g, '.$1');
      for (const control of Array.from(root.querySelectorAll<HTMLElement>('[name]'))) {
        if (control.getAttribute('name') !== path) continue;
        control.setAttribute('aria-invalid', 'true');
        control.setAttribute('aria-describedby', 'cqa-editor-error');
        const disclosure = control.closest('details');
        if (disclosure) disclosure.open = true;
      }
    }
  }
  const sumEl = h('span', { class: 'cqa-sum-value' });
  const sumBox = h('div', { class: 'cqa-sum' }, h('span', null, `${t.checklists.sumWeights}: `), sumEl);
  function updateSum(): void {
    const sum = cl.criteria.filter((c) => c.kind !== 'gross_error').reduce((acc, c) => acc + c.weight, 0);
    const ok = Math.abs(sum - 100) < 0.005;
    sumEl.textContent = `${fmt(Math.round(sum * 100) / 100)} · ${ok ? t.checklists.sumOk : t.checklists.sumHint}`;
    sumBox.classList.toggle('is-ok', ok);
    sumBox.classList.toggle('is-off', !ok);
    sumBox.title = ok ? '' : t.checklists.sumHint;
  }

  async function loadVersion(v: number): Promise<void> {
    if (saving || loadingVersion) return;
    if (hasChanges() && !window.confirm(t.checklists.discardDraft)) {
      const picker = root.querySelector<HTMLSelectElement>('.cqa-version-picker select');
      if (picker) picker.value = String(cl.version);
      return;
    }
    loadingVersion = true;
    status = null;
    setBusy();
    try {
      const loaded = await ctx.api.checklist(cl.id, v === latest ? undefined : v);
      if (ctx.signal.aborted) return;
      cl = loaded;
      readOnly = v !== latest;
      cleanDraft = JSON.stringify(cl);
    } catch (e) {
      status = banner(errorMessage(e), errorDetails(e));
    } finally {
      loadingVersion = false;
    }
    if (!ctx.signal.aborted) draw();
  }

  function setBusy(): void {
    const button = root.querySelector<HTMLButtonElement>('button[type="submit"]');
    if (button) {
      button.disabled = saving || loadingVersion;
      button.setAttribute('aria-busy', String(saving));
      button.textContent = saving ? t.checklists.saving : t.checklists.saveVersion;
    }
    const fieldset = root.querySelector<HTMLFieldSetElement>('fieldset');
    if (fieldset) fieldset.disabled = readOnly || saving || loadingVersion;
    const picker = root.querySelector<HTMLSelectElement>('.cqa-version-picker select');
    if (picker) picker.disabled = saving || loadingVersion;
    updateDraftStatus();
  }

  async function save(): Promise<void> {
    if (saving || loadingVersion || readOnly || ctx.signal.aborted) return;
    saving = true;
    status = null;
    showStatus();
    for (const control of Array.from(root.querySelectorAll('[aria-invalid]'))) {
      control.removeAttribute('aria-invalid');
      control.removeAttribute('aria-describedby');
    }
    setBusy();
    try {
      const saved = isNew ? await ctx.api.createChecklist(cl) : await ctx.api.updateChecklist(cl);
      if (ctx.signal.aborted) return;
      if (isNew) history.replaceState(null, '', hrefChecklist(saved.id));
      isNew = false;
      cl = saved;
      latest = saved.version;
      cleanDraft = JSON.stringify(cl);
      status = banner(t.checklists.saved(saved.version), null, 'ok');
      status.append(
        h('p', null, t.checklists.reevaluateHint),
        h('div', { class: 'cqa-editor-success-links' },
          h('a', { href: '#/checklists' }, t.checklists.title),
          h('a', { href: '#/dialogs/DEV' }, t.checklists.toDialogs)),
      );
      draw();
    } catch (e) {
      if (ctx.signal.aborted) return;
      status = banner(errorMessage(e) || t.checklists.validationFailed, errorDetails(e));
      status.id = 'cqa-editor-error';
      showStatus();
      markErrors(errorDetails(e));
    } finally {
      saving = false;
      if (!ctx.signal.aborted) setBusy();
    }
    if (!ctx.signal.aborted) status?.scrollIntoView({
      block: 'start', behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth',
    });
  }

  function move(i: number, delta: number): void {
    const j = i + delta;
    if (j < 0 || j >= cl.criteria.length) return;
    [cl.criteria[i], cl.criteria[j]] = [cl.criteria[j], cl.criteria[i]];
    draw();
    root.querySelectorAll('.cqa-criterion')[j]?.querySelector<HTMLButtonElement>(`[data-move="${delta}"]`)?.focus();
  }

  function stepsEditor(c: Criterion, criterionIndex: number): HTMLElement {
    const steps = c.steps ?? [];
    return h(
      'div',
      { class: 'cqa-steps' },
      h('div', { class: 'cqa-field-label' }, t.checklists.steps),
      steps.map((s, i) =>
        h(
          'div',
          { class: 'cqa-step' },
          field(t.checklists.stepValue, numberInput(s.value, (v) => (s.value = v), { name: `criteria.${criterionIndex}.steps.${i}.value`, step: '1' })),
          field(t.checklists.stepDescription, textInput(s.description, (v) => (s.description = v), { name: `criteria.${criterionIndex}.steps.${i}.description` }), 'cqa-step-description'),
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
    const title = h('h3', null, `${c.id} · ${c.title || t.checklists.addCriterion}`);
    const description = h('details', {
      class: 'cqa-criterion-description',
      open: descriptionsOpen.get(c) ?? !c.description,
      ontoggle: (e: Event) => {
        const details = e.currentTarget as HTMLDetailsElement;
        if (details.isConnected) descriptionsOpen.set(c, details.open);
      },
    },
    h('summary', null, t.checklists.descriptionToggle),
    field(t.checklists.critDescription, h('textarea', {
      name: `criteria.${i}.description`, class: 'cqa-input cqa-textarea', rows: 3, value: c.description,
      oninput: (e: Event) => (c.description = (e.target as HTMLTextAreaElement).value),
    })),
    h('label', { class: 'cqa-field cqa-check' },
      h('input', {
        name: `criteria.${i}.na_allowed`, type: 'checkbox', checked: c.na_allowed,
        onchange: (e: Event) => {
          c.na_allowed = (e.target as HTMLInputElement).checked;
          descriptionsOpen.set(c, true);
          draw();
          root.querySelector<HTMLInputElement>(`[name="criteria.${i}.na_allowed"]`)?.focus();
        },
      }),
      h('span', null, t.checklists.critNaAllowed)),
    c.na_allowed ? field(t.checklists.critNaCondition, textInput(c.na_condition ?? '', (v) => (c.na_condition = v || null), { name: `criteria.${i}.na_condition` })) : null,
    c.answer_type === 'scale' ? stepsEditor(c, i) : null);
    return h('section', { class: 'cqa-criterion', 'data-criterion': c.id },
      h('div', { class: 'cqa-criterion-head' }, title,
        h('div', { class: 'cqa-criterion-tools' },
          h('button', {
            type: 'button', class: 'cqa-btn cqa-btn--small', 'aria-disabled': String(i === 0),
            'data-move': '-1', onclick: () => move(i, -1), 'aria-label': t.common.up, title: t.common.up,
          }, '↑'),
          h('button', {
            type: 'button', class: 'cqa-btn cqa-btn--small', 'aria-disabled': String(i === cl.criteria.length - 1),
            'data-move': '1', onclick: () => move(i, 1), 'aria-label': t.common.down, title: t.common.down,
          }, '↓'),
          h('button', {
            type: 'button', class: 'cqa-btn cqa-btn--small cqa-btn--danger',
            onclick: () => { cl.criteria.splice(i, 1); draw(); },
          }, t.common.remove))),
      h('div', { class: 'cqa-criterion-identity' },
        field(t.checklists.critId, textInput(c.id, (v) => {
          c.id = v;
          title.textContent = `${c.id} · ${c.title}`;
        }, { name: `criteria.${i}.id` })),
        field(t.checklists.critTitle, textInput(c.title, (v) => {
          c.title = v;
          title.textContent = `${c.id} · ${c.title}`;
        }, { name: `criteria.${i}.title` }))),
      h('div', { class: 'cqa-criterion-options' },
        field(t.checklists.critWeight, numberInput(c.weight, (v) => {
          c.weight = v;
          updateSum();
        }, { min: '0', name: `criteria.${i}.weight` })),
        field(t.checklists.critAnswerType, named(select([
          ['yes_no', t.checklists.yesNo], ['scale', t.checklists.scale],
        ], c.answer_type, (v) => {
          c.answer_type = v === 'scale' ? 'scale' : 'yes_no';
          c.steps = c.answer_type === 'scale' ? (c.steps ?? [{ value: 0, description: '' }, { value: 1, description: '' }]) : null;
          if (c.answer_type === 'scale') descriptionsOpen.set(c, true);
          draw();
          root.querySelector<HTMLSelectElement>(`[name="criteria.${i}.answer_type"]`)?.focus();
        }), `criteria.${i}.answer_type`)),
        field(t.checklists.critKind, named(select([
          ['scored', t.checklists.scored], ['gross_error', t.checklists.grossError],
        ], c.kind ?? 'scored', (v) => {
          c.kind = v === 'gross_error' ? 'gross_error' : 'scored';
          updateSum();
        }), `criteria.${i}.kind`)),
        field(t.checklists.critSection, named(select(sectionOptions, c.section_id ?? '', (v) => (c.section_id = v || null)), `criteria.${i}.section_id`))),
      description);
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
          field(t.checklists.sectionTitle, textInput(s.title, (v) => (s.title = v), { name: `sections.${i}.title` }), 'cqa-section-title'),
          field(t.checklists.sectionId, textInput(s.id, (v) => (s.id = v), { name: `sections.${i}.id` }), 'cqa-section-id'),
          h(
            'button',
            {
              type: 'button',
              class: 'cqa-btn cqa-btn--small cqa-btn--danger',
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
        oninput: updateDraftStatus,
        onchange: updateDraftStatus,
        onfocusin: (e: FocusEvent) => {
          const control = e.target as HTMLElement;
          const bar = root.querySelector('.cqa-savebar');
          if (!bar || bar.contains(control)) return;
          if (control.getBoundingClientRect().bottom + 16 > bar.getBoundingClientRect().top) {
            control.scrollIntoView({ block: 'center', behavior: 'auto' });
          }
        },
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
          field(t.checklists.id, textInput(cl.id, (v) => (cl.id = v), { name: 'id', disabled: !isNew, required: true })),
          field(t.checklists.name, textInput(cl.name, (v) => (cl.name = v), { name: 'name' }), 'cqa-span-2'),
          field(
            t.checklists.channel,
            named(select(
              [
                ['', t.checklists.noChannel],
                ['agent chat', t.channel['agent chat']],
                ['voice call', t.channel['voice call']],
              ],
              cl.channel_default ?? '',
              (v) => (cl.channel_default = v === '' ? null : (v as Checklist['channel_default'])),
            ), 'channel_default'),
          ),
          field(t.checklists.notes, h('textarea', { name: 'notes', class: 'cqa-input cqa-textarea', rows: 2, value: cl.notes, oninput: (e: Event) => (cl.notes = (e.target as HTMLTextAreaElement).value) }), 'cqa-span-3'),
          field(t.checklists.source, textInput(cl.source, (v) => (cl.source = v), { name: 'source' })),
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
              root.querySelector<HTMLInputElement>(`[name="criteria.${cl.criteria.length - 1}.title"]`)?.focus();
            },
          },
          t.checklists.addCriterion,
        ),
      ),
      h(
        'div',
        { class: 'cqa-savebar' },
        h('div', { class: 'cqa-savebar-state' }, sumBox, draftStatus),
        readOnly ? null : h('button', { type: 'submit', class: 'cqa-btn cqa-btn--primary', 'aria-busy': 'false' }, t.checklists.saveVersion),
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
      ...(readOnly ? [h('p', { class: 'cqa-editor-readonly' }, t.checklists.readOnly)] : []),
      statusSlot,
      form,
    );
    updateSum();
    showStatus();
    setBusy();
    savebarObserver.disconnect();
    const savebar = root.querySelector('.cqa-savebar');
    if (savebar) savebarObserver.observe(savebar);
  }

  draw();
}
