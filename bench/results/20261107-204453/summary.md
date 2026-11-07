# Benchmark · set=gold · gold=all · n=65

## h200-gemma · per_criterion · k=1

| metric | value |
|---|---|
| dialogs | 65 |
| first_try_valid_rate | 1.000 |
| failure_rate | 0.000 |
| mean_seconds | 25.933 |
| p90_seconds | 68.374 |
| mean_prompt_tokens | 24022.862 |
| mean_completion_tokens | 655.508 |
| cost_per_evaluation_usd | 0.002 |
| citation_ok_rate | 1.000 |
| evidence_fallback_rate | 0.000 |

**Gold**

| metric | value |
|---|---|
| dialogs | 65 |
| weighted_agreement | 0.907 |
| total_mae | 5.827 |
| total_bias | -0.506 |
| total_none_mismatches | 0 |

By language:

| language | weighted_agreement |
|---|---|
| EN | 0.931 |
| KZ | 0.944 |
| RU | 0.881 |

By channel:

| channel | weighted_agreement |
|---|---|
| agent chat | 0.930 |
| voice call | 0.634 |

Per criterion:

| criterion | n | agree | majority_baseline | kappa | na tp/fp/fn/tn | gross P/R/support |
|---|---|---|---|---|---|---|
| c01 | 65 | 0.969 | 0.923 | 0.735 | — | — |
| c02 | 65 | 0.923 | 0.662 | 0.837 | 43/4/0/18 | — |
| c03 | 65 | 0.985 | 0.831 | 0.948 | 54/0/0/11 | — |
| c04 | 65 | 0.831 | 0.738 | 0.777 | 1/0/0/64 | — |
| c05 | 65 | 0.938 | 0.769 | 0.834 | — | — |
| c06 | 65 | 0.815 | 0.723 | 0.706 | — | — |
| c07 | 65 | 0.892 | 0.677 | 0.750 | 5/0/2/58 | — |
| c08 | 65 | 1.000 | 0.877 | 1.000 | — | 1.000/1.000/8 |

