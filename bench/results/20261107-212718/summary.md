# Benchmark · set=gold · gold=all · n=65

## or-gemini-argon · single · k=1

| metric | value |
|---|---|
| dialogs | 65 |
| first_try_valid_rate | 1.000 |
| failure_rate | 0.431 |
| mean_seconds | 23.409 |
| p90_seconds | 67.680 |
| mean_prompt_tokens | 6389.243 |
| mean_completion_tokens | 808.297 |
| cost_per_evaluation_usd | 0.021 |
| citation_ok_rate | 1.000 |
| evidence_fallback_rate | 0.000 |

**Gold**

| metric | value |
|---|---|
| dialogs | 37 |
| weighted_agreement | 0.877 |
| total_mae | 8.118 |
| total_bias | -5.084 |
| total_none_mismatches | 0 |

By language:

| language | weighted_agreement |
|---|---|
| EN | 0.978 |
| KZ | 0.857 |
| RU | 0.838 |

By channel:

| channel | weighted_agreement |
|---|---|
| agent chat | 0.902 |
| voice call | 0.663 |

Per criterion:

| criterion | n | agree | majority_baseline | kappa | na tp/fp/fn/tn | gross P/R/support |
|---|---|---|---|---|---|---|
| c01 | 37 | 1.000 | 0.973 | 1.000 | — | — |
| c02 | 37 | 0.892 | 0.676 | 0.773 | 25/1/0/11 | — |
| c03 | 37 | 0.973 | 0.811 | 0.915 | 30/0/0/7 | — |
| c04 | 37 | 0.811 | 0.730 | 0.721 | 0/0/0/37 | — |
| c05 | 37 | 0.892 | 0.784 | 0.730 | — | — |
| c06 | 37 | 0.676 | 0.703 | 0.742 | — | — |
| c07 | 37 | 1.000 | 0.676 | 1.000 | 4/0/0/33 | — |
| c08 | 37 | 0.973 | 0.865 | 0.893 | — | 0.833/1.000/5 |

