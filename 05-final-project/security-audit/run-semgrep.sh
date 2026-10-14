#!/usr/bin/env bash
# Deterministic layer of the security audit: Semgrep over the app and the
# repo's GitHub workflows, with the same rulesets locally and in CI.
#
#   05-final-project/security-audit/run-semgrep.sh            # human-readable
#   05-final-project/security-audit/run-semgrep.sh --json -o runs/<id>/semgrep.json
#   05-final-project/security-audit/run-semgrep.sh --error    # exit 1 on any finding (CI)
#
# Runs from the repo root so .github/workflows/ is in scope. Registry rulesets
# only, no Semgrep login, metrics off. Semgrep honours .gitignore, so real
# .env files and the dev database are never read. A finding is either fixed
# or annotated in place with `nosemgrep: <rule> -- <reason>` and recorded in
# a run's findings.json. See audit-brief.md.
set -euo pipefail
cd "$(dirname "$0")/../.."

SEMGREP_VERSION=1.180.0

exec uvx "semgrep==$SEMGREP_VERSION" scan --metrics=off \
  --config p/python --config p/javascript --config p/typescript \
  --config p/react --config p/dockerfile --config p/github-actions \
  --config p/secrets \
  --exclude node_modules --exclude .venv \
  "$@" 05-final-project .github
