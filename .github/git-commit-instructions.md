# Git Commit Instructions

## Format

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

## Types

| Type | Use When |
|------|----------|
| `feat` | Adding a new feature |
| `fix` | Fixing a bug |
| `docs` | Documentation changes only |
| `style` | Formatting, whitespace, etc. |
| `refactor` | Code change that neither fixes nor adds |
| `perf` | Performance improvement |
| `test` | Adding or correcting tests |
| `chore` | Build process, dependencies, tooling |
| `ci` | CI/CD configuration changes |
| `revert` | Reverting a previous commit |

## Scopes (Folio-Specific)

Use the module or feature area:

`accounts`, `assets`, `transactions`, `portfolio`, `ui`, `api`, `db`, `deps`, `build`

## Rules

- Subject line ≤ 72 characters
- Use imperative mood: "add feature" not "added feature"
- No period at end of subject
- No emoji in commits
- Body wraps at 80 characters
- Reference issues: `Fixes #123` or `Closes #456`

## Examples

```
feat(portfolio): add unrealized P&L breakdown by asset
fix(portfolio): handle zero-quantity holding edge case in sell processing
docs(readme): update build instructions for development setup
test(transactions): add edge case tests for withdrawal validation
chore(deps): bump FastAPI to 0.115.0
refactor(api): extract common query parameters to shared dependency
```
