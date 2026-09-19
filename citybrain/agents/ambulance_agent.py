from .base_agent import BaseAgent
from collections.abc import Mapping

from citybrain.models.agent_result import ResourceSelectionResult


class AmbulanceAgent(BaseAgent):

    def __init__(self):
        super().__init__("Ambulance Agent")

    def run(self, emergency, state):
        """Legacy first-available selection interface."""

        ambulances = state.get("ambulances", [])

        for ambulance in ambulances:

            if ambulance.get("available"):
                return ambulance

        return None

    def select(self, emergency, state):
        """Select only an explicitly available, identified ambulance."""
        ambulances = state.get("ambulances", []) if isinstance(state, Mapping) else []
        if not isinstance(ambulances, (list, tuple)):
            return ResourceSelectionResult(None, False, "invalid_ambulance_collection",
                                           "ambulance", 0)
        for ambulance in ambulances:
            if (isinstance(ambulance, Mapping)
                    and ambulance.get("available") is True
                    and ambulance.get("id")):
                return ResourceSelectionResult(dict(ambulance), True,
                                               "available_ambulance_selected",
                                               "ambulance", len(ambulances))
        return ResourceSelectionResult(None, False, "no_available_ambulance",
                                       "ambulance", len(ambulances))

    run_structured = select
    select_ambulance = select
