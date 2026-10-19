# Security and privacy (always apply)

- Passwords hashed with argon2 or bcrypt. JWTs are short-lived. Roles: admin, manager, analyst, viewer.
- RBAC is enforced in a shared FastAPI dependency, not ad-hoc in each route.
- Rate-limit `/query` and `/reports/generate`.
- Mask or aggregate sensitive fields before any LLM call. Reports send only aggregated JSON.
- Secrets come from environment variables. If you spot a hardcoded secret, remove it and report it.
- Add an audit log entry for logins, queries, approvals and exports.
