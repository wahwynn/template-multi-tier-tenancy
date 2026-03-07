# GitHub Copilot Instructions

**You MUST read and follow all conventions in CONVENTIONS.md before making any changes.** That file contains all coding standards, style guides, and development workflows for this project.

This file contains additional behavioral guidance specific to GitHub Copilot.

## Pre-flight Check

At the start of every session, before doing any work:

1. Read `PROJECT.md`. If any metadata field says "(not yet decided)", **stop and ask the user** to fill it in before proceeding. Do not assume or guess the project type, framework, or database.

## Copilot-Specific Behavior

- **Follow the style guide strictly**: When generating code completions, follow the type hint, naming, and formatting conventions in CONVENTIONS.md.
- **No deprecated patterns in suggestions**: Never suggest `List`, `Dict`, `Optional` imports from `typing` in Python. Never suggest TypeScript `enum` or default exports in TypeScript.
- **Test-first suggestions**: When asked to implement a feature, suggest the test first, then the implementation.
- **Respect existing patterns**: Match the style of surrounding code — do not introduce inconsistent formatting, naming, or structural patterns.
