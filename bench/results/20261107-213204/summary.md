# Benchmark · set=gold · gold=all · n=65

## h200-gemma · per_criterion · k=1

| metric | value |
|---|---|
| dialogs | 65 |
| first_try_valid_rate | 0.985 |
| failure_rate | 0.000 |
| mean_seconds | 31.772 |
| p90_seconds | 66.482 |
| mean_prompt_tokens | 24832.923 |
| mean_completion_tokens | 659.338 |
| cost_per_evaluation_usd | 0.003 |
| citation_ok_rate | 1.000 |
| evidence_fallback_rate | 0.000 |

**Gold**

| metric | value |
|---|---|
| dialogs | 65 |
| weighted_agreement | 0.911 |
| total_mae | 5.776 |
| total_bias | -0.963 |
| total_none_mismatches | 0 |

By language:

| language | weighted_agreement |
|---|---|
| EN | 0.944 |
| KZ | 0.957 |
| RU | 0.877 |

By channel:

| channel | weighted_agreement |
|---|---|
| agent chat | 0.936 |
| voice call | 0.614 |

Per criterion:

| criterion | n | agree | majority_baseline | kappa | na tp/fp/fn/tn | gross P/R/support |
|---|---|---|---|---|---|---|
| c01 | 65 | 0.969 | 0.923 | 0.735 | — | — |
| c02 | 65 | 0.954 | 0.662 | 0.903 | 43/3/0/19 | — |
| c03 | 65 | 0.985 | 0.831 | 0.948 | 54/0/0/11 | — |
| c04 | 65 | 0.877 | 0.738 | 0.890 | 1/0/0/64 | — |
| c05 | 65 | 0.908 | 0.785 | 0.753 | — | — |
| c06 | 65 | 0.769 | 0.723 | 0.602 | — | — |
| c07 | 65 | 0.923 | 0.738 | 0.816 | 5/0/2/58 | — |
| c08 | 65 | 1.000 | 0.877 | 1.000 | — | 1.000/1.000/8 |

