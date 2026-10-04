---
name: debug-ci-failure
description: Triage a failing backend test run (unit or integration) by classifying it first, checking the project's known-gotcha list, then reproducing the smallest failing case. Use when a test suite fails and the cause isn't obvious from the first error line.
---

# Debug a test-suite failure

A general triage procedure, generalized from the project-specific version at
`03-test-containerize-and-deploy-an-ai-assisted-app/.claude/skills/debug-ci-failure/SKILL.md`.
When adapting this plugin to a new project, replace the commands and
"known-gotcha" grep below with that project's equivalents.

## 1. Classify the failure

Run the unit/fast suite and the integration/slow suite separately:

```bash
<unit test command>          # e.g. uv run pytest -m "not integration" -q
<integration test command>   # e.g. uv run pytest -m integration -q
```

- Only the integration suite fails → suspect environment/infrastructure
  (a real database, migrations, external service), not application logic.
- The unit suite also fails → application logic bug.

## 2. Check for a documented known-gotcha before debugging from scratch

Many repos keep a running list of non-obvious issues already found once
(a README "Challenges & Notes" section, a `docs/gotchas.md`, or similar).
Grep it for the failing area before re-deriving a fix:

```bash
grep -n -A2 -i "<keyword from the failing test/module>" README.md
```

## 3. Reproduce the smallest failing case

```bash
<test command> <specific failing test> -x --tb=short
```

## 4. Check any machine-readable contract the code must satisfy

If the failure involves a request/response shape or public interface,
confirm the contract test (OpenAPI spec check, schema validation, etc.)
still passes on its own.

## 5. Fix, then re-run the full suite

Don't just confirm the one reported test now passes — re-run everything, in
case the same class of bug appears in a parametrized or parallel code path
(e.g. a second backend/store implementation).
