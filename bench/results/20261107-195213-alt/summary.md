# Benchmark · set=gold · gold=all · n=65

## h200-glimmer · single · k=1

| metric | value |
|---|---|
| dialogs | 65 |
| first_try_valid_rate | 1.000 |
| failure_rate | 0.000 |
| mean_seconds | 23.621 |
| p90_seconds | 68.995 |
| mean_prompt_tokens | 3207.985 |
| mean_completion_tokens | 528.508 |
| cost_per_evaluation_usd | 0.001 |
| citation_ok_rate | 1.000 |
| evidence_fallback_rate | 0.000 |

**Gold**

| metric | value |
|---|---|
| dialogs | 65 |
| weighted_agreement | 0.823 |
| total_mae | 8.805 |
| total_bias | -2.756 |
| total_none_mismatches | 0 |

By language:

| language | weighted_agreement |
|---|---|
| EN | 0.884 |
| KZ | 0.868 |
| RU | 0.777 |

By channel:

| channel | weighted_agreement |
|---|---|
| agent chat | 0.845 |
| voice call | 0.554 |

Per criterion:

| criterion | n | agree | majority_baseline | kappa | na tp/fp/fn/tn | gross P/R/support |
|---|---|---|---|---|---|---|
| c01 | 65 | 0.938 | 0.923 | 0.567 | — | — |
| c02 | 65 | 0.738 | 0.662 | 0.358 | 42/14/1/8 | — |
| c03 | 65 | 0.969 | 0.831 | 0.899 | 53/0/1/11 | — |
| c04 | 65 | 0.738 | 0.738 | 0.763 | 1/0/0/64 | — |
| c05 | 65 | 0.892 | 0.769 | 0.689 | — | — |
| c06 | 65 | 0.708 | 0.723 | 0.581 | — | — |
| c07 | 65 | 0.692 | 0.677 | 0.258 | 4/4/3/54 | — |
| c08 | 65 | 1.000 | 0.877 | 1.000 | — | 1.000/1.000/8 |

## h200-gptoss · single · k=1

| metric | value |
|---|---|
| dialogs | 65 |
| first_try_valid_rate | 0.892 |
| failure_rate | 0.000 |
| mean_seconds | 16.979 |
| p90_seconds | 50.933 |
| mean_prompt_tokens | 3919.215 |
| mean_completion_tokens | 979.646 |
| cost_per_evaluation_usd | 0.001 |
| citation_ok_rate | 0.997 |
| evidence_fallback_rate | 0.000 |

**Gold**

| metric | value |
|---|---|
| dialogs | 65 |
| weighted_agreement | 0.803 |
| total_mae | 10.490 |
| total_bias | -6.468 |
| total_none_mismatches | 0 |

By language:

| language | weighted_agreement |
|---|---|
| EN | 0.888 |
| KZ | 0.815 |
| RU | 0.762 |

By channel:

| channel | weighted_agreement |
|---|---|
| agent chat | 0.832 |
| voice call | 0.463 |

Per criterion:

| criterion | n | agree | majority_baseline | kappa | na tp/fp/fn/tn | gross P/R/support |
|---|---|---|---|---|---|---|
| c01 | 65 | 0.985 | 0.923 | 0.881 | — | — |
| c02 | 65 | 0.723 | 0.662 | 0.529 | 30/1/13/21 | — |
| c03 | 65 | 0.862 | 0.831 | 0.635 | 47/0/7/11 | — |
| c04 | 65 | 0.708 | 0.738 | 0.652 | 1/0/0/64 | — |
| c05 | 65 | 0.846 | 0.769 | 0.586 | — | — |
| c06 | 65 | 0.785 | 0.723 | 0.675 | — | — |
| c07 | 65 | 0.723 | 0.677 | 0.284 | 0/0/7/58 | — |
| c08 | 65 | 0.969 | 0.877 | 0.871 | — | 0.800/1.000/8 |

## aigw-luna · single · k=1

| metric | value |
|---|---|
| dialogs | 65 |
| first_try_valid_rate | 0.985 |
| failure_rate | 0.000 |
| mean_seconds | 17.753 |
| p90_seconds | 26.873 |
| mean_prompt_tokens | 5116.615 |
| mean_completion_tokens | 694.354 |
| cost_per_evaluation_usd | 0.001 |
| citation_ok_rate | 1.000 |
| evidence_fallback_rate | 0.000 |

**Gold**

| metric | value |
|---|---|
| dialogs | 65 |
| weighted_agreement | 0.859 |
| total_mae | 7.586 |
| total_bias | -3.238 |
| total_none_mismatches | 0 |

By language:

| language | weighted_agreement |
|---|---|
| EN | 0.931 |
| KZ | 0.851 |
| RU | 0.831 |

By channel:

| channel | weighted_agreement |
|---|---|
| agent chat | 0.884 |
| voice call | 0.562 |

Per criterion:

| criterion | n | agree | majority_baseline | kappa | na tp/fp/fn/tn | gross P/R/support |
|---|---|---|---|---|---|---|
| c01 | 65 | 0.969 | 0.923 | 0.735 | — | — |
| c02 | 65 | 0.785 | 0.662 | 0.620 | 34/1/9/21 | — |
| c03 | 65 | 0.969 | 0.831 | 0.899 | 53/0/1/11 | — |
| c04 | 65 | 0.785 | 0.738 | 0.809 | 1/0/0/64 | — |
| c05 | 65 | 0.877 | 0.769 | 0.669 | — | — |
| c06 | 65 | 0.769 | 0.723 | 0.728 | — | — |
| c07 | 65 | 0.908 | 0.677 | 0.790 | 6/0/1/58 | — |
| c08 | 65 | 0.985 | 0.877 | 0.932 | — | 0.889/1.000/8 |

