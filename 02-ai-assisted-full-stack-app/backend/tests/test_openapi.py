"""Keep `../openapi.yaml` and the FastAPI app in sync.

The YAML file is the hand-maintained contract; this test fails if the app
grows or loses an endpoint without the contract being updated to match.
"""

from pathlib import Path

import yaml
from fastapi.testclient import TestClient

from app.main import create_app

CONTRACT_PATH = Path(__file__).resolve().parents[2] / "openapi.yaml"


def _operations(paths: dict) -> set[tuple[str, str]]:
    methods = {"get", "post", "put", "patch", "delete"}
    return {
        (path, method)
        for path, item in paths.items()
        for method in item
        if method in methods
    }


def test_contract_file_is_valid_yaml():
    spec = yaml.safe_load(CONTRACT_PATH.read_text())
    assert spec["openapi"].startswith("3.")
    assert "paths" in spec


def test_documented_operations_match_the_app():
    documented = _operations(yaml.safe_load(CONTRACT_PATH.read_text())["paths"])
    live = _operations(create_app().openapi()["paths"])
    assert documented == live


def test_app_serves_its_own_openapi_schema():
    resp = TestClient(create_app()).get("/openapi.json")
    assert resp.status_code == 200
    assert resp.json()["info"]["title"] == "Card Catalog API"
