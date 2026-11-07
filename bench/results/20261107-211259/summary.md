# Benchmark · set=gold · gold=all · n=65

## h200-flashnext · single · k=1

| metric | value |
|---|---|
| dialogs | 65 |
| first_try_valid_rate | 0.985 |
| failure_rate | 0.000 |
| mean_seconds | 11.980 |
| p90_seconds | 44.867 |
| mean_prompt_tokens | 3948.892 |
| mean_completion_tokens | 613.431 |
| cost_per_evaluation_usd | 0.002 |
| citation_ok_rate | 1.000 |
| evidence_fallback_rate | 0.000 |

**Gold**

| metric | value |
|---|---|
| dialogs | 65 |
| weighted_agreement | 0.884 |
| total_mae | 6.557 |
| total_bias | 3.375 |
| total_none_mismatches | 0 |

By language:

| language | weighted_agreement |
|---|---|
| EN | 0.908 |
| KZ | 0.934 |
| RU | 0.853 |

By channel:

| channel | weighted_agreement |
|---|---|
| agent chat | 0.908 |
| voice call | 0.604 |

Per criterion:

| criterion | n | agree | majority_baseline | kappa | na tp/fp/fn/tn | gross P/R/support |
|---|---|---|---|---|---|---|
| c01 | 65 | 0.954 | 0.923 | 0.552 | — | — |
| c02 | 65 | 0.877 | 0.662 | 0.754 | 40/3/3/19 | — |
| c03 | 65 | 1.000 | 0.831 | 1.000 | 54/0/0/11 | — |
| c04 | 65 | 0.846 | 0.738 | 0.868 | 1/0/0/64 | — |
| c05 | 65 | 0.877 | 0.769 | 0.597 | — | — |
| c06 | 65 | 0.723 | 0.723 | 0.522 | — | — |
| c07 | 65 | 0.938 | 0.677 | 0.870 | 6/0/1/58 | — |
| c08 | 65 | 1.000 | 0.877 | 1.000 | — | 1.000/1.000/8 |

