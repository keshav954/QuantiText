# Grounding & Hallucination Evaluation Results

> Generated: 2026-10-17 18:25
> Tests: 5 | Hallucination-free: 3/5

## Results

| Test | Numbers Found | Grounded | Ungrounded | Grounding Rate | Hallucination Free |
|------|--------------|----------|------------|----------------|-------------------|
| Template Narrative | 2 | 2 | 0 | 100.0% | ✅ |
| Hallucinated Narrative (control) | 3 | 0 | 3 | 0.0% | ❌ |
| Partial Grounding | 3 | 2 | 1 | 66.7% | ❌ |
| Empty Data | 0 | 0 | 0 | 100.0% | ✅ |
| SQL Result Grounding | 2 | 2 | 0 | 100.0% | ✅ |

## Grounding Methodology

1. Extract all numeric values from LLM-generated text
2. Extract all numeric values from source data (JSON)
3. Check that every number in the output exists in the source
4. Flag ungrounded numbers as potential hallucinations

## Safeguards Implemented

- Template narrative fallback when LLM unavailable (100% grounding guaranteed)
- SQL validator rejects non-SELECT queries
- Read-only DB connection for NL2SQL execution
- Self-repair loop (max 2 retries) for SQL errors
- No customer PII sent to LLM — only aggregated figures

---
⚠️ All numbers from script execution. Never fabricated.