from .base_agent import BaseAgent
from collections.abc import Mapping

from citybrain.models.agent_result import ResourceSelectionResult


class HospitalAgent(BaseAgent):

    def __init__(self):
        super().__init__("Hospital Agent")

    def run(self, emergency, state):
        """Legacy first-hospital-with-explicit-ICU selection interface."""

        hospitals = state.get("hospitals", [])

        for hospital in hospitals:

            if hospital.get("icu_available"):
                return hospital

        return None

    def select(self, emergency, state):
        """Select only supplied hospitals with explicit ICU availability."""
        hospitals = state.get("hospitals", []) if isinstance(state, Mapping) else []
        if not isinstance(hospitals, (list, tuple)):
            return ResourceSelectionResult(None, False, "invalid_hospital_collection",
                                           "hospital", 0)
        for hospital in hospitals:
            if (isinstance(hospital, Mapping)
                    and hospital.get("icu_available") is True
                    and hospital.get("id")):
                return ResourceSelectionResult(dict(hospital), True,
                                               "suitable_hospital_selected",
                                               "hospital", len(hospitals))
        return ResourceSelectionResult(None, False, "no_suitable_hospital",
                                       "hospital", len(hospitals))

    run_structured = select
    select_hospital = select
