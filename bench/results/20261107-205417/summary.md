# Benchmark · set=gold · gold=all · n=65

## alem-qwen27b · single · k=1

| metric | value |
|---|---|
| dialogs | 65 |
| first_try_valid_rate | 1.000 |
| failure_rate | 0.000 |
| mean_seconds | 13.157 |
| p90_seconds | 14.920 |
| mean_prompt_tokens | 3837.138 |
| mean_completion_tokens | 748.308 |
| cost_per_evaluation_usd | — |
| citation_ok_rate | 0.998 |
| evidence_fallback_rate | 0.000 |

**Gold**

| metric | value |
|---|---|
| dialogs | 65 |
| weighted_agreement | 0.898 |
| total_mae | 6.575 |
| total_bias | 4.170 |
| total_none_mismatches | 0 |

By language:

| language | weighted_agreement |
|---|---|
| EN | 0.944 |
| KZ | 0.937 |
| RU | 0.861 |

By channel:

| channel | weighted_agreement |
|---|---|
| agent chat | 0.919 |
| voice call | 0.644 |

Per criterion:

| criterion | n | agree | majority_baseline | kappa | na tp/fp/fn/tn | gross P/R/support |
|---|---|---|---|---|---|---|
| c01 | 65 | 0.969 | 0.923 | 0.783 | — | — |
| c02 | 65 | 0.892 | 0.662 | 0.786 | 40/2/3/20 | — |
| c03 | 65 | 1.000 | 0.831 | 1.000 | 54/0/0/11 | — |
| c04 | 65 | 0.846 | 0.738 | 0.884 | 1/0/0/64 | — |
| c05 | 65 | 0.862 | 0.769 | 0.558 | — | — |
| c06 | 65 | 0.815 | 0.723 | 0.663 | — | — |
| c07 | 65 | 0.908 | 0.677 | 0.817 | 6/1/1/57 | — |
| c08 | 65 | 1.000 | 0.877 | 1.000 | — | 1.000/1.000/8 |

