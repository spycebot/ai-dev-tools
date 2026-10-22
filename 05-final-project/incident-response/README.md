# Incident responder

When the [5xx alert](../observability/alerts.yaml) fires, this responder
collects the evidence, has a headless agent work out what happened, and
lets a policy file (not the model) decide what happens next. It is the
Module 4 pattern (alert → evidence → agent → policy → action → verify →
record), ported from the HW4 Order Tracker to Card Catalog.

```text
Grafana alert ──webhook :8001──► responder.py
  1. collect-evidence.sh   fixed, read-only queries: deploy state, diff, metrics, logs, traces, smoke test
                           public IPs redacted before anything else reads it
  2. claude -p             Read/Grep/Glob in the repo only → JSON proposal (response.schema.json)
  3. policy.decide()       autonomy-policy.yaml + facts the responder gathered itself
  4. runbooks/rollback.sh  only if the policy allows it: staging on its own, prod after approve.sh
  5. verify-recovery.sh    image, health, smoke test, no new 5xx for 3 minutes
  6. incidents/<id>/       incident.json + incident.md: the full record
```

The full write-up, including the recorded incident, is in
[`docs/operations-and-security-report.md`](../docs/operations-and-security-report.md).

## Files

| File | What it is |
|---|---|
| [`responder.py`](responder.py) | `serve` (the webhook), `replay <alert.json>`, `approve <ID>`; the pipeline above |
| [`collect-evidence.sh`](collect-evidence.sh) | Evidence packet, before any model runs; writes `evidence/manifest.json` |
| [`responder-task.md`](responder-task.md) | The agent's prompt (after the `---`) |
| [`response.schema.json`](response.schema.json) | What the agent must return: impact, cause, evidence, proposed action, confidence |
| [`autonomy-policy.yaml`](autonomy-policy.yaml) | Autonomy levels per action and environment, and the conditions for acting |
| [`policy.py`](policy.py), [`test_policy.py`](test_policy.py) | The decision, and 11 tests of it |
| [`runbooks/`](runbooks/) | `rollback.sh` (wraps `deploy.sh rollback`) and `verify-recovery.sh` |
| [`approve.sh`](approve.sh) | A human approves an action the policy held back |
| [`incidents/`](incidents/) | One folder per incident |

## Autonomy

| Level | Meaning | Applies to |
|---|---|---|
| 0 observe | Evidence and a record; nothing else | `none`, `escalate`, and anything the policy rejects |
| 1 propose | Written up; a human runs `approve.sh <ID>` | rollback of **prod** |
| 2 act | The responder runs the runbook, then verification | rollback of **staging** |

A rollback also needs all of: the proposal names the environment that
alerted, confidence `high`, a previous image exists, the alert's image is
still the one deployed, and no other automatic action on that environment
in the last hour. If any fails, the incident is escalated and nothing runs.
The model can't change any of this: its output is only a proposal.

## Running it

On the EC2 host, with the monitoring stack up (`../observability/obs.sh up`):

```bash
cd 05-final-project/incident-response
uv run --no-project --with pyyaml --with jsonschema python responder.py serve   # leave running
./approve.sh INC-20261022-175440-staging                                          # when a record says "await_approval"
uv run --no-project --with pytest --with pyyaml pytest test_policy.py             # the policy tests
```

`claude` must be installed and logged in for the user running the
responder. Each incident costs about $0.20–0.60 in model usage.

## Incidents

| Incident | What happened | Decision | Outcome |
|---|---|---|---|
| [INC-20261021-210634-staging](incidents/INC-20261021-210634-staging/incident.md) | A hand-written test alert (`test=true`) | `no_action`: the agent judged it not real | Nothing ran, as intended |
| [INC-20261022-175440-staging](incidents/INC-20261022-175440-staging/incident.md) | Game day: a deliberately broken build on staging, every card move to the end of a column returned 500 | `execute`: rollback staging | Rollback done 69 s after the alert fired; recovery verified |
