"""Unit tests for the permission boundary (policy.py) against the real policy file.

    uv run --no-project --with pytest --with pyyaml pytest 05-final-project/incident-response/test_policy.py
"""

from datetime import datetime, timedelta
from pathlib import Path

import pytest
import yaml

from policy import Facts, decide

POLICY = yaml.safe_load((Path(__file__).parent / "autonomy-policy.yaml").read_text())
BAD = "ghcr.io/spycebot/card-catalog:bad"
GOOD = "ghcr.io/spycebot/card-catalog:good"
NOW = datetime(2026, 10, 22, 12, 0)


def proposal(action="rollback", env="staging", confidence="high", real=True):
    return {
        "is_real_incident": real,
        "proposed_action": {"type": action, "environment": env, "reason": "r"},
        "confidence": confidence,
    }


def facts(env="staging", alert_images=(BAD,), current=BAD, previous=GOOD, actions=()):
    return Facts(env, list(alert_images), current, previous, list(actions), NOW)


def test_staging_rollback_runs_automatically():
    d = decide(proposal(), facts(), POLICY)
    assert (d.outcome, d.level, d.target_image) == ("execute", 2, GOOD)
    assert d.runbook == "runbooks/rollback.sh" and d.verify == "runbooks/verify-recovery.sh"


def test_prod_rollback_waits_for_a_human():
    d = decide(proposal(env="prod"), facts(env="prod"), POLICY)
    assert (d.outcome, d.level) == ("await_approval", 1)


@pytest.mark.parametrize("p, f, reason", [
    (proposal(env="prod"), facts(env="staging"), "alert is for 'staging'"),
    (proposal(confidence="medium"), facts(), "below 'high'"),
    (proposal(), facts(previous=""), "no previous image"),
    (proposal(), facts(previous=BAD), "same as the current"),
    (proposal(), facts(current=GOOD), "no longer the one deployed"),
    (proposal(action="restart_database"), facts(), "not in autonomy-policy.yaml"),
])
def test_unmet_conditions_escalate_and_execute_nothing(p, f, reason):
    d = decide(p, f, POLICY)
    assert d.outcome == "escalate" and d.runbook is None
    assert any(reason in r for r in d.reasons), d.reasons


def test_rate_limit_downgrades_a_second_automatic_action_to_approval():
    d = decide(proposal(), facts(actions=[NOW - timedelta(minutes=20)]), POLICY)
    assert (d.outcome, d.level) == ("await_approval", 1)
    old = decide(proposal(), facts(actions=[NOW - timedelta(hours=2)]), POLICY)
    assert old.outcome == "execute"


def test_not_real_or_none_does_nothing():
    assert decide(proposal(real=False), facts(), POLICY).outcome == "no_action"
    assert decide(proposal(action="none", env="none"), facts(), POLICY).outcome == "no_action"


def test_agent_escalation_is_respected():
    d = decide(proposal(action="escalate", env="staging"), facts(), POLICY)
    assert (d.outcome, d.runbook) == ("escalate", None)
