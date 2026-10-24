"""The telemetry contract the alert and the incident responder rely on.

observability/alerts.yaml and incident-response/collect-evidence.sh query
`http_server_request_duration_seconds_count` by `http_route` and
`http_response_status_code`, and read ERROR logs with the stack trace. These
tests pin that contract with in-memory OpenTelemetry providers, so a FastAPI
upgrade that renames a metric or attribute fails here, not in production.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import InMemoryLogRecordExporter, SimpleLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from app.main import create_app
from app.store import InMemoryCardStore
from tests.conftest import TEST_AUTH_CONFIG, TEST_PASSWORD


class BrokenStore(InMemoryCardStore):
    """A store whose list fails, standing in for any unhandled bug."""

    def list_cards(self):
        raise RuntimeError("simulated store failure")


@pytest.fixture
def telemetry():
    metrics = InMemoryMetricReader()
    spans = InMemorySpanExporter()
    logs = InMemoryLogRecordExporter()
    tracer_provider = TracerProvider()
    tracer_provider.add_span_processor(SimpleSpanProcessor(spans))
    logger_provider = LoggerProvider()
    logger_provider.add_log_record_processor(SimpleLogRecordProcessor(logs))
    config = {
        "meter_provider": MeterProvider(metric_readers=[metrics]),
        "tracer_provider": tracer_provider,
        "logger_provider": logger_provider,
    }
    return config, metrics, spans, logs


def _request_points(reader: InMemoryMetricReader) -> list[dict]:
    """Attributes of every http.server.request.duration data point."""
    data = reader.get_metrics_data()
    return [
        dict(point.attributes)
        for resource in (data.resource_metrics if data else [])
        for scope in resource.scope_metrics
        for metric in scope.metrics
        if metric.name == "http.server.request.duration"
        for point in metric.data.data_points
    ]


def _client(store, config) -> TestClient:
    client = TestClient(
        create_app(store, auth_config=TEST_AUTH_CONFIG, telemetry=config),
        raise_server_exceptions=False,
    )
    assert client.post("/api/login", json={"password": TEST_PASSWORD}).status_code == 200
    return client


def test_requests_are_measured_by_route_and_status(telemetry):
    config, metrics, _, _ = telemetry
    client = _client(InMemoryCardStore(seed=False), config)
    assert client.get("/api/cards").status_code == 200
    assert client.get("/api/cards/no-such-card").status_code == 404

    points = _request_points(metrics)
    assert {
        "http.request.method": "GET",
        "http.route": "/api/cards",
        "http.response.status_code": 200,
    }.items() <= next(p for p in points if p["http.route"] == "/api/cards").items()
    # The route template, not the raw path: card IDs must not explode the
    # metric's cardinality.
    assert any(
        p["http.route"] == "/api/cards/{card_id}" and p["http.response.status_code"] == 404
        for p in points
    )


def test_unhandled_error_is_a_500_with_an_error_log_and_span(telemetry):
    config, metrics, spans, logs = telemetry
    client = _client(BrokenStore(seed=False), config)
    assert client.get("/api/cards").status_code == 500

    assert any(
        p["http.route"] == "/api/cards" and p["http.response.status_code"] == 500
        for p in _request_points(metrics)
    )
    errors = [
        r.log_record if hasattr(r, "log_record") else r
        for r in logs.get_finished_logs()
    ]
    errors = [r for r in errors if r.severity_text == "ERROR"]
    assert errors, "an unhandled exception must produce an ERROR log"
    assert "simulated store failure" in str(dict(errors[0].attributes))
    assert any(s.status.status_code.name == "ERROR" for s in spans.get_finished_spans())


def test_health_checks_are_not_measured(telemetry):
    config, metrics, _, _ = telemetry
    client = _client(InMemoryCardStore(seed=False), config)
    for _ in range(3):
        assert client.get("/health").status_code == 200
    assert all(p.get("http.route") != "/health" for p in _request_points(metrics))


def _everything_exported(metrics, spans, logs) -> str:
    """Every attribute, event and log body the providers would export."""
    parts = [str(p) for p in _request_points(metrics)]
    for span in spans.get_finished_spans():
        parts += [span.name, str(dict(span.attributes or {}))]
        parts += [f"{e.name} {dict(e.attributes or {})}" for e in span.events]
    for record in logs.get_finished_logs():
        record = record.log_record if hasattr(record, "log_record") else record
        parts += [str(record.body), str(dict(record.attributes or {}))]
    return "\n".join(parts)


def test_no_card_content_or_credentials_reach_telemetry(telemetry):
    """Course criterion: no customer data or credentials in telemetry."""
    config, metrics, spans, logs = telemetry
    client = _client(BrokenStore(seed=False), config)
    cookie = client.cookies.get("cc_session")
    secrets = {
        "password": TEST_PASSWORD,
        "session cookie": cookie,
        "card title": "Renew passport 7f3c",
        "card description": "Bank details in the drawer 9d2e",
    }
    created = client.post(
        "/api/cards",
        json={"title": secrets["card title"], "description": secrets["card description"]},
    )
    assert created.status_code == 201
    card_id = created.json()["id"]
    assert client.patch(f"/api/cards/{card_id}", json={"title": secrets["card title"] + "!"}).status_code == 200
    assert client.get("/api/cards").status_code == 500  # the ERROR log path too
    assert client.post("/api/login", json={"password": "wrong-" + TEST_PASSWORD}).status_code == 401

    exported = _everything_exported(metrics, spans, logs)
    assert "/api/cards" in exported and "simulated store failure" in exported  # it was recorded
    for what, value in secrets.items():
        assert value and value not in exported, f"{what} reached telemetry"
