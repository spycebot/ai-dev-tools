#!/usr/bin/env bash
# Post-deploy smoke test for one Card Catalog environment.
#
#   smoke.sh https://cards.terzotech.net
#   smoke.sh https://staging.cards.terzotech.net --public
#   smoke.sh https://cards.terzotech.net --local   # from the server itself:
#                                                   # resolve the name to 127.0.0.1
#
# Checks, through the real HTTPS front door: the health endpoint, that the
# frontend is served with its security headers, and that the API refuses an
# unauthenticated request and the login endpoint rejects a wrong password.
# With --public (staging, the password-free demo: AUTH_REQUIRED=false) it
# checks the opposite instead: the API serves the board with no session.
# Without --public an open API fails the test, so production can't go
# public by accident. Exits non-zero on the first failure, which is what
# triggers a rollback in deploy.sh.
set -euo pipefail

BASE=${1:?usage: smoke.sh <base-url> [--public] [--local]}
shift
CURL=(curl -sS --max-time 10 --retry 5 --retry-delay 3 --retry-all-errors)
PUBLIC=false
for arg in "$@"; do
  case $arg in
    --public) PUBLIC=true ;;
    --local) HOST=${BASE#https://}; CURL+=(--resolve "$HOST:443:127.0.0.1") ;;
    *) echo "smoke.sh: unknown option $arg" >&2; exit 2 ;;
  esac
done

fail() { echo "SMOKE FAIL: $*" >&2; exit 1; }

"${CURL[@]}" -f "$BASE/health" | grep -q '"status":"ok"' || fail "/health"
echo "ok  /health"

"${CURL[@]}" -f "$BASE/" | grep -q '<title>Card Catalog</title>' || fail "frontend index"
echo "ok  frontend served"

# Audit F08: Caddy must send the CSP and frame protection with the page.
headers=$("${CURL[@]}" -sfI "$BASE/") || fail "HEAD /"
grep -qi "^content-security-policy:.*frame-ancestors 'none'" <<< "$headers" || fail "no Content-Security-Policy with frame-ancestors on /"
grep -qi '^x-frame-options: *DENY' <<< "$headers" || fail "no X-Frame-Options: DENY on /"
echo "ok  security headers"

if $PUBLIC; then
  "${CURL[@]}" -f "$BASE/api/session" | grep -q '"auth_required":false' || fail "/api/session does not report a password-free deployment"
  code=$("${CURL[@]}" -o /dev/null -w '%{http_code}' "$BASE/api/cards")
  [[ $code == 200 ]] || fail "/api/cards without a session returned $code, expected 200 on the public demo"
  echo "ok  API open without a password (public demo)"
  echo "smoke test passed: $BASE"
  exit 0
fi

code=$("${CURL[@]}" -o /dev/null -w '%{http_code}' "$BASE/api/cards")
[[ $code == 401 ]] || fail "/api/cards without a session returned $code, expected 401"
echo "ok  API requires auth"

code=$("${CURL[@]}" -o /dev/null -w '%{http_code}' -H 'content-type: application/json' \
  -d '{"password":"smoke-test-wrong-password"}' "$BASE/api/login")
# 429 is also a pass: the rate limiter (5 failures / 5 min per IP) is part of
# the auth path, and back-to-back deploys + rollbacks can trip it.
[[ $code == 401 || $code == 429 ]] || fail "/api/login with a wrong password returned $code, expected 401 (or 429)"
echo "ok  login rejects a wrong password ($code)"

echo "smoke test passed: $BASE"
