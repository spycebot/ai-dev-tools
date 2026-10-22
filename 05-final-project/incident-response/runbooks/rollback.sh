#!/usr/bin/env bash
# Runbook: roll one environment back to the image it ran before.
#
#   runbooks/rollback.sh <prod|staging>
#
# The only action the incident responder can take. It wraps the same
# deploy.sh rollback a human would run (docs/release-process.md): switch to
# the previous image, wait for the container's health check, smoke test.
# Database migrations are never rolled back (they must stay backward
# compatible), so a rollback is always a container switch and nothing else.
# Run by policy.py (staging, automatically) or approve.sh (any environment,
# after a human approves); never by the model.
set -euo pipefail

env=${1:?usage: rollback.sh <prod|staging>}
[[ $env == prod || $env == staging ]] || { echo "environment must be prod or staging" >&2; exit 2; }
exec "${SRV_DIR:-/srv/card-catalog}/deploy.sh" rollback "$env"
