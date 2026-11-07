# Benchmark · set=gold · gold=all · n=65

## alem-qwen27b · per_criterion · k=1

| metric | value |
|---|---|
| dialogs | 65 |
| first_try_valid_rate | 0.985 |
| failure_rate | 0.000 |
| mean_seconds | 9.016 |
| p90_seconds | 12.872 |
| mean_prompt_tokens | 23535.138 |
| mean_completion_tokens | 972.046 |
| cost_per_evaluation_usd | — |
| citation_ok_rate | 1.000 |
| evidence_fallback_rate | 0.000 |

**Gold**

| metric | value |
|---|---|
| dialogs | 65 |
| weighted_agreement | 0.865 |
| total_mae | 7.399 |
| total_bias | -3.048 |
| total_none_mismatches | 0 |

By language:

| language | weighted_agreement |
|---|---|
| EN | 0.904 |
| KZ | 0.900 |
| RU | 0.833 |

By channel:

| channel | weighted_agreement |
|---|---|
| agent chat | 0.880 |
| voice call | 0.683 |

Per criterion:

| criterion | n | agree | majority_baseline | kappa | na tp/fp/fn/tn | gross P/R/support |
|---|---|---|---|---|---|---|
| c01 | 65 | 0.969 | 0.923 | 0.783 | — | — |
| c02 | 65 | 0.815 | 0.662 | 0.597 | 41/8/2/14 | — |
| c03 | 65 | 1.000 | 0.831 | 1.000 | 54/0/0/11 | — |
| c04 | 65 | 0.815 | 0.738 | 0.852 | 1/0/0/64 | — |
| c05 | 65 | 0.892 | 0.769 | 0.728 | — | — |
| c06 | 65 | 0.692 | 0.723 | 0.620 | — | — |
| c07 | 65 | 0.877 | 0.677 | 0.729 | 5/1/2/57 | — |
| c08 | 65 | 0.969 | 0.877 | 0.840 | — | 1.000/0.750/8 |

