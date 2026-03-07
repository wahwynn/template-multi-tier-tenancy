# CLAUDE.md

**You MUST read and follow all conventions in [CONVENTIONS.md](CONVENTIONS.md) before making any changes.** That file contains all coding standards, style guides, and development workflows for this project.

This file contains additional behavioral guidance specific to Claude Code.

## Pre-flight Check

At the start of every session, before doing any work:

1. Read `PROJECT.md`. If any metadata field says "(not yet decided)", **stop and ask the user** to fill it in before proceeding. Do not assume or guess the project type, framework, or database.
2. Check `plans/` for active plan files. If any exist, resume work from where it left off.

## Claude-Specific Behavior
- **Planning files**: Store all planning documents, decision logs, and design docs in `plans/`. Never store plans in session or local agent storage — they must be versioned and reviewable.
- **Plan lifecycle**: Active plans live in `plans/`. When a plan is completed, move it to `plans/archive/`. Treat files in `plans/archive/` as historical reference only — never execute archived plans.
- **Branch naming**: Use `claude/<task-description>-<id>` for branches created by Claude.
