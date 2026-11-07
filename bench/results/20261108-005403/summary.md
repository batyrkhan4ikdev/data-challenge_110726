# Benchmark · set=gold · gold=all · n=65

## h200-kz · per_criterion · k=1

| metric | value |
|---|---|
| dialogs | 65 |
| first_try_valid_rate | 0.985 |
| failure_rate | 0.000 |
| mean_seconds | 39.906 |
| p90_seconds | 88.173 |
| mean_prompt_tokens | 26503.062 |
| mean_completion_tokens | 862.769 |
| cost_per_evaluation_usd | 0.001 |
| citation_ok_rate | 1.000 |
| evidence_fallback_rate | 0.000 |

**Gold**

| metric | value |
|---|---|
| dialogs | 65 |
| weighted_agreement | 0.740 |
| total_mae | 14.580 |
| total_bias | -7.777 |
| total_none_mismatches | 0 |

By language:

| language | weighted_agreement |
|---|---|
| EN | 0.766 |
| KZ | 0.710 |
| RU | 0.742 |

By channel:

| channel | weighted_agreement |
|---|---|
| agent chat | 0.767 |
| voice call | 0.416 |

Per criterion:

| criterion | n | agree | majority_baseline | kappa | na tp/fp/fn/tn | gross P/R/support |
|---|---|---|---|---|---|---|
| c01 | 65 | 0.908 | 0.923 | 0.204 | — | — |
| c02 | 65 | 0.646 | 0.662 | 0.394 | 30/4/13/18 | — |
| c03 | 65 | 0.769 | 0.831 | 0.501 | 40/0/14/11 | — |
| c04 | 65 | 0.692 | 0.738 | 0.519 | 1/0/0/64 | — |
| c05 | 65 | 0.877 | 0.785 | 0.670 | — | — |
| c06 | 65 | 0.677 | 0.723 | 0.410 | — | — |
| c07 | 65 | 0.492 | 0.738 | 0.198 | 4/0/3/58 | — |
| c08 | 65 | 0.985 | 0.877 | 0.932 | — | 0.889/1.000/8 |

