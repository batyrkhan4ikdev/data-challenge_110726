# Benchmark · set=gold · gold=all · n=65

## h200-q27 · single · k=1

| metric | value |
|---|---|
| dialogs | 65 |
| first_try_valid_rate | 0.985 |
| failure_rate | 0.000 |
| mean_seconds | 32.603 |
| p90_seconds | 74.838 |
| mean_prompt_tokens | 3893.308 |
| mean_completion_tokens | 561.569 |
| cost_per_evaluation_usd | 0.002 |
| citation_ok_rate | 0.993 |
| evidence_fallback_rate | 0.000 |

**Gold**

| metric | value |
|---|---|
| dialogs | 65 |
| weighted_agreement | 0.877 |
| total_mae | 7.519 |
| total_bias | 4.366 |
| total_none_mismatches | 0 |

By language:

| language | weighted_agreement |
|---|---|
| EN | 0.924 |
| KZ | 0.878 |
| RU | 0.857 |

By channel:

| channel | weighted_agreement |
|---|---|
| agent chat | 0.901 |
| voice call | 0.594 |

Per criterion:

| criterion | n | agree | majority_baseline | kappa | na tp/fp/fn/tn | gross P/R/support |
|---|---|---|---|---|---|---|
| c01 | 65 | 0.954 | 0.923 | 0.642 | — | — |
| c02 | 65 | 0.862 | 0.662 | 0.712 | 41/4/2/18 | — |
| c03 | 65 | 1.000 | 0.831 | 1.000 | 54/0/0/11 | — |
| c04 | 65 | 0.862 | 0.738 | 0.887 | 1/0/0/64 | — |
| c05 | 65 | 0.831 | 0.769 | 0.460 | — | — |
| c06 | 65 | 0.754 | 0.723 | 0.535 | — | — |
| c07 | 65 | 0.831 | 0.677 | 0.648 | 4/1/3/57 | — |
| c08 | 65 | 1.000 | 0.877 | 1.000 | — | 1.000/1.000/8 |

