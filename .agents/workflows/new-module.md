# /new-module
Add a new backend module end to end. Ask for the module name first.
1. Write a short implementation plan and wait for approval.
2. Create model + Alembic migration, Pydantic schemas, service package, and router.
3. Add RBAC dependency and audit logging on every route.
4. Add pytest tests (happy path, permission denied, bad input).
5. Add the matching frontend API client and a minimal page or component.
6. Update docs and `.env.example` if needed, then run `/verify`.
