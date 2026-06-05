# Folio — Agent Workflow Guide

This guide explains how to use the multi-agent development workflow for Folio.

## Overview

Folio uses a 4-agent workflow where each agent has a specific role:

| Agent | Role | Artifacts |
|-------|------|-----------|
| **Planning Agent** | Writes feature specifications | `.agents/plans/*.md` |
| **Developer Agent** | Implements from approved plans | Feature branches |
| **QA Agent** | Verifies features against specs | `.agents/reports/*.md` |
| **Git Agent** | Commits, merges, releases | Changelog, tags |

## Workflow Cycle

```
  You → Planning Agent → You (approve) → Developer Agent → QA Agent
                                                              ↓
                                              FAIL → Developer Agent (fix)
                                              PASS → You (review) → Git Agent → ✅ Done
```

## Step-by-Step

### Step 1: Plan

Open a new AI chat session and say:

> You are the Planning Agent. Read `.agents/agents/planning.agent.md` for your instructions.
>
> Feature request: *<describe what you want>*
>
> Write a plan to `.agents/plans/<feature-name>.md`

The agent will research the codebase and produce a detailed specification.

### Step 2: Approve

Review the generated plan. Ask questions, request changes, or approve:

> Plan approved. Update status to Approved.

### Step 3: Develop

Open a **new** AI chat session and say:

> You are the Developer Agent. Read `.agents/agents/developer.agent.md` for your instructions.
>
> Implement the approved plan at `.agents/plans/<feature-name>.md`

The agent will create a feature branch, implement the changes, write tests, and verify builds.

### Step 4: QA

Open a **new** AI chat session and say:

> You are the QA Agent. Read `.agents/agents/qa.agent.md` for your instructions.
>
> Verify the feature branch `feature/<name>` against the plan at `.agents/plans/<feature-name>.md`

The agent will run tests, check acceptance criteria, and produce a report.

### Step 5: Fix (if needed)

If QA fails, go back to the Developer Agent session:

> QA found issues. See `.agents/reports/<feature-name>-qa.md`. Fix them.

### Step 6: Release

After you manually verify and QA passes:

> You are the Git Agent. Read `.agents/agents/git.agent.md` for your instructions.
>
> The feature branch `feature/<name>` has passed QA.
> Stage, commit with conventional format, merge to main, and tag as vX.Y.Z.

## Quick Reference

### Build Commands

```bash
# Backend
cd backend && source .venv/bin/activate && python -m pytest -v

# Frontend
cd frontend && npm run build
```

### Git Hooks

Install the pre-configured hooks:

```bash
cp scripts/pre-commit .git/hooks/pre-commit
cp scripts/pre-push .git/hooks/pre-push
```

### File Locations

| What | Where |
|------|-------|
| Project context | `AGENTS.md` |
| Agent definitions | `.agents/agents/*.agent.md` |
| Skills / how-to guides | `.agents/skills/*/SKILL.md` |
| Feature plans | `.agents/plans/*.md` |
| QA reports | `.agents/reports/*.md` |
| Task queue | `.agents/tasks.yml` |
| Commit format | `.github/git-commit-instructions.md` |
| Backend guidance | `backend/AGENTS.md` |
| Frontend guidance | `frontend/AGENTS.md` |
