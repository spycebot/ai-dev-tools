# Audit run 2026-10-22-operations

**Commit:** `3fae8a7` (main after PR #24) plus the incident-response PR ·
**Reviewer model:** claude-opus-5-5 in Claude Code · **Owner sign-off:** by
merging the PR that adds this run

An audit of what the operations work added: the monitoring stack
([`observability/`](../../../observability/)), the incident responder
([`incident-response/`](../../../incident-response/)), the new backend
dependencies, and what the staging game day showed. Each finding, with its
evidence and rationale, is in [`findings.json`](findings.json). The
operations side is written up in
[`docs/operations-and-security-report.md`](../../../docs/operations-and-security-report.md).

## What ran

| Layer | Tool | Result | Raw output |
|---|---|---|---|
| Deterministic | Semgrep 1.180.0, same 7 rulesets, 150 files (51 new) | 0 hits | [`semgrep.json`](semgrep.json) |
| Dependencies | pip-audit 2.10.1, 41 backend runtime packages | 0 known vulnerabilities (after F13) | [`pip-audit.json`](pip-audit.json) |
| Dependencies | CI `security-scan` job on PR #24 | caught F13 | GitHub Actions log |
| Model review | the responder: what it reads, changes, publishes; who can reach it | 4 findings | `findings.json` |
| Manual test | 3 headless `claude -p` probes of the agent's read scope | outside-repo read denied; deny rules hold | F15 |
| Manual test | the game day itself | 1 finding | F18 |

Semgrep's 8 parse errors are the same `deploy.yml` steps as in the baseline,
which its GitHub Actions rules can't parse.

## Findings

| ID | Severity | Finding | Disposition |
|---|---|---|---|
| F14 | medium | Visitors' IP addresses reached the incident record (public repo) | **fixed**: redacted before the model runs |
| F15 | medium | The agent reads attacker-controlled log text and its answer is published | **fixed**: explicit read deny list, verified by probes |
| F13 | low | certifi trusted compromised emSign CAs | **fixed**: 2026.10.19 (PR #24) |
| F16 | low | Grafana admin/admin, used by the evidence collector | accepted: localhost only |
| F17 | low | Responder webhook on all interfaces, port 8001 | accepted: code rejects non-private clients |
| F18 | low | `deploy.sh` deploys any image, even one that skipped CI | **deferred**: owner decision |

## Decisions for the owner

- **F18:** have `deploy.sh` refuse images that didn't come from a green CI
  run on `main`, and add a logged-in card move to `smoke.sh`.
- Still open from the baseline: F08 + F09 (CSP, frame protection, base
  image digests), and making `security-scan` a required check.
