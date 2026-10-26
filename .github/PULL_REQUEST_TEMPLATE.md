## Summary

<!-- What does this pull request change, and why? Link the issue it closes, for example "Closes #12". -->

## Type of change

- [ ] `fix`: bug fix
- [ ] `feat`: new feature
- [ ] `docs`: documentation only
- [ ] `refactor`, `chore`, `ci`, or `build`

## Checklist

<!-- The commands are described in CONTRIBUTING.md, under "Checks". -->

- [ ] Tests pass: `uv run --extra dev python -m pytest`
- [ ] Lint and types pass: `uv run ruff check src/ tests/` and `uv run mypy src/ --ignore-missing-imports`
- [ ] Documentation check passes: `uv run --no-project python scripts/check_docs.py`
- [ ] If `webapp/` changed: `npm run typecheck`, `npm run lint`, `npm run i18n:parity`, and `npm run ui:contract` pass
- [ ] A test was added or updated for the change
- [ ] Documentation is updated where needed (README, `METHODOLOGY.md`, `docs/`, `scripts/README.md`) and follows `docs/STYLE.md`
- [ ] No secret, collected data, analyst bundle, or personal data (such as anything from the `comments` table) is committed
- [ ] Commits follow [Conventional Commits](https://www.conventionalcommits.org/)
