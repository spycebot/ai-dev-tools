# Observability

Metrics, logs and traces from the deployed Card Catalog (prod and staging),
one dashboard, and one alert on user impact that pages the incident
responder in [`../incident-response/`](../incident-response/).

```text
prod / staging containers ──OTLP/HTTP──► otel-collector ──► Prometheus  (metrics)
  (FastAPI native OpenTelemetry)                        ├─► Loki        (logs)
                                                        └─► Tempo       (traces)
Grafana: dashboard + "Card Catalog 5xx responses" ──webhook──► responder (host :8001)
```

| File | What it is |
|---|---|
| [`compose.yaml`](compose.yaml) | The stack: Collector, Prometheus, Loki, Tempo, Grafana, each with a memory limit |
| [`collector.yaml`](collector.yaml) | OTLP in; Prometheus, Loki and Tempo out |
| [`dashboard.json`](dashboard.json) | Deployed image per environment, 5xx per route, request rate by status, p95 latency, ERROR logs, error traces |
| [`alerts.yaml`](alerts.yaml) | The one alert: any 5xx in the last 2 minutes, per environment and route |
| [`grafana/`](grafana/) | Data sources (with log ↔ trace links) and the webhook contact point |
| [`observability.env`](observability.env) | The app's export settings, switched on by `obs.sh` |
| [`obs.sh`](obs.sh) | `up`, `down`, `status` |

## What the app sends

Nothing custom: the backend uses **FastAPI's native OpenTelemetry**
(`fastapi[opentelemetry]`). For every request except `/health` it records
a span and the `http.server.request.duration` histogram, labelled with
method, route template and status code. For every unhandled exception it
records an ERROR log with the exception type, message and stack trace,
linked to the trace. `docker-compose.server.yml` tags all of it with
`deployment.environment.name` (prod or staging) and `service.version` (the
exact image, `ghcr.io/spycebot/card-catalog:<git sha>`), so an alert names
the deploy that is failing.

[`backend/tests/test_telemetry.py`](../backend/tests/test_telemetry.py) pins
this contract (metric name, attributes, the ERROR log, `/health` excluded),
so a FastAPI upgrade that changes it fails CI rather than silently breaking
the alert.

Export is **off by default**. The app only exports while
`/srv/card-catalog/observability.env` exists, and `obs.sh` creates and
removes that file. Local development and CI export nothing.

## Running it (on the EC2 host)

The stack needs about 1.6 GB of memory next to the app, which means a
`t3.medium`. On the usual `t3.small` it stays off. See
[the operations report](../docs/operations-and-security-report.md) for why.

```bash
05-final-project/observability/obs.sh up      # start the stack, then switch export on (recreates prod + staging)
05-final-project/observability/obs.sh status
05-final-project/observability/obs.sh down    # switch export off, then stop the stack; data volumes are kept
```

Grafana only listens on the server's localhost. Open it through an SSH
tunnel from your own machine:

```bash
ssh -L 3000:localhost:3000 ubuntu@<server>    # then browse to http://localhost:3000 (admin / admin)
```

The default `admin` password is acceptable only because Grafana is never
reachable from outside the server. Set `GRAFANA_ADMIN_PASSWORD` before
`obs.sh up` if that ever changes.

## The alert

`Card Catalog 5xx responses` evaluates every 20 seconds:

```promql
sum by (deployment_environment_name, service_version, http_route)
  (increase(http_server_request_duration_seconds_count{job="card-catalog", http_response_status_code=~"5.."}[2m])) > 0
```

There is one owner and no SLO, so a single 5xx is a failed action by a
real person. The alert fires per environment and route, and its labels
carry the environment, route and deployed image. That is enough for the
responder to know where to look and what it may roll back. With no errors
the query returns nothing, and `noDataState: OK` treats that as healthy.

## Lessons

- **Grafana alert intervals must be a multiple of its 10-second scheduler
  tick.** With `interval: 15s`, Grafana 13 refused to start at all, in a
  restart loop. `20s` works.
- **Prometheus label names come from OTLP.** `service.name` becomes `job`,
  and promoted resource attributes become labels with dots replaced by
  underscores (`deployment_environment_name`). The histogram arrives as
  `http_server_request_duration_seconds_{bucket,count,sum}`.
