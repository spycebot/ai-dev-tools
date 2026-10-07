#!/usr/bin/env bash
# Post-deploy smoke test for one Card Catalog environment.
#
#   smoke.sh https://staging.cards.terzotech.net
#   smoke.sh https://cards.terzotech.net --local   # from the server itself:
#                                                   # resolve the name to 127.0.0.1
#
# Checks, through the real HTTPS front door: the health endpoint, that the
# frontend is served, that the API refuses an unauthenticated request, and
# that the login endpoint is up and rejects a wrong password. Exits non-zero
# on the first failure, which is what triggers a rollback in deploy.sh.
set -euo pipefail

BASE=${1:?usage: smoke.sh <base-url> [--local]}
CURL=(curl -sS --max-time 10 --retry 5 --retry-delay 3 --retry-all-errors)
if [[ ${2:-} == --local ]]; then
  HOST=${BASE#https://}
  CURL+=(--resolve "$HOST:443:127.0.0.1")
fi

fail() { echo "SMOKE FAIL: $*" >&2; exit 1; }

"${CURL[@]}" -f "$BASE/health" | grep -q '"status":"ok"' || fail "/health"
echo "ok  /health"

"${CURL[@]}" -f "$BASE/" | grep -q '<title>Card Catalog</title>' || fail "frontend index"
echo "ok  frontend served"

code=$("${CURL[@]}" -o /dev/null -w '%{http_code}' "$BASE/api/cards")
[[ $code == 401 ]] || fail "/api/cards without a session returned $code, expected 401"
echo "ok  API requires auth"

code=$("${CURL[@]}" -o /dev/null -w '%{http_code}' -H 'content-type: application/json' \
  -d '{"password":"smoke-test-wrong-password"}' "$BASE/api/login")
[[ $code == 401 ]] || fail "/api/login with a wrong password returned $code, expected 401"
echo "ok  login rejects a wrong password"

echo "smoke test passed: $BASE"
