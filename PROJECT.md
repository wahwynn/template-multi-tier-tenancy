# Project Metadata

- **Project type**: full-stack
- **Backend framework**: Django 5.x + Django REST Framework
- **Frontend framework**: Next.js 15 (App Router) + TypeScript
- **Database**: PostgreSQL 16 (schema-per-tenant isolation)
- **Cache**: Redis 7

## Project Structure

```
frontend/          ← Next.js frontend
backend/           ← Django backend
docker-compose.yml ← Local development orchestration
```

See `docs/plans/2026-03-07-multi-tenant-scaffold-design.md` for full architecture decisions.
