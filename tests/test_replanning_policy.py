from types import SimpleNamespace

from citybrain.models.planner_result import PlannerOutcome
from citybrain.planner.replanning_policy import ReplanningPolicy


def validation(valid=True, reason="remaining_route_valid"):
    return SimpleNamespace(valid=valid, reason=reason)


def decide(policy=None, **overrides):
    values = dict(
        validation=validation(), current_route=["a"], proposed_route=["b"],
        current_score=20, proposed_score=10, current_time=20,
        active_since=0, last_replan_time=0,
    )
    values.update(overrides)
    return (policy or ReplanningPolicy()).decide(**values)


def test_material_improvement_replans():
    result = decide(ReplanningPolicy(minimum_improvement=5))
    assert result.decision is PlannerOutcome.REPLAN
    assert result.reason == "material_improvement_and_timing_satisfied"


def test_tiny_improvement_keeps_active_route():
    result = decide(
        ReplanningPolicy(minimum_improvement=5), proposed_score=18,
    )
    assert result.decision is PlannerOutcome.KEEP
    assert result.reason == "improvement_below_threshold"


def test_matching_candidate_keeps_active_route():
    result = decide(proposed_route=["a"])
    assert result.decision is PlannerOutcome.KEEP
    assert result.reason == "best_candidate_matches_active_route"


def test_commitment_and_cooldown_prevent_oscillation():
    commitment = decide(
        ReplanningPolicy(minimum_commitment=30), current_time=10,
    )
    cooldown = decide(
        ReplanningPolicy(cooldown=30), current_time=20, last_replan_time=10,
    )
    assert commitment.reason == "minimum_commitment_not_elapsed"
    assert cooldown.reason == "cooldown_not_elapsed"


def test_invalid_route_bypasses_optional_delays():
    result = decide(
        ReplanningPolicy(minimum_improvement=100, minimum_commitment=100,
                         cooldown=100, invalid_route_override=True),
        validation=validation(False, "blocked_edge"),
        current_score=float("inf"), current_time=1,
    )
    assert result.decision is PlannerOutcome.REPLAN
    assert result.reason == "invalid_active_route_override:blocked_edge"
    assert result.commitment_satisfied and result.cooldown_satisfied


def test_no_usable_candidate_is_no_route():
    result = decide(proposed_route=[], proposed_score=float("inf"))
    assert result.decision is PlannerOutcome.NO_ROUTE
    assert result.reason == "no_usable_candidate_route"


def test_policy_rejects_negative_configuration():
    try:
        ReplanningPolicy(minimum_improvement=-1)
    except ValueError as error:
        assert "minimum_improvement" in str(error)
    else:
        raise AssertionError("negative policy configuration was accepted")
