# Skill: Git Workflow

## When to Use
When performing any git operations on the Folio project.

## Branch Strategy

| Branch | Purpose | Merges To |
|--------|---------|----------|
| `main` | Stable releases | — |
| `feature/<name>` | New features | `main` |
| `fix/<name>` | Bug fixes | `main` |
| `chore/<name>` | Maintenance tasks | `main` |

## Commit Format

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

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
| `ci` | CI/CD configuration changes |

### Folio Scopes
`accounts`, `assets`, `transactions`, `portfolio`, `fifo`, `ui`, `api`, `db`, `deps`, `build`

### Rules
- Subject line ≤ 72 characters
- Imperative mood: "add feature" not "added feature"
- No period at end of subject
- No emoji in commits
- Reference issues if applicable: `Fixes #123`

## Merge Process

1. Verify QA report is `PASS`
2. Verify human has approved the merge
3. `git checkout main`
4. `git merge --no-ff feature/<name>` (preserve merge history)
5. Update `CHANGELOG.md`
6. `git branch -d feature/<name>`
7. If releasing: `git tag -a vX.Y.Z -m "<description>"`
8. Confirm with user before `git push`

## CHANGELOG Format

Follow [Keep a Changelog](https://keepachangelog.com/):

```markdown
## [Unreleased]

## [vX.Y.Z] — YYYY-MM-DD
### Added
- New feature description
### Fixed
- Bug fix description
### Changed
- Change description
```

## Safety Rules
- **Never** force-push to `main`
- **Never** push without user confirmation
- **Never** delete `main` branch
- **Always** verify tests pass before merging
