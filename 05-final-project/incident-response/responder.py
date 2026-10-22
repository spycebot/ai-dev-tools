"""Card Catalog incident responder: alert -> evidence -> agent -> policy -> action -> verify.

    uv run --no-project --with pyyaml --with jsonschema python 05-final-project/incident-response/responder.py serve
    ... responder.py replay <alert.json>     run the pipeline on a saved alert payload
    ... responder.py approve <INCIDENT-ID>   a human approves a pending action (see approve.sh)

`serve` listens on :8001 for Grafana's webhook (private and loopback
clients only). For each firing notification it opens an incident folder
under incidents/ and runs, in order:

  1. collect-evidence.sh         read-only, deterministic, before any model
  2. the agent (claude -p)       Read/Grep/Glob only; returns response.schema.json
  3. policy.decide()             autonomy-policy.yaml + facts the responder
                                 gathered itself; the model can't change these
  4. the runbook, if allowed     fixed argv from the policy, never model text
  5. verify-recovery.sh          or an escalation / approval packet
  6. incident.json + incident.md the record a reader can reconstruct it from

One incident runs at a time; alerts that arrive meanwhile are saved and
skipped. Nothing here holds AWS or GitHub credentials: the only write it can
make outside this folder is deploy.sh rollback on this host.
"""

from __future__ import annotations

import ipaddress
import json
import os
import re
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import jsonschema
import yaml

from policy import Facts, decide

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
INCIDENTS = HERE / "incidents"
SRV = Path(os.getenv("SRV_DIR", "/srv/card-catalog"))
PORT = int(os.getenv("RESPONDER_PORT", "8001"))
AGENT_CMD = os.getenv("AGENT_CMD", "claude")
AGENT_TIMEOUT = int(os.getenv("AGENT_TIMEOUT", "900"))
VERIFY_WATCH = os.getenv("VERIFY_WATCH_SECONDS", "180")
AGENT_TOOLS = "Read,Grep,Glob"   # read-only; no Bash, no Edit/Write, no network
# Evidence includes attacker-controlled text (request paths in container.log),
# and the record is committed to a public repo. Headless claude already denies
# reads outside the repo; these deny rules hold even if a user's settings
# allow more, and also cover secrets that could ever land inside the repo.
AGENT_DENY = ",".join(f"Read({p})" for p in (
    "//srv/**", "~/.claude/**", "~/.config/**", "~/.ssh/**", "~/.aws/**", "~/setup/**",
    "**/.env", "**/.env.*", "**/prod.env", "**/staging.env", "**/*.db"))

SCHEMA = json.loads((HERE / "response.schema.json").read_text())
POLICY = yaml.safe_load((HERE / "autonomy-policy.yaml").read_text())
lock = threading.Lock()


def log(msg: str) -> None:
    print(f"{datetime.now().isoformat(timespec='seconds')} {msg}", flush=True)


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def images() -> dict[str, str]:
    lines = (SRV / "images.env").read_text().splitlines()
    return dict(line.split("=", 1) for line in lines if "=" in line)


def env_images(env: str) -> tuple[str, str]:
    var = "PROD" if env == "prod" else "STAGING"
    i = images()
    return i.get(f"{var}_IMAGE", ""), i.get(f"{var}_PREVIOUS_IMAGE", "")


def run(argv: list[str], timeout: int, **kw) -> dict:
    started = time.time()
    try:
        p = subprocess.run(argv, capture_output=True, text=True, timeout=timeout,
                           stdin=subprocess.DEVNULL, **kw)
        result = {"exit_code": p.returncode, "stdout": p.stdout, "stderr": p.stderr}
    except subprocess.TimeoutExpired:
        result = {"exit_code": None, "stdout": "", "stderr": f"timed out after {timeout}s"}
    return {"argv": argv, "started_at": datetime.fromtimestamp(started, timezone.utc)
            .strftime("%Y-%m-%dT%H:%M:%SZ"), "seconds": round(time.time() - started), **result}


# --- 2. The agent ------------------------------------------------------------

def run_agent(folder: Path, env: str) -> tuple[dict | None, dict]:
    task = (HERE / "responder-task.md").read_text().split("\n---\n", 1)[1]
    prompt = task.replace("{incident}", str(folder.relative_to(REPO))).replace("{environment}", env)
    argv = [AGENT_CMD, "-p", prompt, "--output-format", "json",
            # claude's validator rejects the 2020-12 `$schema` URI; the
            # schema itself is plain enough for any draft.
            "--json-schema", json.dumps({k: v for k, v in SCHEMA.items() if k != "$schema"}),
            "--tools", AGENT_TOOLS, "--permission-mode", "default",
            "--disallowedTools", AGENT_DENY,
            "--strict-mcp-config"]
    result = run(argv, AGENT_TIMEOUT, cwd=REPO)
    (folder / "agent-output.json").write_text(result["stdout"] or "{}")
    if result["stderr"]:
        (folder / "agent-stderr.log").write_text(result["stderr"])
    shown = [AGENT_CMD, "-p", "<responder-task.md>", "--output-format", "json",
             "--json-schema", "<response.schema.json>", "--tools", AGENT_TOOLS, "--permission-mode", "default",
             "--disallowedTools", "<AGENT_DENY>", "--strict-mcp-config"]
    meta = {"command": shown, "cwd": str(REPO), "exit_code": result["exit_code"], "seconds": result["seconds"]}
    try:
        out = json.loads(result["stdout"])
    except json.JSONDecodeError:
        return None, {**meta, "error": "agent returned no JSON"}
    meta.update(model=list((out.get("modelUsage") or {}).keys()), cost_usd=out.get("total_cost_usd"),
                turns=out.get("num_turns"), session_id=out.get("session_id"),
                permission_denials=out.get("permission_denials"))
    proposal = out.get("structured_output")
    try:
        jsonschema.validate(proposal, SCHEMA)
    except jsonschema.ValidationError as exc:
        return None, {**meta, "error": f"proposal does not match the schema: {exc.message}"}
    return proposal, meta


# --- 3-5. Policy, action, verification ----------------------------------------

def past_automatic_actions(env: str) -> list[datetime]:
    times = []
    for record in INCIDENTS.glob("*/incident.json"):
        try:
            r = json.loads(record.read_text())
        except json.JSONDecodeError:
            continue
        a = r.get("action") or {}
        if r.get("environment") == env and a.get("executed_by") == "responder" and a.get("started_at"):
            times.append(datetime.strptime(a["started_at"], "%Y-%m-%dT%H:%M:%SZ"))
    return times


def execute(record: dict, decision: dict, executed_by: str) -> None:
    env = decision["environment"]
    log(f"{record['id']}: running {decision['runbook']} {env}")
    action = run([str(HERE / decision["runbook"]), env], 600)
    record["action"] = {**action, "executed_by": executed_by}
    verify = run([str(HERE / decision["verify"]), env, decision["target_image"], VERIFY_WATCH], 900)
    try:
        record["verification"] = json.loads(verify["stdout"])
    except json.JSONDecodeError:
        record["verification"] = {"recovered": False, "error": verify["stderr"] or "no output"}
    log(f"{record['id']}: recovered={record['verification'].get('recovered')}")
    if not record["verification"].get("recovered"):
        record["escalation"] = packet(record, "the action ran but recovery was not verified")


def packet(record: dict, why: str) -> dict:
    p = record.get("proposal") or {}
    return {"why": why, "page": "the owner", "environment": record["environment"],
            "deployed_image": record["deployed"]["current_image"],
            "summary": p.get("summary"), "user_impact": p.get("user_impact"),
            "suspected_cause": p.get("suspected_cause"), "evidence": f"{record['folder']}/evidence/",
            "next_steps": p.get("follow_up", [])}


# --- The pipeline --------------------------------------------------------------

def handle(payload: dict) -> Path | None:
    firing = [a for a in payload.get("alerts", []) if a.get("status") == "firing"]
    if not firing:
        return None
    labels = firing[0].get("labels", {})
    env = labels.get("deployment_environment_name", "")
    if env not in ("prod", "staging"):
        env = "staging" if labels.get("test") else env
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    incident_id = f"INC-{stamp}-{re.sub(r'[^a-z]', '', env) or 'unknown'}"
    folder = INCIDENTS / incident_id
    folder.mkdir(parents=True)
    (folder / "alert.json").write_text(json.dumps(payload, indent=2))
    if not lock.acquire(blocking=False):
        (folder / "skipped.txt").write_text("Another incident was being handled; alert saved only.\n")
        log(f"{incident_id}: busy, alert saved only")
        return folder
    threading.Thread(target=pipeline, args=(folder, incident_id, env, firing), daemon=True).start()
    return folder


def pipeline(folder: Path, incident_id: str, env: str, firing: list[dict]) -> None:
    try:
        current, previous = env_images(env) if env in ("prod", "staging") else ("", "")
        record = {
            "id": incident_id, "folder": str(folder.relative_to(REPO)), "environment": env,
            "opened_at": utcnow(),
            "alert": {"rule": firing[0]["labels"].get("alertname"), "fired_at": firing[0].get("startsAt"),
                      "routes": sorted({a["labels"].get("http_route", "") for a in firing}),
                      "alert_images": sorted({a["labels"].get("service_version", "") for a in firing}),
                      "description": firing[0].get("annotations", {}).get("description"),
                      "labels": firing[0]["labels"]},
            "deployed": {"current_image": current, "previous_image": previous},
        }
        if env in ("prod", "staging"):
            log(f"{incident_id}: collecting evidence")
            ev = run([str(HERE / "collect-evidence.sh"), str(folder), env,
                      record["alert"]["routes"][0]], 300)
            record["evidence"] = json.loads((folder / "evidence/manifest.json").read_text()) \
                if (folder / "evidence/manifest.json").exists() else {"error": ev["stderr"]}

        log(f"{incident_id}: agent started")
        proposal, agent = run_agent(folder, env)
        record["agent"], record["proposal"] = agent, proposal
        if proposal is None:
            record["decision"] = {"outcome": "escalate", "reasons": [agent.get("error", "no proposal")]}
            record["escalation"] = packet(record, "the agent did not return a valid proposal")
        else:
            facts = Facts(env, record["alert"]["alert_images"], current, previous,
                          past_automatic_actions(env))
            decision = decide(proposal, facts, POLICY).to_dict()
            record["decision"] = {**decision, "policy": "autonomy-policy.yaml", "decided_at": utcnow()}
            log(f"{incident_id}: decision {decision['outcome']} ({'; '.join(decision['reasons'])})")
            if decision["outcome"] == "execute":
                execute(record, decision, "responder")
            elif decision["outcome"] == "await_approval":
                record["escalation"] = packet(record, "policy requires a human to approve this action")
                record["escalation"]["approve_with"] = f"05-final-project/incident-response/approve.sh {incident_id}"
            elif decision["outcome"] == "escalate":
                record["escalation"] = packet(record, "; ".join(decision["reasons"]))
        record["closed_at"] = utcnow()
        save(folder, record)
        log(f"{incident_id}: done -> {folder.relative_to(REPO)}/incident.md")
    except Exception as exc:  # noqa: BLE001 -- a responder crash must still leave a trace
        (folder / "responder-error.txt").write_text(f"{type(exc).__name__}: {exc}\n")
        log(f"{incident_id}: responder error {exc!r}")
    finally:
        lock.release()


# --- 6. The record ---------------------------------------------------------------

def save(folder: Path, record: dict) -> None:
    (folder / "incident.json").write_text(json.dumps(record, indent=2) + "\n")
    (folder / "incident.md").write_text(render(record))


def render(r: dict) -> str:
    p, d, a, v, e = (r.get(k) or {} for k in ("proposal", "decision", "action", "verification", "escalation"))
    ag = r.get("agent", {})
    lines = [f"# {r['id']}", "",
             f"Environment **{r['environment']}** · opened {r['opened_at']} · closed {r.get('closed_at', '-')}", "",
             "## Deployed version and user impact", "",
             f"- Running: `{r['deployed']['current_image']}`",
             f"- Previous: `{r['deployed']['previous_image']}`",
             f"- Impact: {p.get('user_impact', '-')}", "",
             "## Alert and evidence", "",
             f"- Rule: {r['alert']['rule']}, fired {r['alert']['fired_at']}",
             f"- {r['alert']['description']}",
             f"- Evidence: `{r['folder']}/evidence/` "
             f"({len((r.get('evidence') or {}).get('files', []))} files, see manifest.json)", ""]
    for item in p.get("evidence", []):
        lines.append(f"  - [{item['source']}] `{item['file']}`: {item['finding']}")
    lines += ["", "## Model, configuration and proposal", "",
              f"- Model: {', '.join(ag.get('model') or ['-'])}; {ag.get('turns', '-')} turns, "
              f"{ag.get('seconds', '-')} s, ${ag.get('cost_usd') or 0:.2f}; tools `{AGENT_TOOLS}` only; "
              f"permission denials: {len(ag.get('permission_denials') or [])}",
              f"- Command: `{' '.join(ag.get('command', []))}`",
              f"- Real incident: {p.get('is_real_incident', '-')}; confidence: {p.get('confidence', '-')}",
              f"- Summary: {p.get('summary', ag.get('error', '-'))}",
              f"- Suspected cause: {p.get('suspected_cause', '-')}",
              f"- Proposed: **{(p.get('proposed_action') or {}).get('type', '-')}** "
              f"{(p.get('proposed_action') or {}).get('environment', '')}: "
              f"{(p.get('proposed_action') or {}).get('reason', '')}", "",
              "## Policy decision and command executed", "",
              f"- Decision: **{d.get('outcome', '-')}** at autonomy level {d.get('level', '-')} "
              f"({'; '.join(d.get('reasons', []))})"]
    if a:
        lines += [f"- Executed by {a['executed_by']} at {a['started_at']}: `{' '.join(a['argv'])}` "
                  f"→ exit {a['exit_code']} in {a['seconds']} s", "", "```text", a["stdout"].strip()[-2000:], "```"]
    else:
        lines.append("- Nothing executed.")
    lines += ["", "## Recovery verification or escalation", ""]
    if v:
        lines.append(f"- Recovered: **{v.get('recovered')}** ({v.get('started_at')} → {v.get('ended_at')})")
        for name, check in (v.get("checks") or {}).items():
            detail = {k: x for k, x in check.items() if k not in ("ok", "output")}
            lines.append(f"  - {name}: {'ok' if check.get('ok') else 'FAILED'} {json.dumps(detail)}")
    if not v and not e:
        lines.append("- None needed: no action was proposed or taken.")
    if e:
        lines += [f"- Escalation: {e['why']}"] + [f"  - Next: {s}" for s in e.get("next_steps") or []]
        if e.get("approve_with"):
            lines.append(f"  - Approve with: `{e['approve_with']}`")
    lines += ["", "## Follow-up", ""] + [f"- {s}" for s in p.get("follow_up", [])] + [""]
    return "\n".join(lines)


# --- Entry points ------------------------------------------------------------------

def approve(incident_id: str) -> int:
    if not re.fullmatch(r"INC-\d{8}-\d{6}-[a-z]+", incident_id):
        print("not an incident id", file=sys.stderr)
        return 2
    folder = INCIDENTS / incident_id
    record = json.loads((folder / "incident.json").read_text())
    decision = record.get("decision", {})
    if decision.get("outcome") != "await_approval" or record.get("action"):
        print(f"{incident_id} has no action waiting for approval", file=sys.stderr)
        return 1
    current, previous = env_images(record["environment"])
    if current != record["deployed"]["current_image"]:
        print("the environment changed since the incident; re-check before acting", file=sys.stderr)
        return 1
    record["approval"] = {"by": os.getenv("SUDO_USER") or os.getenv("USER"), "at": utcnow()}
    execute(record, {**decision, "target_image": previous}, f"human ({record['approval']['by']})")
    record["closed_at"] = utcnow()
    save(folder, record)
    print((folder / "incident.md").read_text())
    return 0


class Handler(BaseHTTPRequestHandler):
    def _reply(self, code: int, body: dict) -> None:
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):  # noqa: N802
        if self.path == "/healthz":
            return self._reply(200, {"status": "ok", "busy": lock.locked()})
        self._reply(404, {"error": "not found"})

    def do_POST(self):  # noqa: N802
        if self.path != "/alerts":
            return self._reply(404, {"error": "not found"})
        ip = ipaddress.ip_address(self.client_address[0])
        if not (ip.is_loopback or ip.is_private):
            return self._reply(403, {"error": "forbidden"})
        try:
            payload = json.loads(self.rfile.read(min(int(self.headers.get("Content-Length", 0)), 1_000_000)))
        except ValueError:
            return self._reply(400, {"error": "invalid JSON"})
        folder = handle(payload)
        if folder is None:
            return self._reply(200, {"status": "ignored", "reason": "nothing firing"})
        log(f"alert accepted -> {folder.name}")
        self._reply(202, {"status": "accepted", "incident": folder.name})

    def log_message(self, fmt, *args):
        log(f"{self.client_address[0]} {fmt % args}")


def main(argv: list[str]) -> int:
    INCIDENTS.mkdir(exist_ok=True)
    cmd = argv[1] if len(argv) > 1 else "serve"
    if cmd == "approve" and len(argv) == 3:
        return approve(argv[2])
    if cmd == "replay" and len(argv) == 3:
        folder = handle(json.loads(Path(argv[2]).read_text()))
        if folder:
            while lock.locked() or not ((folder / "incident.json").exists() or (folder / "responder-error.txt").exists()):
                time.sleep(2)
            print(folder / "incident.md")
        return 0
    if cmd == "serve":
        log(f"responder listening on :{PORT}; incidents in {INCIDENTS}")
        ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
