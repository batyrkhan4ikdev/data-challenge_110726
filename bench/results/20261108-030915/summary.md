# Benchmark · set=gold · gold=all · n=65

## h200-gemma · single · k=1

| metric | value |
|---|---|
| dialogs | 65 |
| first_try_valid_rate | 0.969 |
| failure_rate | 0.000 |
| mean_seconds | 16.062 |
| p90_seconds | 49.568 |
| mean_prompt_tokens | 4159.615 |
| mean_completion_tokens | 536.431 |
| cost_per_evaluation_usd | 0.001 |
| citation_ok_rate | 1.000 |
| evidence_fallback_rate | 0.000 |

**Gold**

| metric | value |
|---|---|
| dialogs | 65 |
| weighted_agreement | 0.899 |
| total_mae | 5.474 |
| total_bias | 3.056 |
| total_none_mismatches | 0 |

By language:

| language | weighted_agreement |
|---|---|
| EN | 0.934 |
| KZ | 0.970 |
| RU | 0.853 |

By channel:

| channel | weighted_agreement |
|---|---|
| agent chat | 0.925 |
| voice call | 0.584 |

Per criterion:

| criterion | n | agree | majority_baseline | kappa | na tp/fp/fn/tn | gross P/R/support |
|---|---|---|---|---|---|---|
| c01 | 65 | 0.969 | 0.923 | 0.735 | — | — |
| c02 | 65 | 0.938 | 0.662 | 0.875 | 42/2/1/20 | — |
| c03 | 65 | 0.969 | 0.831 | 0.902 | 52/0/2/11 | — |
| c04 | 65 | 0.862 | 0.738 | 0.898 | 1/0/0/64 | — |
| c05 | 65 | 0.908 | 0.785 | 0.695 | — | — |
| c06 | 65 | 0.738 | 0.723 | 0.531 | — | — |
| c07 | 65 | 0.938 | 0.738 | 0.843 | 6/0/1/58 | — |
| c08 | 65 | 1.000 | 0.877 | 1.000 | — | 1.000/1.000/8 |

