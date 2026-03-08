# Project Metadata

- **Project type**: full-stack
- **Backend framework**: Django 6 + Django REST Framework
- **Frontend framework**: Next.js 15 (App Router) + TypeScript
- **Database**: PostgreSQL 16 (three-tier schema isolation: public / shared / tenant)
- **Cache**: Redis 7

## Project Structure

```
frontend/          ← Next.js frontend
backend/           ← Django backend
docs/              ← Architecture design docs and implementation plans
CONVENTIONS.md     ← Coding standards and development workflow
docker-compose.yml ← Local development orchestration
```

See `docs/plans/2026-03-07-multi-tenant-scaffold-design.md` for architecture decisions.
