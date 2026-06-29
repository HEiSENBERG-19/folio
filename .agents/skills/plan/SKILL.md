---
name: Feature Planning
description: Workflow for planning new features. Read this when asked to plan a feature.
---

# Skill: Feature Planning

## When to Use
When the user asks to plan a feature, write a spec, or design a change.

> 💡 This phase works best with Opus. Switch with `/model claude-opus-4-6` if you haven't.

## Workflow

1. **Read context**: Read `AGENTS.md` (root), `backend/AGENTS.md`, `frontend/AGENTS.md`
2. **Check existing plans**: Review `.agents/plans/` for overlapping or conflicting plans
3. **Research the codebase**: Understand the impact area — read relevant source files
4. **Write the plan**: Save to `.agents/plans/<feature-name>.md` using the format below
5. **STOP**: Tell the user to review and say "approved" to continue

## Plan Format

```markdown
---
name: <Feature Name>
status: Planned
priority: high | medium | low
created: YYYY-MM-DD
updated: YYYY-MM-DD
verification_scope: backend | frontend | full
needs_e2e: true | false
progress:
  - "[ ] Task 1"
  - "[ ] Task 2"
---

# Feature: <Name>

## Summary
One-paragraph description of what this feature does.

## Motivation
Why this feature is needed. What user problem it solves.

## Acceptance Criteria
1. Testable criterion with clear pass/fail
2. Another testable criterion

## Technical Design

### Backend
- New/modified files and what they contain
- API endpoint specifications (method, path, request/response)
- Service layer logic

### Frontend
- New/modified components
- Hook specifications
- UI behavior description

### Database Changes
Schema additions or "None — no database changes."

## Edge Cases
- Error conditions and how they're handled
- Boundary conditions

## Testing Strategy
- Backend: pytest test descriptions
- Frontend: Vitest unit tests, Playwright E2E tests if applicable

## Files to Modify
- `path/to/existing/file.py` — what changes

## New Files
- `path/to/new/file.py` — what it contains
```

## Status Transitions

```
Planned → Approved → In Progress → Completed
                  ↘ Cancelled
```

## Rules
- Always check existing plans before creating a new one
- Never skip the `Approved` step — human must approve
- Update `progress` checkboxes as tasks complete
- Update `updated` date on every modification
- Cross-reference related plans if they overlap
- Include `verification_scope` and `needs_e2e` in every plan's frontmatter
