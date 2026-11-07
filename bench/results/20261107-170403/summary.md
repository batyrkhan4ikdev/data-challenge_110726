# Benchmark · set=gold · n=5

## h200-gemma · single · k=1

| metric | value |
|---|---|
| dialogs | 5 |
| first_try_valid_rate | 1.000 |
| failure_rate | 0.000 |
| mean_seconds | 4.750 |
| p90_seconds | 5.297 |
| mean_prompt_tokens | 3973.400 |
| mean_completion_tokens | 521.600 |
| cost_per_evaluation_usd | 0.000 |
| citation_ok_rate | 1.000 |
| evidence_fallback_rate | 0.000 |

**Gold**

| metric | value |
|---|---|
| dialogs | 5 |
| weighted_agreement | 0.851 |
| total_mae | 7.360 |
| total_bias | 7.360 |
| total_none_mismatches | 0 |

By language:

| language | weighted_agreement |
|---|---|
| EN | 1.000 |
| KZ | 1.000 |
| RU | 0.752 |

By channel:

| channel | weighted_agreement |
|---|---|
| agent chat | 0.913 |
| voice call | 0.604 |

Per criterion:

| criterion | n | agree | majority_baseline | kappa | na tp/fp/fn/tn | gross P/R/support |
|---|---|---|---|---|---|---|
| c01 | 5 | 0.800 | 0.800 | 0.000 | 0/0/0/5 | — |
| c02 | 5 | 0.800 | 0.600 | 0.545 | 3/1/0/1 | — |
| c03 | 5 | 1.000 | 0.800 | 1.000 | 4/0/0/1 | — |
| c04 | 5 | 1.000 | 0.800 | 1.000 | 0/0/0/5 | — |
| c05 | 5 | 0.800 | 0.800 | 0.000 | — | — |
| c06 | 5 | 0.600 | 0.600 | 0.000 | — | — |
| c07 | 5 | 0.800 | 0.600 | 0.545 | 0/0/0/5 | — |
| c08 | 5 | 1.000 | 1.000 | — | — | —/—/0 |

## h200-gptoss · single · k=1

| metric | value |
|---|---|
| dialogs | 5 |
| first_try_valid_rate | 0.800 |
| failure_rate | 0.000 |
| mean_seconds | 10.531 |
| p90_seconds | 11.828 |
| mean_prompt_tokens | 4852.200 |
| mean_completion_tokens | 974.000 |
| cost_per_evaluation_usd | 0.000 |
| citation_ok_rate | 1.000 |
| evidence_fallback_rate | 0.000 |

**Gold**

| metric | value |
|---|---|
| dialogs | 5 |
| weighted_agreement | 0.780 |
| total_mae | 14.516 |
| total_bias | -14.516 |
| total_none_mismatches | 0 |

By language:

| language | weighted_agreement |
|---|---|
| EN | 1.000 |
| KZ | 1.000 |
| RU | 0.634 |

By channel:

| channel | weighted_agreement |
|---|---|
| agent chat | 0.938 |
| voice call | 0.149 |

Per criterion:

| criterion | n | agree | majority_baseline | kappa | na tp/fp/fn/tn | gross P/R/support |
|---|---|---|---|---|---|---|
| c01 | 5 | 0.800 | 0.800 | 0.000 | 0/0/0/5 | — |
| c02 | 5 | 1.000 | 0.600 | 1.000 | 3/0/0/2 | — |
| c03 | 5 | 0.800 | 0.800 | 0.444 | 4/0/0/1 | — |
| c04 | 5 | 0.600 | 0.800 | 0.444 | 0/0/0/5 | — |
| c05 | 5 | 0.800 | 0.800 | 0.545 | — | — |
| c06 | 5 | 0.800 | 0.600 | 0.783 | — | — |
| c07 | 5 | 0.600 | 0.600 | 0.000 | 0/0/0/5 | — |
| c08 | 5 | 0.800 | 1.000 | 0.000 | — | 0.000/—/0 |

## h200-kz · single · k=1

| metric | value |
|---|---|
| dialogs | 5 |
| first_try_valid_rate | 1.000 |
| failure_rate | 0.000 |
| mean_seconds | 43.299 |
| p90_seconds | 48.173 |
| mean_prompt_tokens | 4142.200 |
| mean_completion_tokens | 615.800 |
| cost_per_evaluation_usd | 0.001 |
| citation_ok_rate | 1.000 |
| evidence_fallback_rate | 0.000 |

**Gold**

| metric | value |
|---|---|
| dialogs | 5 |
| weighted_agreement | 0.772 |
| total_mae | 9.752 |
| total_bias | 9.552 |
| total_none_mismatches | 0 |

By language:

| language | weighted_agreement |
|---|---|
| EN | 0.950 |
| KZ | 0.851 |
| RU | 0.686 |

By channel:

| channel | weighted_agreement |
|---|---|
| agent chat | 0.765 |
| voice call | 0.802 |

Per criterion:

| criterion | n | agree | majority_baseline | kappa | na tp/fp/fn/tn | gross P/R/support |
|---|---|---|---|---|---|---|
| c01 | 5 | 1.000 | 0.800 | 1.000 | 0/0/0/5 | — |
| c02 | 5 | 0.600 | 0.600 | 0.286 | 1/0/2/2 | — |
| c03 | 5 | 1.000 | 0.800 | 1.000 | 4/0/0/1 | — |
| c04 | 5 | 0.800 | 0.800 | 0.762 | 0/0/0/5 | — |
| c05 | 5 | 0.800 | 0.800 | 0.000 | — | — |
| c06 | 5 | 0.600 | 0.600 | 0.000 | — | — |
| c07 | 5 | 0.200 | 0.600 | -0.667 | 0/0/0/5 | — |
| c08 | 5 | 1.000 | 1.000 | — | — | —/—/0 |

## h200-glimmer · single · k=1

| metric | value |
|---|---|
| dialogs | 5 |
| first_try_valid_rate | 1.000 |
| failure_rate | 0.000 |
| mean_seconds | 9.252 |
| p90_seconds | 10.309 |
| mean_prompt_tokens | 3299.600 |
| mean_completion_tokens | 519.000 |
| cost_per_evaluation_usd | 0.000 |
| citation_ok_rate | 1.000 |
| evidence_fallback_rate | 0.000 |

**Gold**

| metric | value |
|---|---|
| dialogs | 5 |
| weighted_agreement | 0.822 |
| total_mae | 4.638 |
| total_bias | 1.514 |
| total_none_mismatches | 0 |

By language:

| language | weighted_agreement |
|---|---|
| EN | 1.000 |
| KZ | 1.000 |
| RU | 0.703 |

By channel:

| channel | weighted_agreement |
|---|---|
| agent chat | 0.950 |
| voice call | 0.307 |

Per criterion:

| criterion | n | agree | majority_baseline | kappa | na tp/fp/fn/tn | gross P/R/support |
|---|---|---|---|---|---|---|
| c01 | 5 | 0.800 | 0.800 | 0.000 | 0/0/0/5 | — |
| c02 | 5 | 0.800 | 0.600 | 0.545 | 3/1/0/1 | — |
| c03 | 5 | 0.800 | 0.800 | 0.000 | 4/1/0/0 | — |
| c04 | 5 | 0.800 | 0.800 | 0.848 | 0/0/0/5 | — |
| c05 | 5 | 0.800 | 0.800 | 0.000 | — | — |
| c06 | 5 | 1.000 | 0.600 | 1.000 | — | — |
| c07 | 5 | 0.600 | 0.600 | 0.000 | 0/0/0/5 | — |
| c08 | 5 | 1.000 | 1.000 | — | — | —/—/0 |

## aigw-sonnet · single · k=1

| metric | value |
|---|---|
| dialogs | 5 |
| first_try_valid_rate | 1.000 |
| failure_rate | 0.000 |
| mean_seconds | 8.186 |
| p90_seconds | 11.321 |
| mean_prompt_tokens | 7344.800 |
| mean_completion_tokens | 1016.000 |
| cost_per_evaluation_usd | 0.025 |
| citation_ok_rate | 1.000 |
| evidence_fallback_rate | 0.000 |

**Gold**

| metric | value |
|---|---|
| dialogs | 5 |
| weighted_agreement | 0.832 |
| total_mae | 10.174 |
| total_bias | -10.174 |
| total_none_mismatches | 0 |

By language:

| language | weighted_agreement |
|---|---|
| EN | 1.000 |
| KZ | 1.000 |
| RU | 0.719 |

By channel:

| channel | weighted_agreement |
|---|---|
| agent chat | 0.901 |
| voice call | 0.554 |

Per criterion:

| criterion | n | agree | majority_baseline | kappa | na tp/fp/fn/tn | gross P/R/support |
|---|---|---|---|---|---|---|
| c01 | 5 | 1.000 | 0.800 | 1.000 | 0/0/0/5 | — |
| c02 | 5 | 1.000 | 0.600 | 1.000 | 3/0/0/2 | — |
| c03 | 5 | 0.800 | 0.800 | 0.444 | 4/0/0/1 | — |
| c04 | 5 | 0.600 | 0.800 | 0.706 | 0/0/0/5 | — |
| c05 | 5 | 1.000 | 0.800 | 1.000 | — | — |
| c06 | 5 | 0.800 | 0.600 | 0.783 | — | — |
| c07 | 5 | 0.600 | 0.600 | 0.000 | 0/0/0/5 | — |
| c08 | 5 | 1.000 | 1.000 | — | — | —/—/0 |

## aigw-luna · single · k=1

| metric | value |
|---|---|
| dialogs | 5 |
| first_try_valid_rate | 1.000 |
| failure_rate | 0.000 |
| mean_seconds | 18.162 |
| p90_seconds | 26.073 |
| mean_prompt_tokens | 4980.000 |
| mean_completion_tokens | 649.800 |
| cost_per_evaluation_usd | 0.001 |
| citation_ok_rate | 1.000 |
| evidence_fallback_rate | 0.000 |

**Gold**

| metric | value |
|---|---|
| dialogs | 5 |
| weighted_agreement | 0.782 |
| total_mae | 13.486 |
| total_bias | -12.910 |
| total_none_mismatches | 0 |

By language:

| language | weighted_agreement |
|---|---|
| EN | 1.000 |
| KZ | 0.851 |
| RU | 0.686 |

By channel:

| channel | weighted_agreement |
|---|---|
| agent chat | 0.913 |
| voice call | 0.257 |

Per criterion:

| criterion | n | agree | majority_baseline | kappa | na tp/fp/fn/tn | gross P/R/support |
|---|---|---|---|---|---|---|
| c01 | 5 | 1.000 | 0.800 | 1.000 | 0/0/0/5 | — |
| c02 | 5 | 0.400 | 0.600 | 0.167 | 1/0/2/2 | — |
| c03 | 5 | 0.800 | 0.800 | 0.444 | 4/0/0/1 | — |
| c04 | 5 | 0.800 | 0.800 | 0.848 | 0/0/0/5 | — |
| c05 | 5 | 1.000 | 0.800 | 1.000 | — | — |
| c06 | 5 | 0.800 | 0.600 | 0.783 | — | — |
| c07 | 5 | 0.600 | 0.600 | 0.000 | 0/0/0/5 | — |
| c08 | 5 | 1.000 | 1.000 | — | — | —/—/0 |

