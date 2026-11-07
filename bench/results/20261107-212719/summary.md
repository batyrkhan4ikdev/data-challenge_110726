# Benchmark · set=gold · gold=all · n=65

## or-gemini-flash · single · k=1

| metric | value |
|---|---|
| dialogs | 65 |
| first_try_valid_rate | 1.000 |
| failure_rate | 0.200 |
| mean_seconds | 15.792 |
| p90_seconds | 52.978 |
| mean_prompt_tokens | 6171.385 |
| mean_completion_tokens | 696.500 |
| cost_per_evaluation_usd | 0.008 |
| citation_ok_rate | 1.000 |
| evidence_fallback_rate | 0.000 |

**Gold**

| metric | value |
|---|---|
| dialogs | 52 |
| weighted_agreement | 0.899 |
| total_mae | 5.195 |
| total_bias | -0.984 |
| total_none_mismatches | 0 |

By language:

| language | weighted_agreement |
|---|---|
| EN | 0.931 |
| KZ | 0.922 |
| RU | 0.864 |

By channel:

| channel | weighted_agreement |
|---|---|
| agent chat | 0.920 |
| voice call | 0.554 |

Per criterion:

| criterion | n | agree | majority_baseline | kappa | na tp/fp/fn/tn | gross P/R/support |
|---|---|---|---|---|---|---|
| c01 | 52 | 0.981 | 0.923 | 0.847 | — | — |
| c02 | 52 | 0.923 | 0.673 | 0.845 | 33/1/2/16 | — |
| c03 | 52 | 0.981 | 0.827 | 0.933 | 43/1/0/8 | — |
| c04 | 52 | 0.846 | 0.731 | 0.839 | 1/0/0/51 | — |
| c05 | 52 | 0.962 | 0.769 | 0.892 | — | — |
| c06 | 52 | 0.692 | 0.731 | 0.603 | — | — |
| c07 | 52 | 0.962 | 0.692 | 0.917 | 4/0/0/48 | — |
| c08 | 52 | 1.000 | 0.846 | 1.000 | — | 1.000/1.000/8 |

