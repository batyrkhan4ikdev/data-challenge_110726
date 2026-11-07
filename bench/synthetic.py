"""Synthetic counterfactual edge cases over gold DEV chats (issue #49).

Rule-based, no LLM. Every operator is a pure transform of a gold parent chat whose expected
verdict on one target criterion follows from the checklist text by construction:

  c01_drop_greeting      strip greeting + self-introduction from the first operator turn   -> c01 no
  c07_strip_farewell     strip farewell sentences from the last operator turn              -> c07 no
  c07_drop_closing_turn  drop the final operator turn that carries the farewell            -> c07 no
  c03_drop_identification  strip the identification request (+ the system "identity
                         verified" event) from a dialog that later works on the account    -> c03 no
  c08_offer_offsite_transfer  insert an operator turn asking for money to a personal card -> c08 yes (gross)
  c08_insult             insert an insulting operator turn                                 -> c08 yes (gross)

Only agent chats are used (voice transcripts are ASR text; regexes would be unreliable). A parent is
eligible only when the gold verdict is the opposite of the expected one and the pattern is detected
unambiguously (see each transform). Client turns are never edited.

CLI:
  python -m bench.synthetic generate   # writes bench/synthetic/cases.json (ids/transforms/verdicts only)
  python -m bench.synthetic report     # re-render synthetic.md from results.json
  python -m bench.synthetic run        # judge run on parents + synthetic set, writes results.json + synthetic.md
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from server.dataset import load_fixture
from server.models import Record, Turn

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "data" / "cache" / "DEV.json"
OUT_DIR = Path(__file__).resolve().parent / "synthetic"
CASES = OUT_DIR / "cases.json"
RESULTS = OUT_DIR / "results.json"
REPORT = Path(__file__).resolve().parent / "synthetic.md"

CRITERIA = ["c01", "c02", "c03", "c04", "c05", "c06", "c07", "c08"]
LANGS = ["RU", "KZ", "EN"]

# ---------------------------------------------------------------- patterns

_NAME_RU = r"[А-ЯЁ][а-яё]+"
GREET_INTRO = {
    "RU": re.compile(
        rf"^(?:Здравствуйте|Добрый день|Добрый вечер|Доброе утро)[!,.]?\s+"
        rf"(?:меня зовут|я|Меня зовут|Я)\s+{_NAME_RU}(?:\s+из поддержки|,\s*поддержка Freedom Broker)?[.!,]?\s*"
    ),
    "KZ": re.compile(
        r"^Сәлеметсіз бе[!,.]?\s+(?:менің атым|мен|Менің атым|Мен)\s+[А-ЯӘІҢҒҮҰҚӨҺ][^\s.!,]*[.!,]?\s*"
    ),
    "EN": re.compile(
        r"^(?:Hi|Hello|Good (?:morning|afternoon|evening))[!,.]?\s+(?:I'm|I am|My name is)\s+[A-Z][a-z]+"
        r"(?:\s+from support)?[.!,]?\s*"
    ),
}
GREET_WORD = {
    "RU": re.compile(r"здравствуйте|добрый (?:день|вечер)|доброе утро|привет", re.I),
    "KZ": re.compile(r"сәлеметсіз бе|сәлем", re.I),
    "EN": re.compile(r"\b(?:hi|hello|good (?:morning|afternoon|evening))\b", re.I),
}
FAREWELL = {
    "RU": re.compile(
        r"до свидания|хорошего (?:дня|вечера|дальнейшего)|всего (?:доброго|хорошего)|спасибо за обращение|"
        r"до встречи|прощайте",
        re.I,
    ),
    "KZ": re.compile(r"сау болыңыз|күніңіз сәтті|кеш жарық|сау болыңыздар|қош болыңыз", re.I),
    "EN": re.compile(
        r"\bgood-?bye\b|\bbye\b|have a (?:good|great|nice) (?:day|evening)|take care|"
        r"thanks? for (?:contacting|reaching out)",
        re.I,
    ),
}
IDENT_REQUEST = {
    "RU": re.compile(r"подтвердить личность|начн[её]м с идентификации|пройти идентификацию|верифицир", re.I),
    "KZ": re.compile(r"жеке басыңызды растау|жеке басыңызды", re.I),
    "EN": re.compile(r"verify your identity|identity verification|confirm your identity", re.I),
}
IDENT_SYSTEM = re.compile(
    r"личность клиента подтверждена|клиенттің жеке басы расталды|customer identity verified", re.I
)
_SENT = re.compile(r"(?<=[.!?])\s+")

OFFSITE = {
    "RU": "Кстати, можете перевести деньги лично мне на карту, я вложу их с выгодой, оформлять через компанию не нужно.",
    "KZ": "Айтпақшы, ақшаны тікелей менің жеке картама аударыңыз, мен оны тиімді салып беремін, компания арқылы рәсімдеудің қажеті жоқ.",
    "EN": "By the way, you can transfer the money to my personal card and I'll invest it for you with better returns, no need to go through the company.",
}
INSULT = {
    "RU": "Вы что, совсем не способны понять простые вещи? Объясняю уже в который раз, не будьте глупым.",
    "KZ": "Сіз қарапайым нәрсені де түсіне алмайсыз ба? Қанша рет түсіндіремін, ақымақ болмаңыз.",
    "EN": "Are you really too stupid to understand something this simple? I've explained it three times already.",
}

# ---------------------------------------------------------------- helpers


def _reindex(turns: list[Turn]) -> list[Turn]:
    return [t.model_copy(update={"idx": i}) for i, t in enumerate(turns)]


def _ops(turns: list[Turn]) -> list[Turn]:
    return [t for t in turns if t.speaker == "operator"]


def _with_text(t: Turn, text: str) -> Turn:
    return t.model_copy(update={"text": text})


def _strip_sentences(text: str, pattern: re.Pattern[str]) -> str:
    return " ".join(s for s in _SENT.split(text.strip()) if not pattern.search(s)).strip()


def _any_op(turns: list[Turn], pattern: re.Pattern[str]) -> bool:
    return any(pattern.search(t.text) for t in _ops(turns))


@dataclass(frozen=True)
class Transform:
    name: str
    target: str  # criterion whose verdict is asserted
    expected: str
    parent_gold: str  # required gold verdict of the parent on `target`
    apply: Callable[[list[Turn], str], list[Turn] | None]  # None = not applicable (ambiguous / pattern absent)


def _c01_drop_greeting(turns: list[Turn], lang: str) -> list[Turn] | None:
    ops = _ops(turns)
    if not ops:
        return None
    first = ops[0]
    m = GREET_INTRO[lang].match(first.text)
    if not m:
        return None
    rest = first.text[m.end():].strip()
    if not rest or GREET_WORD[lang].search(rest):
        return None
    out = [_with_text(t, rest) if t is first else t for t in turns]
    if _any_op(out, GREET_WORD[lang]):  # a later operator greeting would keep c01 arguable
        return None
    return _reindex(out)


def _last_op(turns: list[Turn]) -> Turn | None:
    ops = _ops(turns)
    return ops[-1] if ops else None


def _c07_strip_farewell(turns: list[Turn], lang: str) -> list[Turn] | None:
    last = _last_op(turns)
    if last is None or not FAREWELL[lang].search(last.text) or len(_ops(turns)) < 2:
        return None
    rest = _strip_sentences(last.text, FAREWELL[lang])
    out = [t for t in turns if t is not last] if not rest else [_with_text(t, rest) if t is last else t for t in turns]
    if _any_op(out, FAREWELL[lang]):
        return None
    return _reindex(out)


def _c07_drop_closing_turn(turns: list[Turn], lang: str) -> list[Turn] | None:
    last = _last_op(turns)
    if last is None or turns[-1] is not last or not FAREWELL[lang].search(last.text) or len(_ops(turns)) < 2:
        return None
    out = [t for t in turns if t is not last]
    if _any_op(out, FAREWELL[lang]):
        return None
    return _reindex(out)


def _c03_drop_identification(turns: list[Turn], lang: str) -> list[Turn] | None:
    hits = [t for t in _ops(turns) if IDENT_REQUEST[lang].search(t.text)]
    verified = [t for t in turns if t.speaker == "system" and IDENT_SYSTEM.search(t.text)]
    if len(hits) != 1 or len(verified) != 1:
        return None
    hit = hits[0]
    rest = _strip_sentences(hit.text, IDENT_REQUEST[lang])
    if rest == hit.text.strip():
        return None
    out = [t for t in turns if t is not verified[0] and not (t is hit and not rest)]
    out = [_with_text(t, rest) if t is hit else t for t in out]
    if _any_op(out, IDENT_REQUEST[lang]):
        return None
    return _reindex(out)


def _insert_after_first_op(text_by_lang: dict[str, str]) -> Callable[[list[Turn], str], list[Turn] | None]:
    def apply(turns: list[Turn], lang: str) -> list[Turn] | None:
        pos = next((i for i, t in enumerate(turns) if t.speaker == "operator"), None)
        if pos is None or len(_ops(turns)) < 2:
            return None
        base = turns[pos]
        new = base.model_copy(update={"text": text_by_lang[lang], "offset_s": None})
        return _reindex(turns[: pos + 1] + [new] + turns[pos + 1:])

    return apply


TRANSFORMS: list[Transform] = [
    Transform("c01_drop_greeting", "c01", "no", "yes", _c01_drop_greeting),
    Transform("c07_strip_farewell", "c07", "no", "yes", _c07_strip_farewell),
    Transform("c07_drop_closing_turn", "c07", "no", "yes", _c07_drop_closing_turn),
    Transform("c03_drop_identification", "c03", "no", "yes", _c03_drop_identification),
    Transform("c08_offer_offsite_transfer", "c08", "yes", "no", _insert_after_first_op(OFFSITE)),
    Transform("c08_insult", "c08", "yes", "no", _insert_after_first_op(INSULT)),
]
BY_NAME = {t.name: t for t in TRANSFORMS}

# ---------------------------------------------------------------- generation


def load_parents() -> dict[str, Record]:
    return {r.conversation_id: r for r in load_fixture(CACHE)}


def case_id(parent: str, transform: str) -> str:
    return f"syn-{parent}-{transform}"


def build_case(parent: Record, transform: Transform) -> Record | None:
    if parent.channel != "agent chat":
        return None
    turns = transform.apply(list(parent.transcript), parent.language)
    if turns is None:
        return None
    return parent.model_copy(update={"conversation_id": case_id(parent.conversation_id, transform.name), "transcript": turns})


def generate(parents: dict[str, Record] | None = None, gold: dict[str, dict[str, str]] | None = None):
    """Return (case descriptors, {case_id: Record}); sorted and deterministic."""
    if parents is None:
        parents = load_parents()
    if gold is None:
        from bench.prefill import load_gold

        gold = load_gold()
    cases: list[dict] = []
    records: dict[str, Record] = {}
    for pid in sorted(parents):
        parent = parents[pid]
        g = gold.get(pid, {})
        for tf in TRANSFORMS:
            if g.get(tf.target) != tf.parent_gold:
                continue
            rec = build_case(parent, tf)
            if rec is None:
                continue
            records[rec.conversation_id] = rec
            cases.append(
                {
                    "case_id": rec.conversation_id,
                    "parent_id": pid,
                    "language": parent.language,
                    "transform": tf.name,
                    "target": tf.target,
                    "expected": tf.expected,
                    "parent_gold": {c: g[c] for c in CRITERIA if c in g},
                    "untouched": [c for c in CRITERIA if c != tf.target],
                    "turns_parent": len(parent.transcript),
                    "turns_case": len(rec.transcript),
                }
            )
    return cases, records


# ---------------------------------------------------------------- run + report


def _flip(a, b) -> bool:
    return a != b


def summarise(cases: list[dict], parent_rows: dict[str, dict], case_rows: dict[str, dict]) -> dict:
    """{transform: {lang: stats}}; lang 'ALL' included."""
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for c in cases:
        groups[(c["transform"], c["language"])].append(c)
        groups[(c["transform"], "ALL")].append(c)
    out: dict = {}
    for (tf, lang), cs in sorted(groups.items()):
        n = n_ok = hits = parent_already = gained = 0
        coll_checks = coll_flips = coll_cases = 0
        for c in cs:
            row, prow = case_rows.get(c["case_id"]), parent_rows.get(c["parent_id"])
            if not row or not row.get("ok") or not prow or not prow.get("ok"):
                continue
            n_ok += 1
            tgt = c["target"]
            hit = row["verdicts"].get(tgt) == c["expected"]
            hits += hit
            pre = prow["verdicts"].get(tgt) == c["expected"]
            parent_already += pre
            gained += hit and not pre
            flips = [k for k in c["untouched"] if _flip(row["verdicts"].get(k), prow["verdicts"].get(k))]
            coll_checks += len(c["untouched"])
            coll_flips += len(flips)
            coll_cases += bool(flips)
        n = len(cs)
        out.setdefault(tf, {})[lang] = {
            "n": n,
            "n_ok": n_ok,
            "hits": hits,
            "hit_rate": hits / n_ok if n_ok else None,
            "parent_already_expected": parent_already,
            "flipped_from_parent": gained,
            "collateral_flips": coll_flips,
            "collateral_checks": coll_checks,
            "cases_with_collateral": coll_cases,
        }
    return out


def _pct(x) -> str:
    return "—" if x is None else f"{x * 100:.0f}%"


def render_report(summary: dict, meta: dict, collateral_by_crit: dict, misses: list[dict]) -> str:
    L: list[str] = []
    a = L.append
    a("# Синтетические edge-кейсы с gold-родителем (issue #49)")
    a("")
    a(f"Судья: `{meta['profile']}`, режим `{meta['mode']}`, k={meta['k']}, температура 0. "
      f"Родителей: {meta['parents']}, синтетических кейсов: {meta['cases']}; запуск {meta['date']}.")
    a("")
    a("Генератор: `bench/synthetic.py` (без LLM, детерминированный; перегенерация `python -m bench.synthetic generate`). "
      "Список кейсов (id, родитель, трансформация, ожидаемый вердикт, gold родителя) — `bench/synthetic/cases.json`; "
      "вердикты судьи — `bench/synthetic/results.json`. Текст диалогов не коммитится.")
    a("")
    a("## Трансформации")
    a("")
    a("| Трансформация | Что делает | Цель | Ожидание | Условие родителя |")
    a("|---|---|---|---|---|")
    desc = {
        "c01_drop_greeting": "вырезает приветствие и самопредставление из первой реплики оператора",
        "c07_strip_farewell": "вырезает предложения-прощания из последней реплики оператора",
        "c07_drop_closing_turn": "удаляет финальную реплику оператора с прощанием",
        "c03_drop_identification": "вырезает запрос идентификации и системное событие «личность подтверждена»",
        "c08_offer_offsite_transfer": "вставляет реплику оператора с просьбой перевести деньги на личную карту",
        "c08_insult": "вставляет оскорбительную реплику оператора",
    }
    for tf in TRANSFORMS:
        a(f"| `{tf.name}` | {desc[tf.name]} | {tf.target} | {tf.expected}{' (грубая ошибка)' if tf.target == 'c08' else ''} | gold {tf.target}={tf.parent_gold} |")
    a("")
    a("Клиентские реплики не редактируются; остальные критерии «должны остаться как у родителя» — "
      "сравнение идёт с вердиктами судьи на неизменённом родителе (изолирует эффект правки, а не ошибки судьи на родителе).")
    a("")
    a("## Результаты: трансформация × язык")
    a("")
    a("`hit` — судья на кейсе выдал ожидаемый вердикт по целевому критерию. `уже было` — родитель и так давал это "
      "ожидаемое значение (правка ничего не доказывает на этих кейсах). `сдвиг` — родитель ≠ ожидаемому, кейс = ожидаемому. "
      "`колл.` — число флипов нецелевых критериев относительно родителя / число проверок (кейсов с хотя бы одним флипом).")
    a("")
    a("| Трансформация | Язык | n | hit | hit % | уже было | сдвиг | колл. флипы | кейсов с флипом |")
    a("|---|---|---:|---:|---:|---:|---:|---:|---:|")
    for tf in TRANSFORMS:
        per = summary.get(tf.name, {})
        for lang in [*LANGS, "ALL"]:
            s = per.get(lang)
            if not s:
                continue
            lab = "все" if lang == "ALL" else lang
            a(f"| `{tf.name}` | {lab} | {s['n']} ({s['n_ok']} ok) | {s['hits']} | {_pct(s['hit_rate'])} | "
              f"{s['parent_already_expected']} | {s['flipped_from_parent']} | "
              f"{s['collateral_flips']}/{s['collateral_checks']} | {s['cases_with_collateral']} |")
    a("")
    a("## Коллатеральные флипы по критериям")
    a("")
    a("| Трансформация | " + " | ".join(CRITERIA) + " |")
    a("|---|" + "---:|" * len(CRITERIA))
    for tf in TRANSFORMS:
        d = collateral_by_crit.get(tf.name, {})
        a(f"| `{tf.name}` | " + " | ".join(str(d.get(c, 0)) if c != tf.target else "·" for c in CRITERIA) + " |")
    a("")
    a("## Проверка KZ против RU/EN")
    a("")
    kz_lines = []
    for tf in TRANSFORMS:
        per = summary.get(tf.name, {})
        parts = []
        for lang in LANGS:
            s = per.get(lang)
            parts.append(f"{lang} {_pct(s['hit_rate'])} (n={s['n_ok']})" if s else f"{lang} n/a")
        kz_lines.append(f"- `{tf.name}`: " + "; ".join(parts))
    L.extend(kz_lines)
    a("")
    if misses:
        a("## Промахи (id, без текста)")
        a("")
        a("| case | цель | ожидание | судья | родитель (судья) |")
        a("|---|---|---|---|---|")
        for m in misses:
            a(f"| `{m['case_id']}` | {m['target']} | {m['expected']} | {m['got']} | {m['parent']} |")
        a("")
    a("## Ограничения")
    a("")
    a("- Правки, сделанные правилами, заметнее и однозначнее реальных ошибок: судья видит «дырку» там, где живой оператор "
      "ошибался бы мягче. Высокий hit rate — нижняя планка чувствительности, а не оценка точности на реальных диалогах.")
    a("- Родители — только agent chat из DEV с gold-вердиктом, противоположным ожиданию; поэтому n малы, особенно "
      "для c03 и c07 (в gold мало «да»). Доверительные интервалы широкие; различия в 1–2 кейса — шум.")
    a("- Регэкспы под приветствие/прощание/идентификацию подобраны под шаблонные синтетические чаты DEV (p1-*); "
      "голосовые звонки (ASR-текст) не используются.")
    a("- Вставленные реплики (c08) шаблонные и дословно одинаковы для всех родителей одного языка; "
      "KZ-реплики составлены вручную и могут звучать менее естественно, чем RU/EN.")
    a("- `c03_drop_identification` удаляет также системное событие «личность подтверждена» (иначе ожидание «нет» не следует "
      "из текста); клиентские реплики остаются, поэтому диалог слегка неестественный.")
    a("- Ошибки судьи не считаются попаданием: часть кейсов `c07_drop_closing_turn` не получила вердикта — модель сослалась "
      "на несуществующую реплику (`expected_range` за пределами диалога) и после повтора запрос отклонён валидатором "
      "(в таблице n — все кейсы, «ok» — получившие вердикт; hit % считается по ok). Сам отказ — осмысленный сигнал "
      "(судья ищет закрывающую реплику, которой нет), но верифицировать «нет» он не смог.")
    a("- Промахи `c03_drop_identification` — вердикт `na`, а не `yes`: без запроса идентификации судья видит диалог без "
      "защищённого действия и ставит «неприменимо». Ожидание «нет» следует из чек-листа буквально (данные раскрыты без "
      "проверки), но `na` — допустимое прочтение; n=4, выводов о KZ/EN не делаем.")
    a("- Коллатеральные флипы `c08_insult` — в основном c05/c06 (эмпатия/ведение диалога), т.е. ожидаемая реакция на "
      "грубую реплику, а не нестабильность судьи; для `c08_offer_offsite_transfer` и `c01_drop_greeting` флипы редки и "
      "сопоставимы по языкам.")
    a("- Официальные итоги не затрагиваются: ни `server/scoring.py`, ни промпты, ни `results/` не менялись.")
    a("")
    return "\n".join(L)


def write_report(cases: list[dict], rows: list[dict], profile_name: str, run_date: str) -> None:
    by_id = {r["conversation_id"]: r for r in rows}
    summary = summarise(cases, by_id, by_id)
    collateral: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    misses = []
    for c in cases:
        row, prow = by_id[c["case_id"]], by_id[c["parent_id"]]
        if not row["ok"] or not prow["ok"]:
            continue
        for k in c["untouched"]:
            if row["verdicts"].get(k) != prow["verdicts"].get(k):
                collateral[c["transform"]][k] += 1
        got = row["verdicts"].get(c["target"])
        if got != c["expected"]:
            misses.append({"case_id": c["case_id"], "target": c["target"], "expected": c["expected"],
                           "got": got, "parent": prow["verdicts"].get(c["target"])})
    meta = {"profile": profile_name, "mode": "per_criterion", "k": 1,
            "parents": len({c["parent_id"] for c in cases}), "cases": len(cases), "date": run_date}
    REPORT.write_text(render_report(summary, meta, collateral, misses), encoding="utf-8")


def rerender() -> int:
    """Re-render synthetic.md from cases.json + results.json (no judge calls)."""
    cases = json.loads(CASES.read_text(encoding="utf-8"))
    d = json.loads(RESULTS.read_text(encoding="utf-8"))
    write_report(cases, d["rows"], d["profile"], d["date"])
    return 0


async def run(concurrency: int, profile_name: str) -> int:
    from dotenv import load_dotenv

    load_dotenv()
    from datetime import date

    from bench.prefill import load_gold
    from bench.run import run_profile
    from server.config import load_profiles

    parents = load_parents()
    gold = load_gold()
    cases, records = generate(parents, gold)
    profile = load_profiles()[profile_name]
    parent_ids = sorted({c["parent_id"] for c in cases})
    all_records = {**{p: parents[p] for p in parent_ids}, **records}
    ids = parent_ids + sorted(records)
    print(f"running {len(parent_ids)} parents + {len(records)} cases on {profile_name}", file=sys.stderr)
    rows = await run_profile(profile, ids, all_records, "per_criterion", 1, concurrency)
    by_id = {r["conversation_id"]: r for r in rows}
    slim = [{k: r[k] for k in ("conversation_id", "ok", "error", "verdicts", "total", "gross_error")} for r in rows]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS.write_text(json.dumps({"profile": profile_name, "mode": "per_criterion", "k": 1, "date": date.today().isoformat(),
                                   "rows": slim}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    write_report(cases, slim, profile_name, date.today().isoformat())
    failed = [r["conversation_id"] for r in rows if not r["ok"]]
    print(f"done; failed rows: {failed}", file=sys.stderr)
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("generate")
    sub.add_parser("report")
    r = sub.add_parser("run")
    r.add_argument("--concurrency", type=int, default=8)
    r.add_argument("--profile", default="h200-gemma")
    args = ap.parse_args(argv)
    if args.cmd == "generate":
        cases, _ = generate()
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        CASES.write_text(json.dumps(cases, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        counts: dict[str, int] = defaultdict(int)
        for c in cases:
            counts[f"{c['transform']}/{c['language']}"] += 1
        print(json.dumps(counts, ensure_ascii=False, indent=1))
        return 0
    if args.cmd == "report":
        return rerender()
    return asyncio.run(run(args.concurrency, args.profile))


if __name__ == "__main__":
    raise SystemExit(main())
