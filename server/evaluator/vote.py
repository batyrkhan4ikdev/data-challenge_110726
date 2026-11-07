from server.models import Checklist, Item


def aggregate(
    samples: list[dict[str, Item]], checklist: Checklist, criterion_ids: list[str]
) -> dict[str, Item]:
    by_id = {c.id: c for c in checklist.criteria}
    result: dict[str, Item] = {}
    for cid in criterion_ids:
        items = [s[cid] for s in samples if cid in s]
        if not items:
            continue
        votes: dict[str, int] = {}
        for it in items:
            votes[it.verdict] = votes.get(it.verdict, 0) + 1
        if by_id[cid].answer_type == 'scale' and 'na' not in votes:
            steps = sorted(int(it.verdict) for it in items)
            chosen = str(steps[(len(steps) - 1) // 2])
        else:
            chosen = max(votes, key=votes.__getitem__)
        source = next(it for it in items if it.verdict == chosen)
        result[cid] = source.model_copy(update={'votes': votes})
    return result
