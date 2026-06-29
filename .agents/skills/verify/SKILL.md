---
name: Standalone Verification
description: Run QA checks on the current state. Read this when asked to verify or check the build.
---

# Skill: Standalone Verification

## When to Use
When the user asks to verify, run QA, or check the build status.

## Workflow

1. Run `bash scripts/verify.sh --e2e` for a full check (including Playwright E2E tests)
   - Or `bash scripts/verify.sh` for checks without E2E
2. Report results in a structured format
3. If failures exist, explain what's broken and suggest fixes

## What verify.sh Checks

| Check | Command |
|-------|---------|
| Backend pytest | `cd backend && python -m pytest -v --tb=short` |
| Frontend lint | `cd frontend && npm run lint` |
| Frontend types | `cd frontend && npx tsc --noEmit` |
| Frontend unit tests | `cd frontend && npx vitest run` |
| Frontend build | `cd frontend && npm run build` |
| Playwright E2E | `cd frontend && npx playwright test` (only with `--e2e` flag) |

## Result Interpretation

- Exit code 0 = all checks passed
- Exit code 1 = one or more checks failed
- The script outputs a structured summary showing pass/fail for each check

## Optional: Write a Report

If the user asks for a report, save it to `.agents/reports/<name>-qa.md`.
