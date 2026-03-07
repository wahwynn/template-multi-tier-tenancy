# Plans Directory

This directory contains execution plans for building software features and implementing changes in the multi-tenant notes application.

## Structure

- `plans/` - Active plan files that are currently being executed
- `plans/archive/` - Completed plans moved here for historical reference

## Plan File Format

Plan files should be written in Markdown format with the following structure:

```markdown
# Plan: [Descriptive Title]

## Overview

Brief description of what this plan accomplishes.

## Steps

### 1. [Step Name]

- [ ] Task 1
- [ ] Task 2
- [ ] Subtask

### 2. [Next Step]

- [ ] Another task

## Completion Criteria

- [ ] Criterion 1
- [ ] Criterion 2

## Notes

Any additional context, dependencies, or considerations.
```

## Workflow

1. **Create Plan**: Write a new plan file in the `plans/` directory
2. **Execute Plan**: Follow the steps in order, checking off completed tasks
3. **Archive Plan**: When all completion criteria are met, move the plan file to `plans/archive/`
4. **Reference**: Use archived plans for historical context and similar future implementations

## Guidelines

- Plans should be step-by-step and actionable
- Include specific completion criteria
- Break down complex tasks into smaller, verifiable steps
- Update plans as work progresses
- Never execute plans from the `archive/` directory - they are for reference only
