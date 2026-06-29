---
name: Feature Development
description: Implementation workflow for approved plans. Read this when asked to implement a plan.
---

# Skill: Feature Development

## When to Use
When the user approves a plan and asks you to implement it.

> 💡 Switch to Flash for this phase: `/model gemini-2.5-flash`

## Prerequisites
- The plan's YAML `status` must be `Approved`. If not, STOP and tell the user.
- Read the relevant tech skill(s) before coding:
  - Backend work → read `.agents/skills/python-backend/SKILL.md`
  - Frontend work → read `.agents/skills/react-frontend/SKILL.md`

## Phase 1 — Branch & Implement

1. `git checkout -b feature/<plan-name>` from `main`
2. Implement backend first (if applicable):
   - Models → Schemas → Services → Routers → Tests
3. Implement frontend (if applicable):
   - Types → API → Hooks → Components → Pages → Tests
4. Write Vitest unit tests for new hooks/utilities
5. Write or update Playwright E2E tests if the plan specifies `needs_e2e: true`

## Phase 2 — Verify (Hard Gate)

1. Run `bash scripts/verify.sh` (add `--e2e` if plan specifies `needs_e2e: true`)
2. If it fails: read the output, fix the issues, re-run. **Maximum 3 attempts.**
3. If still failing after 3 attempts: **STOP**, report the failures, ask the user for guidance
4. **Do not proceed past this point unless verify.sh exits 0**

## Phase 3 — Commit & Merge

1. `git add -A`
2. Write a single conventional commit message:
   ```
   <type>(<scope>): <description>

   <body summarizing all changes>
   ```
3. `git commit`
4. `git checkout main && git merge --no-ff feature/<plan-name>`
5. `git branch -d feature/<plan-name>`
6. Update the plan's YAML: `status: Completed`, update progress checkboxes
7. **STOP** — tell the user: "Ready to push? Run `git push` when you're ready."
   - The agent does **NOT** push. The user pushes manually.

## Conventional Commit Reference

### Types
| Type | Use When |
|------|----------|
| `feat` | Adding a new feature |
| `fix` | Fixing a bug |
| `docs` | Documentation changes only |
| `chore` | Build process, dependencies, tooling |
| `refactor` | Code change that neither fixes nor adds |
| `test` | Adding or correcting tests |
| `perf` | Performance improvement |

### Folio Scopes
`accounts`, `assets`, `transactions`, `portfolio`, `ui`, `api`, `db`, `deps`, `build`

### Commit Rules
- Subject line ≤ 72 characters
- Imperative mood: "add feature" not "added feature"
- No period at end of subject
- No emoji in commits
- Single squash commit per feature

## Safety Rules
- **Never** force-push to `main`
- **Never** push without user confirmation
- **Never** delete `main` branch
- **Always** verify tests pass before merging
- **Always** run `scripts/verify.sh` before committing
