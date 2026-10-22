#!/usr/bin/env bash
# A human approves the action the policy held back (autonomy level 1).
#
#   05-final-project/incident-response/approve.sh INC-YYYYMMDD-HHMMSS-<env>
#
# Re-checks that the environment still runs the image the incident was
# about, runs the same runbook and verification the responder would have,
# records who approved it, and prints the updated incident record.
set -euo pipefail
cd "$(dirname "$0")"
exec uv run -q --no-project --with pyyaml --with jsonschema python responder.py approve "${1:?incident id}"
