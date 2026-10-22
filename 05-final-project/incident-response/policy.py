"""Decide what happens to the agent's proposal: the permission boundary.

The model proposes; this module decides, from autonomy-policy.yaml and
facts the responder gathered itself (the alert, images.env, past
incidents), never from anything the model claims about them. Pure
functions, no I/O, so the rules are unit tested (test_policy.py).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta

CONFIDENCE = {"low": 0, "medium": 1, "high": 2}


@dataclass
class Facts:
    """What the responder knows independently of the model."""

    alert_environment: str            # from the alert's labels
    alert_images: list[str]           # service_version labels on the firing alerts
    current_image: str                # images.env, now
    previous_image: str               # images.env, now
    automatic_actions: list[datetime] = field(default_factory=list)  # this env, past incidents
    now: datetime = field(default_factory=datetime.now)


@dataclass
class Decision:
    outcome: str                      # execute | await_approval | escalate | no_action
    action: str                       # none | rollback | escalate
    environment: str
    level: int                        # autonomy level applied (0, 1, 2)
    reasons: list[str]
    runbook: str | None = None
    verify: str | None = None
    target_image: str | None = None   # what the environment should run afterwards

    def to_dict(self) -> dict:
        return asdict(self)


def decide(proposal: dict, facts: Facts, policy: dict) -> Decision:
    action = proposal["proposed_action"]["type"]
    env = proposal["proposed_action"]["environment"]
    rules = policy["actions"]

    if not proposal.get("is_real_incident", False) or action == "none":
        return Decision("no_action", "none", facts.alert_environment, 0,
                        ["agent found nothing to act on"])
    if action == "escalate":
        return Decision("escalate", "escalate", facts.alert_environment, 0,
                        ["agent proposed escalation: " + proposal["proposed_action"]["reason"]])
    if action not in rules or action in ("none", "escalate"):
        return _escalate(facts, f"action '{action}' is not in autonomy-policy.yaml")

    rule = rules[action]
    level = rule.get("environments", {}).get(env)
    if level is None:
        return _escalate(facts, f"{action} is not allowed for environment '{env}'")

    conditions = rule.get("conditions", {})
    failed = []
    if conditions.get("environment_must_match_alert") and env != facts.alert_environment:
        failed.append(f"proposal targets '{env}' but the alert is for '{facts.alert_environment}'")
    minimum = conditions.get("min_confidence")
    if minimum and CONFIDENCE.get(proposal.get("confidence"), -1) < CONFIDENCE[minimum]:
        failed.append(f"confidence '{proposal.get('confidence')}' is below '{minimum}'")
    if conditions.get("previous_image_required") and not facts.previous_image:
        failed.append("no previous image to roll back to")
    if conditions.get("previous_image_required") and facts.previous_image == facts.current_image:
        failed.append("previous image is the same as the current one")
    if conditions.get("alert_image_must_be_current") and facts.current_image not in facts.alert_images:
        failed.append("the image in the alert is no longer the one deployed")
    if failed:
        return _escalate(facts, *failed)

    reasons = [f"{action} {env}: all policy conditions met"]
    if level >= 2:
        limit = conditions.get("max_automatic_actions_per_hour")
        recent = [t for t in facts.automatic_actions if facts.now - t < timedelta(hours=1)]
        if limit is not None and len(recent) >= limit:
            level = 1
            reasons.append(f"already {len(recent)} automatic action(s) in {env} this hour: needs a human")
    outcome = "execute" if level >= 2 else "await_approval"
    if outcome == "await_approval" and len(reasons) == 1:
        reasons.append(f"autonomy level for {action} in {env} is {level}: a human approves")
    return Decision(outcome, action, env, level, reasons,
                    runbook=rule.get("runbook"), verify=rule.get("verify"),
                    target_image=facts.previous_image)


def _escalate(facts: Facts, *reasons: str) -> Decision:
    return Decision("escalate", "escalate", facts.alert_environment, 0, list(reasons))
