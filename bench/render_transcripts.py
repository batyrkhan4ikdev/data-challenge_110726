"""Render fixture conversations to gold markdown transcripts."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "tests" / "fixtures" / "dev.json"
OUT_DIR = ROOT / "bench" / "gold" / "transcripts"

NEWLINES = re.compile(r"\r\n|\n")


def load_records() -> list[dict[str, Any]]:
    payload = json.loads(SOURCE.read_text(encoding="utf-8"))
    return payload["data"]["records"]


def render(record: dict[str, Any]) -> str:
    lines = [
        f"# {record['conversation_id']} · {record['channel']} · {record['language']}"
    ]
    audio_url = record.get("audio_url")
    if audio_url is not None:
        lines.append(f"audio: {audio_url}")
    lines.append("")
    for idx, turn in enumerate(record["transcript"]):
        text = NEWLINES.sub(" ", turn["text"])
        lines.append(f"[{idx}] {turn['timestamp']} · {turn['speaker']}: {text}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--ids",
        help="comma-separated conversation ids; renders every record when omitted",
    )
    args = parser.parse_args()

    records = load_records()
    by_id = {record["conversation_id"]: record for record in records}

    if args.ids:
        wanted = [part for part in args.ids.split(",") if part]
        missing = [cid for cid in wanted if cid not in by_id]
        for cid in missing:
            print(f"unknown id: {cid}", file=sys.stderr)
        if missing:
            return 1
        selected = [by_id[cid] for cid in wanted]
    else:
        selected = records

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for record in selected:
        path = OUT_DIR / f"{record['conversation_id']}.md"
        path.write_text(render(record), encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
