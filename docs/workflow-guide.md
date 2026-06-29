# Folio — Workflow Guide

This guide explains how to use the skill-based development workflow for Folio.

## Quick Start

### Plan a Feature (use Opus)
> Switch to Opus: `/model claude-opus-4-6`

```
Read .agents/skills/plan/SKILL.md and plan this feature: <describe your feature>
```

### Implement the Plan (use Flash)
> Switch to Flash: `/model gemini-2.5-flash`

```
Read .agents/skills/develop/SKILL.md and implement .agents/plans/<name>.md
```

### Standalone QA (use Flash)
```
Read .agents/skills/verify/SKILL.md and verify the current state
```

## Workflow Lifecycle

```
Plan (Opus) → You approve → Implement + Verify + Commit (Flash) → You push
```

Everything happens in a single session. The agent pauses for your approval at defined gates:
1. After writing the plan (you review and approve)
2. After committing (you push manually)

## Detailed Steps

### Step 1: Plan
Tell the agent to read the planning skill and describe the feature. It will:
- Research the codebase
- Check for conflicting plans
- Write a spec to `.agents/plans/<feature-name>.md`
- **STOP** and wait for your approval

### Step 2: Approve
Review the plan. Ask questions, request changes, or approve:
> Plan approved. Update status to Approved.

### Step 3: Implement
Tell the agent to read the develop skill and implement the plan. It will:
- Create a feature branch
- Implement backend and/or frontend changes
- Write tests (pytest, Vitest, Playwright)
- Run `scripts/verify.sh` (hard gate — must pass)
- Auto-fix failures (up to 3 attempts)
- Squash commit with conventional format
- Merge to main via `--no-ff`
- **STOP** before pushing

### Step 4: Push
You push manually:
```bash
git push
```

## File & Command Reference

| What | Where |
|------|-------|
| Project context | `AGENTS.md` |
| Backend context | `backend/AGENTS.md` |
| Frontend context | `frontend/AGENTS.md` |
| Skills | `.agents/skills/*/SKILL.md` |
| Feature plans | `.agents/plans/*.md` |
| QA reports (optional) | `.agents/reports/*.md` |
| Verification script | `scripts/verify.sh` |
| Commit format | `.github/git-commit-instructions.md` |

## Standalone QA

You can run QA at any time without the full workflow:

```
Read .agents/skills/verify/SKILL.md and verify the current state
```

This runs `scripts/verify.sh --e2e` and reports results.

## Model Recommendations

| Phase | Model | Why |
|-------|-------|-----|
| Planning | Opus | Architecture decisions, scope analysis |
| Implementation | Flash | Bulk coding, well-defined by the plan |
| Verification | Flash | Mechanical — run scripts, fix errors |
