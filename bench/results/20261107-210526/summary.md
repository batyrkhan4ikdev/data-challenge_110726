# Benchmark · set=gold · gold=all · n=65

## ensemble · single · k=1

| metric | value |
|---|---|
| dialogs | 65 |
| first_try_valid_rate | 0.000 |
| failure_rate | 0.000 |
| mean_seconds | 43.295 |
| p90_seconds | 96.834 |
| mean_prompt_tokens | 31753.308 |
| mean_completion_tokens | 1844.477 |
| cost_per_evaluation_usd | — |
| citation_ok_rate | 1.000 |
| evidence_fallback_rate | 0.000 |

**Gold**

| metric | value |
|---|---|
| dialogs | 65 |
| weighted_agreement | 0.904 |
| total_mae | 5.724 |
| total_bias | 3.671 |
| total_none_mismatches | 0 |

By language:

| language | weighted_agreement |
|---|---|
| EN | 0.931 |
| KZ | 0.924 |
| RU | 0.884 |

By channel:

| channel | weighted_agreement |
|---|---|
| agent chat | 0.926 |
| voice call | 0.644 |

Per criterion:

| criterion | n | agree | majority_baseline | kappa | na tp/fp/fn/tn | gross P/R/support |
|---|---|---|---|---|---|---|
| c01 | 65 | 0.969 | 0.923 | 0.735 | — | — |
| c02 | 65 | 0.938 | 0.662 | 0.875 | 42/2/1/20 | — |
| c03 | 65 | 1.000 | 0.831 | 1.000 | 54/0/0/11 | — |
| c04 | 65 | 0.846 | 0.738 | 0.802 | 1/0/0/64 | — |
| c05 | 65 | 0.862 | 0.769 | 0.558 | — | — |
| c06 | 65 | 0.800 | 0.723 | 0.648 | — | — |
| c07 | 65 | 0.938 | 0.677 | 0.866 | 6/0/1/58 | — |
| c08 | 65 | 1.000 | 0.877 | 1.000 | — | 1.000/1.000/8 |

