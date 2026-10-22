# INC-20261022-175440-staging

Environment **staging** · opened 2026-10-22T17:54:40Z · closed 2026-10-22T17:58:40Z

## Deployed version and user impact

- Running: `ghcr.io/spycebot/card-catalog:df9cbe01da3a0915b5caf7b8a24cba73dc467a9b`
- Previous: `ghcr.io/spycebot/card-catalog:3fae8a72911f86afaae38c10883c142110d684e7`
- Impact: This only affects staging (https://staging.cards.terzotech.net). Users there can't move cards when the target position is at or past the end of the column, including moves into an empty column. These requests get HTTP 500. The evidence window has 7 such failures, at about 17:52:11, 17:54:05, 17:54:10, 17:54:17, 17:54:19, 17:54:22 and 17:54:32 UTC on 2026-10-22 (logs-errors.json). Prometheus puts it at about 5.5 move 500s in 15 minutes and 4 in the 2-minute alert window. No move request succeeded in the window: there is no 200 series for this route. Every other route is fine: GET /api/cards and the frontend return 200. The smoke test passes because it doesn't exercise moves. The current container has run since 06:30:58Z. Telemetry from before about 17:22Z wasn't collected, so I can't say whether earlier moves failed.

## Alert and evidence

- Rule: Card Catalog 5xx responses, fired 2026-10-22T17:54:30Z
- 4 server error(s) (5xx) on /api/cards/{card_id}/move in staging in the last 2 minutes, running ghcr.io/spycebot/card-catalog:df9cbe01da3a0915b5caf7b8a24cba73dc467a9b.
- Evidence: `05-final-project/incident-response/incidents/INC-20261022-175440-staging/evidence/` (13 files, see manifest.json)

  - [alert] `alert.json`: Firing since 17:54:30Z with severity=page, env=staging, route /api/cards/{card_id}/move and service_version df9cbe0. There are 4 5xx in the 2m window and no test label or test annotation.
  - [deploy] `evidence/deploy.json`: Current image is df9cbe0 and previous is 3fae8a7. The container started at 2026-10-22T06:30:58Z. The commit summary describes an unclamped destination index that raises IndexError on moves to the end of a column.
  - [code] `evidence/change.diff`: The only change is board.py plan_move. `index = min(position, len(destination))` is replaced with `anchor = destination[position]; index = destination.index(anchor)`. No migrations are included.
  - [logs] `evidence/logs-errors.json`: 7 ERROR entries between about 17:52:11 and 17:54:32Z, all IndexError 'list index out of range'. The stack goes main.py:234 move_card -> sqlalchemy_store.py:118 move_card -> board.py:79 plan_move. All are on image df9cbe0 in staging.
  - [metrics] `evidence/metrics-requests.json`: Over 15m there are about 5.5 POST /api/cards/{card_id}/move 500s and no 200s for that route. GET /api/cards and the frontend return 200.
  - [metrics] `evidence/metrics-5xx.json`: 5xx appear only on the move route and only for image df9cbe0.
  - [metrics] `evidence/metrics-5xx-timeline.json`: The only series is image df9cbe0. It is 0 for the first two points and about 6 at the last minute. No other image has 5xx.
  - [traces] `evidence/trace-4f5ec970fd76467c8d2e533dc6d96ac9.json`: The fastapi.endpoint span move_card has error.type IndexError, and the server span shows http.response.status_code 500 on staging.cards.terzotech.net with image df9cbe0. traces-search.json lists 5 such failing move traces.
  - [logs] `evidence/container.log`: The container log shows the same IndexError traceback after `POST /api/cards/<id>/move 500`. /health is still 200. Public IPs are redacted, and I saw no secrets or cookies.
  - [logs] `evidence/smoke-now.txt`: The smoke test passes: health, frontend, auth required, and bad password rejected. It doesn't cover card moves, so the outage doesn't show up there.
  - [code] `05-final-project/backend/app/board.py`: The checked-out plan_move (line 78) still has the clamped `min(position, len(destination))`, and its docstring says 'A position past the end of the destination appends'. The previous image's behaviour is correct.

## Model, configuration and proposal

- Model: claude-opus-5-5; 17 turns, 50 s, $0.59; tools `Read,Grep,Glob` only; permission denials: 0
- Command: `claude -p <responder-task.md> --output-format json --json-schema <response.schema.json> --tools Read,Grep,Glob --strict-mcp-config`
- Real incident: True; confidence: high
- Summary: Staging is returning 500s on every card move (POST /api/cards/{card_id}/move). The cause is an IndexError in board.plan_move, added by the image now running (df9cbe0). Roll staging back to 3fae8a7. The diff has no migrations, and prod is not affected. The commit message calls df9cbe0 a deliberately broken game-day build that skipped CI. I treated that as background only. The alert carries no test label and the failures are real, so this counts as a real incident.
- Suspected cause: The failure is in backend/app/board.py, function plan_move, line 79: `anchor = destination[position]`. It is reached through main.py move_card (line 234) and then sqlalchemy_store.py move_card (line 118). Commit df9cbe0 replaced the clamped `index = min(position, len(destination))` with an unclamped lookup. Any position >= len(destination) now raises IndexError: list index out of range, and that becomes a 500. This covers appending to the end of a column and moving into an empty column. The function's own docstring says a position past the end should append.
- Proposed: **rollback** staging: The errors come only from the current image (df9cbe0), and the stack trace points at the exact line that image's diff added. Previous image 3fae8a7 exists and has the correct clamped code. The diff has no migrations, so switching containers back is safe. Prod is not affected.

## Policy decision and command executed

- Decision: **execute** at autonomy level 2 (rollback staging: all policy conditions met)
- Executed by responder at 2026-10-22T17:55:31Z: `/home/ubuntu/ai-dev-tools/05-final-project/incident-response/runbooks/rollback.sh staging` → exit 0 in 8 s

```text
==> staging: rolling back ghcr.io/spycebot/card-catalog:df9cbe01da3a0915b5caf7b8a24cba73dc467a9b -> ghcr.io/spycebot/card-catalog:3fae8a72911f86afaae38c10883c142110d684e7
ok  /health
ok  frontend served
ok  API requires auth
ok  login rejects a wrong password (401)
smoke test passed: https://staging.cards.terzotech.net
==> staging: now running ghcr.io/spycebot/card-catalog:3fae8a72911f86afaae38c10883c142110d684e7 (run rollback again to undo)
```

## Recovery verification or escalation

- Recovered: **True** (2026-10-22T17:55:39Z → 2026-10-22T17:58:40Z)
  - image: ok {"expected": "ghcr.io/spycebot/card-catalog:3fae8a72911f86afaae38c10883c142110d684e7", "running": "ghcr.io/spycebot/card-catalog:3fae8a72911f86afaae38c10883c142110d684e7"}
  - container_health: ok {"status": "healthy"}
  - smoke_test: ok {}
  - no_new_5xx: ok {"window_seconds": 180, "count": "0"}

## Follow-up

- Roll staging back to ghcr.io/spycebot/card-catalog:3fae8a72911f86afaae38c10883c142110d684e7. Then POST a move to the end of a column and into an empty column, and check both return 200.
- Don't merge df9cbe0. If the 'insert before the anchor' behaviour is wanted, keep the clamp: `index = min(position, len(destination))`.
- tests/test_cards.py::test_move_position_past_end_appends already catches this regression. Add a unit test of board.plan_move for moving into an empty column and for position == len(destination).
- Only allow staging deploys of images that passed CI (ci.yml), so locally built images can't skip the unit suite.
- Add an authenticated card move, at the end of a column and into an empty column, to the post-deploy smoke test. The current smoke test passed while every move failed.
