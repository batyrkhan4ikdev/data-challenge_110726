# Benchmark · set=gold · gold=all · n=65

## alem-deepseek · single · k=1

| metric | value |
|---|---|
| dialogs | 65 |
| first_try_valid_rate | 1.000 |
| failure_rate | 0.000 |
| mean_seconds | 14.777 |
| p90_seconds | 17.642 |
| mean_prompt_tokens | 4155.031 |
| mean_completion_tokens | 742.815 |
| cost_per_evaluation_usd | — |
| citation_ok_rate | 0.997 |
| evidence_fallback_rate | 0.000 |

**Gold**

| metric | value |
|---|---|
| dialogs | 65 |
| weighted_agreement | 0.874 |
| total_mae | 6.290 |
| total_bias | -2.115 |
| total_none_mismatches | 0 |

By language:

| language | weighted_agreement |
|---|---|
| EN | 0.934 |
| KZ | 0.891 |
| RU | 0.840 |

By channel:

| channel | weighted_agreement |
|---|---|
| agent chat | 0.896 |
| voice call | 0.604 |

Per criterion:

| criterion | n | agree | majority_baseline | kappa | na tp/fp/fn/tn | gross P/R/support |
|---|---|---|---|---|---|---|
| c01 | 65 | 0.969 | 0.923 | 0.735 | — | — |
| c02 | 65 | 0.908 | 0.662 | 0.821 | 40/1/3/21 | — |
| c03 | 65 | 0.985 | 0.831 | 0.945 | 54/1/0/10 | — |
| c04 | 65 | 0.754 | 0.738 | 0.829 | 1/0/0/64 | — |
| c05 | 65 | 0.892 | 0.769 | 0.717 | — | — |
| c06 | 65 | 0.754 | 0.723 | 0.686 | — | — |
| c07 | 65 | 0.892 | 0.677 | 0.749 | 4/0/3/58 | — |
| c08 | 65 | 1.000 | 0.877 | 1.000 | — | 1.000/1.000/8 |

