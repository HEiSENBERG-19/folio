# Skill: Plan Specification

## When to Use
When creating feature specifications for the Planning Agent workflow.

## Plan Location
All plans go in `.agents/plans/` with descriptive kebab-case names:
- `inr-exchange-rate.md`
- `multi-account-support.md`
- `dividend-tracking.md`

## Plan Format

```markdown
---
name: <Feature Name>
status: Planned
priority: high | medium | low
created: YYYY-MM-DD
updated: YYYY-MM-DD
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
3. ...

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
- Frontend: build verification, component test descriptions

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
