const NS = 'http://www.w3.org/2000/svg';

/** Один <path>/<circle> и т. п. внутри <svg>: [тег, атрибуты]. */
type Shape = [string, { [k: string]: string }];

function svg(size: number, shapes: Shape[], attrs: { [k: string]: string } = {}): SVGSVGElement {
  const el = document.createElementNS(NS, 'svg');
  el.setAttribute('viewBox', '0 0 24 24');
  el.setAttribute('width', String(size));
  el.setAttribute('height', String(size));
  el.setAttribute('aria-hidden', 'true');
  el.setAttribute('fill', 'none');
  el.setAttribute('stroke', 'currentColor');
  el.setAttribute('stroke-width', '2');
  el.setAttribute('stroke-linecap', 'round');
  el.setAttribute('stroke-linejoin', 'round');
  for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v);
  for (const [tag, a] of shapes) {
    const s = document.createElementNS(NS, tag);
    for (const [k, v] of Object.entries(a)) s.setAttribute(k, v);
    el.appendChild(s);
  }
  return el;
}

const path = (d: string): Shape => ['path', { d }];

export type NavIcon = 'dialogs' | 'checklists' | 'appeals' | 'analytics';

const NAV_SHAPES: { [K in NavIcon]: Shape[] } = {
  dialogs: [path('M4 5h16v11H9l-5 4z')],
  checklists: [['rect', { x: '4', y: '4', width: '16', height: '16', rx: '3' }], path('M8 12l3 3 5-6')],
  appeals: [path('M12 4v16M6 20h12M5 8h14'), path('M5 8l-3 7a3 3 0 0 0 6 0zM19 8l-3 7a3 3 0 0 0 6 0z')],
  analytics: [path('M5 20V12M12 20V5M19 20v-5')],
};

export function navIcon(name: NavIcon): SVGSVGElement {
  return svg(20, NAV_SHAPES[name]);
}

export function themeIcon(name: 'light' | 'dark'): SVGSVGElement {
  return name === 'dark'
    ? svg(18, [path('M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z')])
    : svg(18, [
        ['circle', { cx: '12', cy: '12', r: '4' }],
        path('M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4'),
      ]);
}

export function checkIcon(): SVGSVGElement {
  return svg(16, [path('M5 12.5l4.5 4.5L19 7')], { 'stroke-width': '3' });
}

export function crossIcon(): SVGSVGElement {
  return svg(16, [path('M6 6l12 12M18 6L6 18')], { 'stroke-width': '3' });
}

/** Кольцо оценки: доля `pct` (0..100), цвет — через currentColor родителя. */
export function scoreRing(pct: number | null, label: string, sub: string): SVGSVGElement {
  const r = 52;
  const c = 2 * Math.PI * r;
  const frac = pct === null ? 0 : Math.max(0, Math.min(100, pct)) / 100;
  const el = svg(
    168,
    [
      ['circle', { class: 'cqa-ring-track', cx: '70', cy: '70', r: String(r), 'stroke-width': '12' }],
      [
        'circle',
        {
          class: 'cqa-ring-value',
          cx: '70',
          cy: '70',
          r: String(r),
          'stroke-width': '12',
          'stroke-dasharray': `${(c * frac).toFixed(2)} ${c.toFixed(2)}`,
          transform: 'rotate(-90 70 70)',
        },
      ],
      ['text', { class: 'cqa-ring-num', x: '70', y: '74', 'text-anchor': 'middle' }],
      ['text', { class: 'cqa-ring-sub', x: '70', y: '96', 'text-anchor': 'middle' }],
    ],
    { viewBox: '0 0 140 140', role: 'img', 'aria-label': `${label} ${sub}` },
  );
  el.setAttribute('aria-hidden', 'false');
  el.querySelector('.cqa-ring-num')!.textContent = label;
  el.querySelector('.cqa-ring-sub')!.textContent = sub;
  return el;
}
