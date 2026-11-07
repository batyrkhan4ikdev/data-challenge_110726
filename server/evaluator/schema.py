from server.models import Checklist, Criterion
from server.scoring import allowed_verdicts

ITEM_KEYS = ['explanation', 'evidence_idx', 'expected_range', 'na_reason', 'verdict']


def _item_schema(c: Criterion) -> dict:
    return {
        'type': 'object',
        'additionalProperties': False,
        'properties': {
            'explanation': {'type': 'string'},
            'evidence_idx': {'type': 'array', 'items': {'type': 'integer'}},
            'expected_range': {
                'anyOf': [
                    {'type': 'array', 'items': {'type': 'integer'}, 'minItems': 2, 'maxItems': 2},
                    {'type': 'null'},
                ]
            },
            'na_reason': {'anyOf': [{'type': 'string'}, {'type': 'null'}]},
            'verdict': {'type': 'string', 'enum': allowed_verdicts(c)},
        },
        'required': list(ITEM_KEYS),
    }


def build_schema(checklist: Checklist, criterion_ids: list[str]) -> dict:
    by_id = {c.id: c for c in checklist.criteria}
    return {
        'type': 'object',
        'additionalProperties': False,
        'properties': {cid: _item_schema(by_id[cid]) for cid in criterion_ids},
        'required': list(criterion_ids),
    }
