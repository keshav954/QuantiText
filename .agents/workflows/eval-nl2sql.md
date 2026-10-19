# /eval-nl2sql
Evaluate the Copilot against the gold question set in `docs/eval/nl2sql_gold.jsonl`
(fields: question, difficulty, gold_sql).
1. Run each question through the pipeline in the current configuration.
2. Compare result sets of generated SQL vs gold SQL (execution accuracy, order-insensitive).
3. Output a table by difficulty (easy/medium/hard): accuracy, avg retries, avg latency, validator rejections.
4. Save results to `docs/eval/results/<date>-<config>.json` and print the table.
5. List the 5 worst failures with a one-line cause each. Do not edit the gold set to improve scores.
