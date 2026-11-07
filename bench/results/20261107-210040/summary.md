# Benchmark · set=gold · gold=all · n=65

## ensemble · single · k=1

| metric | value |
|---|---|
| dialogs | 65 |
| first_try_valid_rate | 0.000 |
| failure_rate | 0.000 |
| mean_seconds | 33.210 |
| p90_seconds | 83.613 |
| mean_prompt_tokens | 31697.138 |
| mean_completion_tokens | 2194.246 |
| cost_per_evaluation_usd | — |
| citation_ok_rate | 1.000 |
| evidence_fallback_rate | 0.000 |

**Gold**

| metric | value |
|---|---|
| dialogs | 65 |
| weighted_agreement | 0.897 |
| total_mae | 5.931 |
| total_bias | 4.207 |
| total_none_mismatches | 0 |

By language:

| language | weighted_agreement |
|---|---|
| EN | 0.927 |
| KZ | 0.937 |
| RU | 0.867 |

By channel:

| channel | weighted_agreement |
|---|---|
| agent chat | 0.924 |
| voice call | 0.574 |

Per criterion:

| criterion | n | agree | majority_baseline | kappa | na tp/fp/fn/tn | gross P/R/support |
|---|---|---|---|---|---|---|
| c01 | 65 | 0.969 | 0.923 | 0.735 | — | — |
| c02 | 65 | 0.938 | 0.662 | 0.875 | 42/2/1/20 | — |
| c03 | 65 | 1.000 | 0.831 | 1.000 | 54/0/0/11 | — |
| c04 | 65 | 0.846 | 0.738 | 0.879 | 1/0/0/64 | — |
| c05 | 65 | 0.892 | 0.769 | 0.657 | — | — |
| c06 | 65 | 0.738 | 0.723 | 0.480 | — | — |
| c07 | 65 | 0.892 | 0.677 | 0.770 | 6/0/1/58 | — |
| c08 | 65 | 1.000 | 0.877 | 1.000 | — | 1.000/1.000/8 |

