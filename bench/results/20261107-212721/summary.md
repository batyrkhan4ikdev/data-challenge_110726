# Benchmark · set=gold · gold=all · n=65

## or-grok · single · k=1

| metric | value |
|---|---|
| dialogs | 65 |
| first_try_valid_rate | 1.000 |
| failure_rate | 0.385 |
| mean_seconds | 31.648 |
| p90_seconds | 67.942 |
| mean_prompt_tokens | 6238.025 |
| mean_completion_tokens | 2197.975 |
| cost_per_evaluation_usd | 0.026 |
| citation_ok_rate | 1.000 |
| evidence_fallback_rate | 0.000 |

**Gold**

| metric | value |
|---|---|
| dialogs | 40 |
| weighted_agreement | 0.856 |
| total_mae | 5.818 |
| total_bias | 0.544 |
| total_none_mismatches | 0 |

By language:

| language | weighted_agreement |
|---|---|
| EN | 0.913 |
| KZ | 0.844 |
| RU | 0.851 |

By channel:

| channel | weighted_agreement |
|---|---|
| agent chat | 0.884 |
| voice call | 0.604 |

Per criterion:

| criterion | n | agree | majority_baseline | kappa | na tp/fp/fn/tn | gross P/R/support |
|---|---|---|---|---|---|---|
| c01 | 40 | 1.000 | 0.925 | 1.000 | — | — |
| c02 | 40 | 0.800 | 0.550 | 0.651 | 20/4/2/14 | — |
| c03 | 40 | 0.975 | 0.825 | 0.912 | 33/1/0/6 | — |
| c04 | 40 | 0.700 | 0.700 | 0.890 | 1/0/0/39 | — |
| c05 | 40 | 0.900 | 0.725 | 0.717 | — | — |
| c06 | 40 | 0.775 | 0.700 | 0.769 | — | — |
| c07 | 40 | 0.975 | 0.675 | 0.948 | 5/0/0/35 | — |
| c08 | 40 | 1.000 | 0.875 | 1.000 | — | 1.000/1.000/5 |

