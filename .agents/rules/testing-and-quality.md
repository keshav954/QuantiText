# Testing and quality (always apply)

- Write tests with the code, not afterwards. Prefer pytest with fixtures and a test database.
- ML code: test shapes, no-leakage (train data strictly before validation), and that metrics are computed correctly.
- Time-series validation must be walk-forward. Never shuffle time-series data.
- Always compare against a baseline (naive / seasonal-naive). A model that does not beat the baseline is reported as such.
- Run the full test suite and lint before declaring a task complete, and show the output.
- If you cannot verify something (e.g. no API key available), say so explicitly instead of assuming it works.
