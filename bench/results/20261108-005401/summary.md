# Benchmark · set=gold · gold=all · n=65

## h200-kz · single · k=1

| metric | value |
|---|---|
| dialogs | 65 |
| first_try_valid_rate | 0.985 |
| failure_rate | 0.000 |
| mean_seconds | 18.206 |
| p90_seconds | 50.211 |
| mean_prompt_tokens | 4328.738 |
| mean_completion_tokens | 637.000 |
| cost_per_evaluation_usd | 0.001 |
| citation_ok_rate | 0.992 |
| evidence_fallback_rate | 0.002 |

**Gold**

| metric | value |
|---|---|
| dialogs | 65 |
| weighted_agreement | 0.827 |
| total_mae | 11.769 |
| total_bias | 2.250 |
| total_none_mismatches | 0 |

By language:

| language | weighted_agreement |
|---|---|
| EN | 0.868 |
| KZ | 0.858 |
| RU | 0.796 |

By channel:

| channel | weighted_agreement |
|---|---|
| agent chat | 0.842 |
| voice call | 0.644 |

Per criterion:

| criterion | n | agree | majority_baseline | kappa | na tp/fp/fn/tn | gross P/R/support |
|---|---|---|---|---|---|---|
| c01 | 65 | 0.954 | 0.923 | 0.642 | — | — |
| c02 | 65 | 0.785 | 0.662 | 0.601 | 33/4/10/18 | — |
| c03 | 65 | 0.969 | 0.831 | 0.903 | 52/0/2/11 | — |
| c04 | 65 | 0.754 | 0.738 | 0.602 | 1/0/0/64 | — |
| c05 | 65 | 0.877 | 0.785 | 0.616 | — | — |
| c06 | 65 | 0.754 | 0.723 | 0.491 | — | — |
| c07 | 65 | 0.462 | 0.738 | 0.094 | 0/0/7/58 | — |
| c08 | 65 | 0.985 | 0.877 | 0.932 | — | 0.889/1.000/8 |

