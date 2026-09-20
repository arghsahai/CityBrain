"""Signal execution boundary — advisory only.

Subhashini's SignalAgent produces advisory recommendations.
Physical signal control (green-corridor, forced phases) is
future work.

This module validates signal actions and clearly marks them
as advisory.  It does NOT automatically force signals.

Implemented:
    Advisory validation and logging of signal recommendations.

Interface-only (future work):
    Physical TraCI trafficlight.setPhase execution.
    Signal state restoration after emergency passes.
"""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class SignalAction:
    """Structured signal priority request."""

    target: str
    action: str
    reason: str
    advisory: bool = True


@dataclass
class SignalResult:
    """Outcome of a signal action validation."""

    success: bool
    target: str
    reason: str
    advisory: bool = True
    executed: bool = False


class SignalExecutor:
    """
    Signal execution boundary.

    Currently advisory-only.  Validates signal recommendations
    from the planner but does not physically actuate signals.

    Future work:
        If the planner provides sufficient execution data
        (target junction, required phase, duration), this
        executor would apply TraCI trafficlight.setPhase
        and preserve restoration ability.
    """

    def validate_actions(
        self,
        recommendations: list,
    ) -> List[SignalResult]:
        """
        Validate signal advisory recommendations.

        Each recommendation is expected to have:
            target: junction ID
            action: action type (e.g. REQUEST_SIGNAL_PRIORITY)
            reason: human-readable reason

        Returns a list of SignalResult indicating whether each
        action is valid (structurally) and whether it was executed.
        """

        results = []

        for rec in recommendations:
            target = None
            action = None
            reason = None

            if hasattr(rec, "target"):
                target = rec.target
                action = rec.action
                reason = rec.reason
            elif isinstance(rec, dict):
                target = rec.get("target")
                action = rec.get("action")
                reason = rec.get("reason")

            if not target or not action:
                results.append(
                    SignalResult(
                        success=False,
                        target=target or "unknown",
                        reason="invalid_signal_action",
                        advisory=True,
                        executed=False,
                    )
                )
                continue

            # Advisory-only: log but do not execute.
            results.append(
                SignalResult(
                    success=True,
                    target=target,
                    reason=f"advisory_validated: {reason}",
                    advisory=True,
                    executed=False,
                )
            )

        return results

    def execute_advisory(
        self,
        plan,
        state: Optional[dict] = None,
    ) -> List[SignalResult]:
        """
        Extract and validate signal recommendations from a plan.

        Does NOT physically execute signal changes.
        """

        recommendations = []

        if hasattr(plan, "recommendations"):
            signal_recs = plan.recommendations.get("signal", [])

            for rec in signal_recs:
                if isinstance(rec, dict):
                    recommendations.append(rec)

        if not recommendations:
            return []

        return self.validate_actions(recommendations)
