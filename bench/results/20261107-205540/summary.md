# Benchmark · set=gold · gold=all · n=65

## aigw-flashnext · per_criterion · k=1

| metric | value |
|---|---|
| dialogs | 65 |
| first_try_valid_rate | 0.985 |
| failure_rate | 0.000 |
| mean_seconds | 3.729 |
| p90_seconds | 4.734 |
| mean_prompt_tokens | 23533.000 |
| mean_completion_tokens | 1062.215 |
| cost_per_evaluation_usd | — |
| citation_ok_rate | 0.997 |
| evidence_fallback_rate | 0.000 |

**Gold**

| metric | value |
|---|---|
| dialogs | 65 |
| weighted_agreement | 0.873 |
| total_mae | 6.272 |
| total_bias | -0.739 |
| total_none_mismatches | 0 |

By language:

| language | weighted_agreement |
|---|---|
| EN | 0.878 |
| KZ | 0.904 |
| RU | 0.857 |

By channel:

| channel | weighted_agreement |
|---|---|
| agent chat | 0.903 |
| voice call | 0.515 |

Per criterion:

| criterion | n | agree | majority_baseline | kappa | na tp/fp/fn/tn | gross P/R/support |
|---|---|---|---|---|---|---|
| c01 | 65 | 0.969 | 0.923 | 0.735 | — | — |
| c02 | 65 | 0.800 | 0.662 | 0.630 | 35/3/8/19 | — |
| c03 | 65 | 1.000 | 0.831 | 1.000 | 54/0/0/11 | — |
| c04 | 65 | 0.846 | 0.738 | 0.847 | 1/0/0/64 | — |
| c05 | 65 | 0.877 | 0.769 | 0.653 | — | — |
| c06 | 65 | 0.723 | 0.723 | 0.590 | — | — |
| c07 | 65 | 0.908 | 0.677 | 0.789 | 5/0/2/58 | — |
| c08 | 65 | 1.000 | 0.877 | 1.000 | — | 1.000/1.000/8 |

