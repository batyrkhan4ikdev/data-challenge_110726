/** Человеческие названия критериев вместо id вида c02: id остаётся только в data-атрибутах и подсказках. */
export interface Named {
  id: string;
  title: string;
}

export type NameOf = (id: string) => string;

export function nameResolver(criteria: Named[]): NameOf {
  const titles = new Map(criteria.map((c) => [c.id, c.title]));
  return (id) => titles.get(id) ?? id;
}

/** Заменяет упоминания id критериев в серверном тексте («c01 «да»…») на названия. */
export function humanizeIds(text: string, nameOf: NameOf): string {
  return text.replace(/\b[a-z]\d{1,3}\b/gi, (m) => nameOf(m.toLowerCase()) === m.toLowerCase() ? m : `«${nameOf(m.toLowerCase())}»`);
}

/** Ссылки на реплики в серверном тексте: «[13]» и «[13, 14]» → «#13», «#13, #14». */
export function humanizeRefs(text: string): string {
  return text.replace(/\[(\d+(?:\s*[,;]\s*\d+)*)\]/g, (_, nums: string) => nums.split(/\s*[,;]\s*/).map((n) => `#${n}`).join(', '));
}
