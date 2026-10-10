"""Card Catalog Ops MCP server.

Exposes a deliberately small, scoped set of tools to a coding agent working
on the Card Catalog app (the parent directory, 05-final-project/):
running the existing test suites and checking the API/openapi contract.

Design boundary (see ../docs/permissions.md for the full rationale): every
tool here only *runs the project's own test commands*. None of them read
`.env`, connect to a real/production database, accept arbitrary shell input,
or write anything. An agent with only this MCP server attached cannot read
secrets, touch production data, or run an arbitrary command — it can only
ask "do the tests pass."
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from mcp.server.fastmcp import FastMCP

APP_ROOT = Path(__file__).resolve().parent.parent
BACKEND_ROOT = APP_ROOT / "backend"
FRONTEND_ROOT = APP_ROOT / "frontend"

mcp = FastMCP("card-catalog-ops")


def _run(args: list[str], cwd: Path, timeout: int = 120) -> str:
    try:
        result = subprocess.run(
            args,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError as exc:
        return f"error: command not found: {exc}"
    except subprocess.TimeoutExpired:
        return f"error: command timed out after {timeout}s: {' '.join(args)}"
    output = (result.stdout + result.stderr).strip()
    status = "PASSED" if result.returncode == 0 else f"FAILED (exit {result.returncode})"
    return f"{status}\n\n{output[-6000:]}"  # tail only — keep the agent's context bounded


@mcp.tool()
def run_backend_tests(scope: str = "unit") -> str:
    """Run the Card Catalog backend pytest suite.

    scope: "unit" (default, no external services), "integration" (needs
    postgresql-17's initdb/postgres on PATH), or "all".
    """
    marker_args = {
        "unit": ["-m", "not integration"],
        "integration": ["-m", "integration"],
        "all": [],
    }.get(scope)
    if marker_args is None:
        return f"error: unknown scope '{scope}', expected unit|integration|all"
    return _run(["uv", "run", "pytest", "-q", *marker_args], cwd=BACKEND_ROOT)


@mcp.tool()
def check_api_contract() -> str:
    """Verify openapi.yaml and the live FastAPI app expose the same operations."""
    return _run(["uv", "run", "pytest", "tests/test_openapi.py", "-q"], cwd=BACKEND_ROOT)


@mcp.tool()
def run_frontend_lint() -> str:
    """Run oxlint over the Card Catalog frontend."""
    return _run(["npm", "run", "lint"], cwd=FRONTEND_ROOT)


if __name__ == "__main__":
    mcp.run()
