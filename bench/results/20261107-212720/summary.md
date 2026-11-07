# Benchmark · set=gold · gold=all · n=65

## or-deepseek-pro · single · k=1

| metric | value |
|---|---|
| dialogs | 65 |
| first_try_valid_rate | 1.000 |
| failure_rate | 0.185 |
| mean_seconds | 17.006 |
| p90_seconds | 66.778 |
| mean_prompt_tokens | 4544.340 |
| mean_completion_tokens | 704.358 |
| cost_per_evaluation_usd | 0.004 |
| citation_ok_rate | 1.000 |
| evidence_fallback_rate | 0.000 |

**Gold**

| metric | value |
|---|---|
| dialogs | 53 |
| weighted_agreement | 0.859 |
| total_mae | 8.176 |
| total_bias | -3.576 |
| total_none_mismatches | 0 |

By language:

| language | weighted_agreement |
|---|---|
| EN | 0.908 |
| KZ | 0.873 |
| RU | 0.824 |

By channel:

| channel | weighted_agreement |
|---|---|
| agent chat | 0.869 |
| voice call | 0.686 |

Per criterion:

| criterion | n | agree | majority_baseline | kappa | na tp/fp/fn/tn | gross P/R/support |
|---|---|---|---|---|---|---|
| c01 | 53 | 0.925 | 0.906 | 0.462 | — | — |
| c02 | 53 | 0.868 | 0.698 | 0.741 | 32/0/5/16 | — |
| c03 | 53 | 0.981 | 0.830 | 0.936 | 44/0/0/9 | — |
| c04 | 53 | 0.717 | 0.717 | 0.703 | 1/0/0/52 | — |
| c05 | 53 | 0.906 | 0.774 | 0.753 | — | — |
| c06 | 53 | 0.774 | 0.736 | 0.684 | — | — |
| c07 | 53 | 0.868 | 0.679 | 0.693 | 3/0/2/48 | — |
| c08 | 53 | 1.000 | 0.849 | 1.000 | — | 1.000/1.000/8 |

