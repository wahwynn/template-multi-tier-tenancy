# Project Metadata

This file describes the current state of the project. Update it as decisions are made.

- **Project type**: (not yet decided — set to `full-stack`, `backend-only`, or `frontend-only` when the stack is chosen)
- **Backend framework**: (not yet decided)
- **Frontend framework**: (not yet decided)
- **Database**: (not yet decided)

## Project Structure

Choose the layout that matches the project type above. **Delete the sections that don't apply** once the project type is decided.

**Full-stack applications**:

```
frontend/          ← All client-side code (React, Vue, etc.)
backend/           ← All server-side code (API, services, models)
docker-compose.yml ← Orchestration for local development
```

- **Never mix frontend and backend code** in the same directory.
- Each directory should be a self-contained project with its own dependency management (`package.json` for frontend, `pyproject.toml` for backend).
- Each directory should have its own `Dockerfile` and `.dockerignore` when containerized.
- Shared types or contracts (e.g., API schemas) should be defined in the backend and consumed by the frontend — not duplicated.

**Backend-only / API-only applications**:

```
app/               ← Application code (routes, services, models)
tests/             ← All tests, mirroring the app/ structure
migrations/        ← Database migration files
```

**Frontend-only applications**:

```
src/               ← Application source code
public/            ← Static assets
tests/             ← Test files
```

**General rules** (all project types):

- Keep configuration files (`pyproject.toml`, `package.json`, `docker-compose.yml`) at the project root.
- Tests live in a dedicated `tests/` directory — never co-located with source code.
- Keep a flat structure until complexity demands nesting. Do not create deep directory hierarchies prematurely.
