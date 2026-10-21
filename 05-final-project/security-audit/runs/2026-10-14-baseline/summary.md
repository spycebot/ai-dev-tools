# Audit run 2026-10-14-baseline

**Commit:** `ee82e14` (main after PR #7) · **Reviewer model:** claude-opus-5-5
in Claude Code · **Owner sign-off:** by merging the PR that adds this run

The first full audit of Card Catalog. Every finding, with its evidence and
rationale, is in [`findings.json`](findings.json) (schema:
[`../../findings.schema.json`](../../findings.schema.json)).

## What ran

| Layer | Tool | Result | Raw output |
|---|---|---|---|
| Deterministic | Semgrep 1.180.0, 7 registry rulesets, 80 files | 24 hits, all in `.github/workflows/`; none in app code | [`semgrep.json`](semgrep.json) |
| Dependencies | pip-audit 2.10.1, 28 backend runtime packages | 0 known vulnerabilities | [`pip-audit.json`](pip-audit.json) |
| Dependencies | OSV API, 72 frontend packages | 1 (dev-only, build time) | [`osv-frontend.json`](osv-frontend.json) |
| Model review | auth, sessions, proxy trust, secrets flow, agent guardrails | 8 findings | `findings.json` |
| Manual test | 7 spoofed-IP wrong logins against staging | lockout held (401 ×5, then 429) | F06 in `findings.json` |

Semgrep also reported 10 parse errors: its GitHub Actions rules can't parse
`${{ … }}` inside some `run:` blocks as Bash. Those rules skipped five steps
in `deploy.yml`, and the model review read those steps instead.

## Findings

| ID | Severity | Finding | Disposition |
|---|---|---|---|
| F01 | medium | 19 actions referenced by mutable tags, in jobs that can deploy | **fixed**: pinned to SHAs, Dependabot added |
| F05 | medium | Secrets hook missed the Compose `.env` and the server's `prod.env`/`staging.env` | **fixed**: hook widened, tested on 8 paths |
| F03 | low | Workflow input spliced into a shell script (not exploitable: choice input) | **fixed**: passed via env + `case` |
| F04 | low | `source-map-js` 1.2.1 DoS advisory (build-time only) | **fixed**: 1.2.2 |
| F06 | low | Uvicorn trusts any `X-Forwarded-For` | accepted: Caddy strips it (tested) |
| F07 | low | Sessions survive a password reset and logout | **fixed** 2026-10-21: reset rotates the session key |
| F08 | low | No CSP / frame protection | **deferred**: proposal below |
| F09 | low | Base images by mutable tag | **deferred**: with F08 |
| F02 | info | 4 × `curl … \|` flagged as curl-pipe-shell | false positive, annotated |
| F10 | info | OIDC-claims debug step still in deploy jobs | accepted: kept for diagnosis |
| F11 | info | `/docs` is public | accepted: contract is public anyway |
| F12 | info | Rate limiter never evicts IPs | accepted: documented single-instance limit |

After the fixes, `run-semgrep.sh --error` exits 0, with the four false
positives annotated in place.

## Decisions for the owner

- ~~**F07:**~~ Done 2026-10-21 (owner approved): `deploy/set-password.sh`
  now rotates `AUTH_SECRET_KEY` too, so a reset signs every browser out.
  Logout still only clears the cookie in that browser.
- **F08 + F09:** add `X-Frame-Options DENY` and a CSP to the Caddyfile,
  and pin the base images by digest, in one PR that reloads Caddy on the
  server.
- **CI:** make the new `security-scan` job a required status check on
  `main` (Settings → Branches), alongside the existing four.
