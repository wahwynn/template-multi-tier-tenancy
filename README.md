# Empty Web Application Template

A generic template repository for building web applications. The project type and tech stack are customizable — see [PROJECT.md](PROJECT.md) for current status and configuration options.

## Getting Started

1. **Review the project metadata:**

   Read [PROJECT.md](PROJECT.md) to understand the current project type and stack decisions.

2. **Set up environment variables:**

   ```bash
   cp .env.example .env
   ```

3. **Install dependencies:**

   ```bash
   make install
   ```

4. **Run quality checks:**

   ```bash
   make check
   ```

## Available Commands

Run `make help` to see all available commands:

| Command          | Description                                     |
| ---------------- | ----------------------------------------------- |
| `make install`   | Install dependencies                            |
| `make lint`      | Run linter                                      |
| `make format`    | Format code and fix auto-fixable lint issues    |
| `make typecheck` | Run type checker                                |
| `make test`      | Run test suite                                  |
| `make check`     | Run all quality gates (lint + typecheck + test) |
| `make clean`     | Remove build artifacts and caches               |

## Project Structure

See [PROJECT.md](PROJECT.md) for the directory layout and stack decisions.

## Conventions

All coding standards, style guides, and development workflows are documented in [CONVENTIONS.md](CONVENTIONS.md).

## AI Agent Configuration

This repo includes configuration for multiple AI coding assistants:

| File                              | Agent          |
| --------------------------------- | -------------- |
| `CLAUDE.md`                       | Claude Code    |
| `.cursorrules`                    | Cursor         |
| `.github/copilot-instructions.md` | GitHub Copilot |

All agents follow the shared conventions in `CONVENTIONS.md`.

## License

See [LICENSE](LICENSE) for details.
