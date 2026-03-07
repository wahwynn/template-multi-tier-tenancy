# Project Conventions

This file is the single source of truth for coding standards, style guides, and development workflows in this repository. All AI assistants and developers should follow these conventions regardless of tooling.

> **Important**: Read [PROJECT.md](PROJECT.md) first to understand the project type and stack. Use that metadata to determine which structure layout and conventions apply.

## Key Conventions

1. **Read before editing**: Always read a file before modifying it. Understand existing patterns before introducing new ones.
2. **No over-engineering**: Implement only what is asked. Do not add extra abstractions, error handling for impossible cases, or speculative features.
3. **Secrets**: Never hardcode credentials. Use environment variables. Update `.env.example` when adding new required variables.
4. **File creation**: Prefer editing existing files over creating new ones. Only create files when clearly necessary.
5. **TDD — red/green workflow**: Write a failing test first, confirm it fails for the right reason (red), implement the minimum code to make it pass (green), then refactor. Never write implementation code without a failing test driving it.
6. **Test verification on every change**: Run the full test suite after every change — no exceptions. Do not proceed to the next step if any test is failing.
7. **Migrations**: Database schema changes go in versioned migration files. Never modify existing migrations — add new ones.
8. **Dependency discipline**: Prefer standard library over third-party packages. Justify every new dependency. Pin versions — never use unpinned ranges in production config.
9. **Error handling**: Never swallow exceptions silently — log or re-raise. Fail fast at startup if required config or env vars are missing.
10. **Debugging**: Reproduce the bug with a failing test before touching any code. Understand the root cause before fixing — don't patch symptoms.
11. **Commit hygiene**: One logical change per commit; do not bundle unrelated fixes. Never commit commented-out code or debug statements (`print`, `console.log`, `debugger`).
12. **Logging**: Use structured logging (key=value or JSON). Never log secrets or PII. Use the right level: `DEBUG` for dev noise, `INFO` for state transitions, `ERROR` for failures.
13. **API design**: Follow REST conventions; version APIs from day one (`/v1/...`). Return consistent error shapes across all endpoints.
14. **Performance**: Do not optimize prematurely — profile before changing working code. Avoid N+1 queries; prefer eager loading or batch fetching.
15. **Security**: Validate and sanitize all input at system boundaries. Apply least-privilege — request only the permissions a component actually needs.
16. **Breaking changes**: Deprecate before removing. Never silently change the behaviour of an existing interface.
17. **README upkeep**: After every change — new feature, config update, dependency addition, workflow change — update `README.md` so setup and usage instructions stay accurate and complete.

## Development Workflow

### Environment Setup

1. Copy `.env.example` to `.env` and fill in values
2. Install dependencies (command depends on chosen stack)
3. Run database migrations
4. Start the development server

### Git Conventions

- Branch names: `<username>/<short-description>`
- Commit messages: imperative mood, present tense (e.g., `Add auth middleware`, not `Added`)
- Never commit secrets, database files, or build artifacts (enforced by `.gitignore`)
- PRs require a description of what changed and why

### Code Style

**Python** (when used):

- Environment manager: `uv` (always use `uv` — never bare `pip` or `venv` directly)
- Formatter: `ruff format` (opinionated, non-negotiable — do not override defaults)
- Linter: `ruff check` (fix all auto-fixable issues with `ruff check --fix` before committing)
- Type checker: `ty` (from Astral, same ecosystem as ruff)
- Test runner: `pytest`
- All new code must pass `ruff` and `ty` with no errors before committing

**Python Style Guide**:

- **Type hints are mandatory** on all function signatures — parameters and return types. No untyped `def` in new code.
- Use built-in generics (`list[str]`, `dict[str, int]`, `tuple[int, ...]`) — never import `List`, `Dict`, `Tuple` from `typing`.
- Use `X | None` union syntax instead of `Optional[X]`.
- Annotate class attributes and instance variables in `__init__` or as class-level annotations.
- Use `TypeAlias` for complex type expressions to keep signatures readable.
- Prefer `dataclasses.dataclass` or Pydantic `BaseModel` over plain dicts for structured data.
- Use `Enum` or `StrEnum` for fixed sets of values — never bare string constants.
- Prefer `pathlib.Path` over `os.path` for filesystem operations.
- Use f-strings for string formatting — never `%` or `.format()`. **Exception**: use `%`-style lazy formatting in `logging` calls (`logger.info("User %s", user_id)`) so the string is only interpolated when the log level is active.
- Prefer list/dict/set comprehensions over `map`/`filter` with lambdas.
- Follow PEP 8 naming: `snake_case` for functions/variables, `PascalCase` for classes, `UPPER_SNAKE_CASE` for constants.
- Keep functions short and single-purpose. If a function exceeds ~30 lines, consider splitting it.
- Use context managers (`with` statements) for resource management — files, DB connections, locks.
- **Import ordering**: stdlib → third-party → local, enforced by `ruff` with `isort` rules enabled.
- **Docstrings**: Required on public APIs (modules, classes, public functions). Use Google-style format. Skip for obvious/trivial methods.
- **`__all__` exports**: Modules with public APIs should define `__all__` to explicitly declare their public surface.
- **Async conventions**: Prefer `asyncio.TaskGroup` over `asyncio.gather`. Never mix sync and async I/O — use async all the way down or not at all.
- **Minimum Python version**: Python 3.14+ — no backwards compatibility shims.
- **Config loading**: Use Pydantic `BaseSettings` for typed environment variable parsing with validation.
- **Custom exceptions**: Define project-specific exception hierarchies inheriting from a base project exception. Use built-in exceptions only for genuinely generic errors.
- **Dependency injection**: Prefer constructor injection over module-level globals. Pass dependencies explicitly — do not rely on hidden shared state.

**Python Testing Conventions**:

- **Test naming**: `test_<unit>_<scenario>_<expected>` (e.g., `test_create_note_missing_title_raises_validation_error`).
- **Fixtures over setup**: Use `pytest` fixtures — never `setUp`/`tearDown` from `unittest`.
- **Parametrize**: Use `@pytest.mark.parametrize` for covering multiple input/output cases without duplicating test bodies.
- **No logic in tests**: No conditionals, loops, or try/except in test bodies. Each test should be a straight-line sequence of arrange/act/assert.
- **Factory pattern**: Use factories (e.g., `factory_boy` or simple helper functions) to create test data — avoid raw fixture dictionaries or inline model construction.

**Docker Conventions**:

- Use official slim/distroless base images — never `latest` tag.
- Multi-stage builds: separate build and runtime stages to minimize final image size.
- Run as non-root user in production containers.
- Pin base image digests or specific version tags for reproducibility.

**JavaScript / TypeScript** (when used):

- Follow the project's chosen formatter (Prettier or Biome)
- Strict TypeScript — no `any` types without explicit justification
- Test runner: Vitest or Jest

**JavaScript / TypeScript Style Guide**:

- **Strict mode**: Use `"strict": true` and `"noUncheckedIndexedAccess": true` in `tsconfig.json`. Never loosen strictness to fix type errors.
- **Type inference**: Let TypeScript infer return types and variable types when obvious. Only annotate explicitly when the inferred type is too broad or unclear.
- **No `any`**: Use `unknown` and narrow with type guards. If `any` is truly unavoidable, add a `// eslint-disable` comment with justification.
- **Prefer `interface` over `type`** for object shapes — use `type` only for unions, intersections, and mapped types.
- **Immutability by default**: Use `const` always — never `let` unless reassignment is required, never `var`. Prefer `readonly` on properties and `as const` for literal objects/arrays.
- **Nullability**: Use strict null checks. Prefer explicit `null` returns over `undefined`. Use optional chaining (`?.`) and nullish coalescing (`??`) — never logical OR (`||`) for default values.
- **Async/await over `.then()`**: Always use `async`/`await` — never raw Promise chains. Handle errors with try/catch at the appropriate boundary, not on every call.
- **No classes unless necessary**: Prefer plain functions and objects. Use classes only when you need inheritance, lifecycle hooks, or framework requirements (e.g., decorators).
- **Named exports over default exports**: Use named exports for everything — default exports make refactoring and auto-imports harder.
- **Barrel files**: Avoid `index.ts` re-export barrels — they hurt tree-shaking and create circular dependency risks. Import directly from the source module.
- **Error handling**: Throw `Error` subclasses — never throw strings or plain objects. Define project-specific error classes for domain errors.
- **Enums**: Avoid TypeScript `enum` — use `as const` objects with derived union types instead.
- **Array methods over loops**: Prefer `.map()`, `.filter()`, `.reduce()`, `.find()` over `for` loops. Use `for...of` when side effects are the goal.
- **Template literals**: Use template literals for string interpolation — never string concatenation with `+`.
- **Destructuring**: Use destructuring for function parameters and object access. Keep destructuring shallow — avoid deeply nested patterns.
- **Early returns**: Use guard clauses and early returns to reduce nesting. Avoid `else` after a return.
- **Import ordering**: Framework/library imports → third-party → local modules → types, enforced by the chosen linter.

### Running Tests

Once implemented, tests should be runnable with a single command. Ensure all tests pass before pushing. Document the exact command in this file once chosen.

## Adding New Features

Follow the red/green/refactor cycle for every feature:

1. Check if a similar pattern already exists in the codebase and follow it
2. **Red**: Write a failing test that describes the expected behaviour
3. **Green**: Implement the minimum code in the appropriate layer (model → service → API → UI) to make the test pass
4. **Refactor**: Clean up without breaking the passing test; run the suite again to confirm
5. Update `.env.example` if new environment variables are required
6. Document any non-obvious design decisions in code comments
