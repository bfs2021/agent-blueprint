"""Tests for the unused-produced-field lint check."""

from agent_blueprint.ir.compiler import compile_blueprint
from agent_blueprint.linting import lint_blueprint
from agent_blueprint.models.blueprint import BlueprintSpec


def lint(raw: dict):
    spec = BlueprintSpec.model_validate(raw)
    return [
        f
        for f in lint_blueprint(spec, compile_blueprint(spec))
        if f.code == "unused-produced-field"
    ]


def _base(policies: dict | None = None) -> dict:
    raw = {
        "blueprint": {"name": "contracts"},
        "state": {"fields": {
            "messages": {"type": "list[message]", "reducer": "append"},
            "confidence": {"type": "number", "nullable": True},
        }},
        "graph": {
            "entry_point": "router",
            "nodes": {
                "router": {"type": "function"},
                "handoff_review": {"type": "function"},
            },
            "edges": [
                {"from": "router", "to": "END"},
                {"from": "handoff_review", "to": "END"},
            ],
        },
        "contracts": {"nodes": {"router": {"produces": ["confidence"]}}},
    }
    if policies is not None:
        raw["policies"] = policies
    return raw


_ESCALATION = {
    "escalation": {
        "on_low_confidence": "handoff_review",
        "confidence_threshold": 0.75,
    },
}


class TestUnusedProducedField:
    def test_escalation_policy_consumes_confidence(self):
        # The generated runtime reads the node's "confidence" update when
        # policies.escalation is configured with both a target and a threshold.
        assert lint(_base(_ESCALATION)) == []

    def test_without_escalation_policy_confidence_is_still_flagged(self):
        findings = lint(_base())
        assert len(findings) == 1
        assert findings[0].location == "contracts.nodes.router.produces"

    def test_escalation_without_threshold_does_not_consume_confidence(self):
        # _apply_low_confidence_escalation returns before reading "confidence"
        # unless both the target and the threshold are set.
        findings = lint(_base({"escalation": {"on_low_confidence": "handoff_review"}}))
        assert len(findings) == 1
