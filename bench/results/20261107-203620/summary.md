# Benchmark · set=gold · gold=all · n=65

## h200-gemma · per_criterion · k=1

| metric | value |
|---|---|
| dialogs | 65 |
| first_try_valid_rate | 1.000 |
| failure_rate | 0.000 |
| mean_seconds | 26.784 |
| p90_seconds | 65.701 |
| mean_prompt_tokens | 22854.862 |
| mean_completion_tokens | 649.846 |
| cost_per_evaluation_usd | 0.002 |
| citation_ok_rate | 1.000 |
| evidence_fallback_rate | 0.000 |

**Gold**

| metric | value |
|---|---|
| dialogs | 65 |
| weighted_agreement | 0.887 |
| total_mae | 5.953 |
| total_bias | -1.312 |
| total_none_mismatches | 0 |

By language:

| language | weighted_agreement |
|---|---|
| EN | 0.931 |
| KZ | 0.921 |
| RU | 0.853 |

By channel:

| channel | weighted_agreement |
|---|---|
| agent chat | 0.910 |
| voice call | 0.604 |

Per criterion:

| criterion | n | agree | majority_baseline | kappa | na tp/fp/fn/tn | gross P/R/support |
|---|---|---|---|---|---|---|
| c01 | 65 | 0.969 | 0.923 | 0.735 | — | — |
| c02 | 65 | 0.923 | 0.662 | 0.837 | 43/4/0/18 | — |
| c03 | 65 | 0.938 | 0.831 | 0.813 | 51/0/3/11 | — |
| c04 | 65 | 0.831 | 0.738 | 0.831 | 1/0/0/64 | — |
| c05 | 65 | 0.938 | 0.769 | 0.834 | — | — |
| c06 | 65 | 0.754 | 0.723 | 0.648 | — | — |
| c07 | 65 | 0.846 | 0.677 | 0.626 | 6/0/1/58 | — |
| c08 | 65 | 1.000 | 0.877 | 1.000 | — | 1.000/1.000/8 |

