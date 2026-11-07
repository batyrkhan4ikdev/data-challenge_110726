# Benchmark · set=gold · n=5

## h200-gemma · per_criterion · k=1

| metric | value |
|---|---|
| dialogs | 5 |
| first_try_valid_rate | 1.000 |
| failure_rate | 0.000 |
| mean_seconds | 57.253 |
| p90_seconds | 66.211 |
| mean_prompt_tokens | 24364.400 |
| mean_completion_tokens | 650.000 |
| cost_per_evaluation_usd | 0.005 |
| citation_ok_rate | 1.000 |
| evidence_fallback_rate | 0.000 |

**Gold**

| metric | value |
|---|---|
| dialogs | 5 |
| weighted_agreement | 0.911 |
| total_mae | 4.766 |
| total_bias | -1.082 |
| total_none_mismatches | 0 |

By language:

| language | weighted_agreement |
|---|---|
| EN | 1.000 |
| KZ | 1.000 |
| RU | 0.851 |

By channel:

| channel | weighted_agreement |
|---|---|
| agent chat | 0.950 |
| voice call | 0.752 |

Per criterion:

| criterion | n | agree | majority_baseline | kappa | na tp/fp/fn/tn | gross P/R/support |
|---|---|---|---|---|---|---|
| c01 | 5 | 0.800 | 0.800 | 0.000 | 0/0/0/5 | — |
| c02 | 5 | 0.800 | 0.600 | 0.545 | 3/1/0/1 | — |
| c03 | 5 | 1.000 | 0.800 | 1.000 | 4/0/0/1 | — |
| c04 | 5 | 1.000 | 0.800 | 1.000 | 0/0/0/5 | — |
| c05 | 5 | 1.000 | 0.800 | 1.000 | — | — |
| c06 | 5 | 0.800 | 0.600 | 0.783 | — | — |
| c07 | 5 | 0.800 | 0.600 | 0.545 | 0/0/0/5 | — |
| c08 | 5 | 1.000 | 1.000 | — | — | —/—/0 |

## h200-glimmer · per_criterion · k=1

| metric | value |
|---|---|
| dialogs | 5 |
| first_try_valid_rate | 1.000 |
| failure_rate | 0.000 |
| mean_seconds | 12.400 |
| p90_seconds | 17.102 |
| mean_prompt_tokens | 20045.000 |
| mean_completion_tokens | 677.600 |
| cost_per_evaluation_usd | 0.001 |
| citation_ok_rate | 1.000 |
| evidence_fallback_rate | 0.000 |

**Gold**

| metric | value |
|---|---|
| dialogs | 5 |
| weighted_agreement | 0.683 |
| total_mae | 24.000 |
| total_bias | -24.000 |
| total_none_mismatches | 0 |

By language:

| language | weighted_agreement |
|---|---|
| EN | 1.000 |
| KZ | 0.653 |
| RU | 0.587 |

By channel:

| channel | weighted_agreement |
|---|---|
| agent chat | 0.765 |
| voice call | 0.356 |

Per criterion:

| criterion | n | agree | majority_baseline | kappa | na tp/fp/fn/tn | gross P/R/support |
|---|---|---|---|---|---|---|
| c01 | 5 | 0.800 | 0.800 | 0.000 | 0/0/0/5 | — |
| c02 | 5 | 0.800 | 0.600 | 0.545 | 3/1/0/1 | — |
| c03 | 5 | 0.400 | 0.800 | 0.118 | 2/0/2/1 | — |
| c04 | 5 | 0.800 | 0.800 | 0.308 | 0/0/0/5 | — |
| c05 | 5 | 0.600 | 0.800 | 0.286 | — | — |
| c06 | 5 | 0.800 | 0.600 | 0.783 | — | — |
| c07 | 5 | 0.600 | 0.600 | 0.000 | 0/0/0/5 | — |
| c08 | 5 | 1.000 | 1.000 | — | — | —/—/0 |

