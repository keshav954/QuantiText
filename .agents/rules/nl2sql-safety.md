# NL2SQL safety (always apply)

When touching `backend/app/services/nl2sql/`:
- LLM-generated SQL must pass the validator BEFORE execution: parse with `sqlglot`, allow SELECT only,
  reject multiple statements, allowlist tables and columns (analytics views only, never raw tables),
  force a LIMIT, and set a statement timeout.
- Execute only with the read-only DB role (`bi_readonly`).
- Apply the caller's role and org filters to every query.
- If SQL is invalid, ambiguous, or returns an error, retry at most 2 times with the error fed back, then ask the user a clarifying question. Never guess silently.
- Log question, generated SQL, executed SQL, row count and latency to `audit_log`.
- Every number in an LLM explanation must be traceable to the query result. Add or keep the grounding check.
- Any change to prompts, validator or schema linking requires re-running the gold question set (`/eval-nl2sql`).
