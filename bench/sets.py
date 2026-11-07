"""Benchmark id sets and checklist lookup."""

from __future__ import annotations

import json
from pathlib import Path

from server.dataset import load_fixture
from server.models import Checklist, Record

ROOT = Path(__file__).resolve().parent.parent
CHECKLIST_DIR = ROOT / "data" / "checklists"
ASSIGNMENTS = ROOT / "bench" / "gold" / "assignments.json"

# (channel, language or None for any) -> count
SMOKE_STRATA: list[tuple[str, str | None, int]] = [
    ("agent chat", "RU", 5),
    ("agent chat", "KZ", 3),
    ("agent chat", "EN", 2),
    ("voice call", None, 2),
]


def load_records() -> dict[str, Record]:
    return {r.conversation_id: r for r in load_fixture(ROOT / "tests" / "fixtures" / "dev.json")}


def checklist_for(record: Record) -> Checklist:
    name = "call.default.json" if record.channel == "voice call" else "chat.default.json"
    return Checklist.model_validate_json((CHECKLIST_DIR / name).read_text(encoding="utf-8"))


def _spread(ids: list[str], n: int) -> list[str]:
    ids = sorted(ids)
    return [ids[round(i * len(ids) / n)] for i in range(n)]


def smoke_ids() -> list[str]:
    records = load_records().values()
    out: list[str] = []
    for channel, language, n in SMOKE_STRATA:
        ids = [
            r.conversation_id
            for r in records
            if r.channel == channel and (language is None or r.language == language)
        ]
        out.extend(_spread(ids, n))
    return out


def gold_ids() -> list[str]:
    data = json.loads(ASSIGNMENTS.read_text(encoding="utf-8"))
    return [a["conversation_id"] for a in data]


def all_ids() -> list[str]:
    return list(load_records())
