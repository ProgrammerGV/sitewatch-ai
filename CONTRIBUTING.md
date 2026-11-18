# Contributing

Use English for code, UI text, documentation, branch names, and commits.

Follow Conventional Commits, with an imperative description:

```text
feat: add region-based presence confirmation
fix: preserve positive evidence after interruption
test: cover camera failure recovery
docs: explain the event lifecycle
```

Keep capture, inference, rules, persistence and HTTP responsibilities separate. Add meaningful tests for behavioral changes and failures. Unit tests must not need a webcam or download weights.

Before opening a pull request:

```powershell
.venv\Scripts\python.exe -m ruff check backend tests
.venv\Scripts\python.exe -m pytest -q
cd frontend
npm ci
npm run build
```

Use an isolated `_test` database for integration tests. Include the trigger, resulting behavior, verification, and limitations in the pull request description. Do not commit credentials, camera URLs with passwords, private evidence, downloaded model weights, or local database files.
